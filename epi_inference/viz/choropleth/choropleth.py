__all__ = ['create_us_choropleth_scenario', 'create_us_choropleth_summary']

import sys
import geopandas as gpd
import json
import os.path

try:
    from bokeh.io import output_notebook, save, show, output_file
    from bokeh.plotting import figure
    from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar, RangeSlider, PreText, CustomJS
    from bokeh.layouts import gridplot
    from bokeh.palettes import brewer
    from bokeh.resources import CDN
    bokeh_available=True
except:
    bokeh_available=False

currdir = os.path.dirname(__file__)

NON_CONTINENTAL = set(['02','15','60','66','69','72','78'])


def get_values_scenario(gdf, results_json, date, value='beta', value_name='beta'):
    if date is None:
        index=-1
        for fips in results_json:
            datestring = results_json[fips]['date'][index]
            break
    else:
        for fips in results_json:
            index = results_json[fips]['date'].index(date)
            datestring = results_json[fips]['date'][index]
            break
    all_values = set()
    vals = []
    status = []
    for fips in gdf['fips']:
        if fips in results_json:
            status.append( results_json[fips]['status'][index] )
        else:
            status.append( None )

        if fips in results_json and results_json[fips]['status'][index] == 'ok':
            val = results_json[fips][value][index]
            vals.append(val)
            all_values.add(val)
        else:
            vals.append(None)

    ans = {}
    if len(all_values) == 0:
        return ans, None
    ans[value_name] = vals
    ans['Solver Status'] = status
    ans['Date'] = datestring
    return ans, max(all_values)


def create_us_choropleth_scenario(*, results_json, value_key, date=None, shapefile=os.path.join(currdir, 'data/cb_2019_us_county_5m.shp'), states=None, description="Unknown Bokeh Choropleth", value_name="Value", max_value=None, crange=None, cvalue=None, output_html=None, show_browser=False):
    if not bokeh_available:
        raise RuntimeError("Need to install bokeh package to generate choropleth visualization")
    #
    # Load data and rename columns
    #
    gdf = gpd.read_file(shapefile)
    #print(gdf.head())
    if states is None:
        sfp = gdf['STATEFP'].to_list()
        sfp = [x not in NON_CONTINENTAL for x in sfp]
        gdf = gdf.loc[sfp, ]
    elif states == 'AK':    
        gdf = gdf.loc[gdf['STATEFP'] == '02',]
    elif states == 'HI':    
        gdf = gdf.loc[gdf['STATEFP'] == '15',]
    #
    # Setup data that will be presented
    #
    gdf = gdf[['GEOID', 'NAME', 'geometry']]
    gdf.columns = ['fips', 'county_name', 'geometry']
    all_values, max_value = get_values_scenario(gdf, results_json, date, value_key)
    datestring = all_values['Date']
    gdf.insert(1, "solver_status", all_values['Solver Status'])
    gdf.insert(1, "plot_value", all_values['beta'])
    #
    # Create GeoJSONDataSource
    #
    gdf_json = json.loads(gdf.to_json())
    json_data = json.dumps(gdf_json)
    geosource = GeoJSONDataSource(geojson = json_data)
    #
    # The color bar assumes values go from 0 to some maximum value.  The use can specify the 
    # maximum value on the scale, or it will be inferred here
    #
    if max_value is None:
        max_value = int(max_value)+1
    if crange is None:
        crange = [0, max_value]
    else:
        crange = list(crange)
    if cvalue is None:
        cvalue = [crange[0], crange[1]]
    else:
        cvalue = list(cvalue)
    if crange[1] > max_value:
        crange[1] = max_value
    if cvalue[1] > crange[1]:
        cvalue[1] = crange[1]
    if cvalue[0] < crange[0]:
        cvalue[0] = crange[0]
        
    tick_labels = {}
    for i in range(10):
        val = max_value * i/10.0
        tick_labels[str(val)] = '%.02f' % val
    tick_labels[str(max_value)] = '>=%d' % max_value

    palette = brewer['OrRd'][8]
    palette = ['white'] + list(palette[::-1])
    color_mapper = LinearColorMapper(palette = palette, low = 0, high = max_value)
    color_mapper.nan_color = 'darkgray'
    color_mapper.high_color = 'black'

    color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8, width=500, height=20,
                        border_line_color=None,
                        bar_line_color='black',
                        major_label_text_color='black',
                        location = (-10,0), 
                        orientation='horizontal')

    p = figure(title = description+" - "+datestring,
                match_aspect=True,
                plot_width=1200,
                x_axis_location=None,
                y_axis_location=None,
                tools="pan,box_zoom,wheel_zoom,reset,hover,save",
                tooltips=[ ("Name", "@county_name"), ("FIPS", "@fips"), (value_name, "@plot_value"), ("Solver Status", "@solver_status"), ("(Long, Lat)", "($x, $y)") ]
                )

    p.hover.point_policy = "follow_mouse"
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.patches('xs','ys', 
                source=geosource, 
                fill_color={'field' :'plot_value', 'transform' : color_mapper},
                line_color='black',
                line_width=0.25,
                fill_alpha=1)

    p.add_layout(color_bar, 'below')

    # widgets
    range_slider = RangeSlider(start=crange[0], end=crange[1], value=cvalue, value_throttled=cvalue, step=0.1, width=500)
    select_code = """
var maxval = cb_obj.value_throttled[1];
var minval = cb_obj.value_throttled[0];
    
color_mapper.high = maxval;
color_mapper.low = minval;

"""
    callback = CustomJS(args=dict(range_slider=range_slider, color_mapper=color_mapper, plot=p), code = select_code)
    range_slider.js_on_change('value_throttled', callback)

    text = PreText(text='The low/high of the color mapper will be set to the values of the range slider\nValues > max are shown in black\nValues < min are shown in white\nMissing values are shown in gray',width=800)
    
    # final plot layout
    final = gridplot([[p],[range_slider],[text]], toolbar_location="left")

    print("Creating file: "+output_html)
    output_file(output_html, mode='inline', title="US Choropleth Plot")
    save(final)
    if show_browser:
        show(final)


def get_values_summary(gdf, summary_csv, date, value='qmean_filtered_est_beta'):
    if date is None:
        index=-1
        for fips in summary_csv:
            datestring = summary_csv[fips][index]['dates']
            summary_cols = set(summary_csv[fips][index].keys()) - set(['dates'])
            break
    else:
        for fips in summary_csv:
            for index in range(len(summary_csv[fips][index])):
                if date == summary_csv[fips][index]['dates']:
                    datestring = date
                    summary_cols = set(summary_csv[fips][index].keys()) - set(['dates'])
            break


    vals = {}
    for col in summary_cols:
        vals[col] = []
    all_values = set()
    status = []
    for fips in gdf['fips']:
        if fips in summary_csv:
            for col in summary_cols:
                val = summary_csv[fips][index][col]
                if val == '':
                    vals[col].append(None)
                else:
                    val = float(val)
                    vals[col].append(val)
                    if col == value:
                        all_values.add(val)
        else:
            for col in summary_cols:
                vals[col].append(None)

    ans = {}
    if len(all_values) == 0:
        return ans, None
    for col in summary_cols:
        ans[col] = vals[col]
    ans['Date'] = datestring
    return ans, max(all_values)


def create_us_choropleth_summary(*, summary_csv, value_key, date=None, shapefile=os.path.join(currdir, 'data/cb_2019_us_county_5m.shp'), states=None, description="Unknown Bokeh Choropleth", value_name="Value", max_value=None, crange=None, cvalue=None, output_html=None, show_browser=False):
    if not bokeh_available:
        raise RuntimeError("Need to install bokeh package to generate choropleth visualization")
    #
    # Load data and rename columns
    #
    gdf = gpd.read_file(shapefile)
    if states is None:
        sfp = gdf['STATEFP'].to_list()
        sfp = [x not in NON_CONTINENTAL for x in sfp]
        gdf = gdf.loc[sfp, ]
    elif states == 'AK':    
        gdf = gdf.loc[gdf['STATEFP'] == '02',]
    elif states == 'HI':    
        gdf = gdf.loc[gdf['STATEFP'] == '15',]
    #
    # Setup data that will be presented
    #
    gdf = gdf[['GEOID', 'NAME', 'geometry']]
    gdf.columns = ['fips', 'county_name', 'geometry']
    all_values, max_value = get_values_summary(gdf, summary_csv, date)
    datestring = all_values['Date']
    gdf.insert(1, "mean_beta", all_values['qmean_filtered_est_beta'])
    gdf.insert(1, "q05_beta", all_values['q05_filtered_est_beta'])
    gdf.insert(1, "q95_beta", all_values['q95_filtered_est_beta'])
    #
    # Create GeoJSONDataSource
    #
    gdf_json = json.loads(gdf.to_json())
    json_data = json.dumps(gdf_json)
    geosource = GeoJSONDataSource(geojson = json_data)
    #
    # The color bar assumes values go from 0 to some maximum value.  The use can specify the 
    # maximum value on the scale, or it will be inferred here
    #
    if max_value is None:
        max_value = int(max_value)+1
    if crange is None:
        crange = [0, max_value]
    else:
        crange = list(crange)
    if cvalue is None:
        cvalue = [crange[0], crange[1]]
    else:
        cvalue = list(cvalue)
    if crange[1] > max_value:
        crange[1] = max_value
    if cvalue[1] > crange[1]:
        cvalue[1] = crange[1]
    if cvalue[0] < crange[0]:
        cvalue[0] = crange[0]
        
    tick_labels = {}
    for i in range(10):
        val = max_value * i/10.0
        tick_labels[str(val)] = '%.02f' % val
    tick_labels[str(max_value)] = '>=%d' % max_value

    palette = brewer['OrRd'][8]
    palette = ['white'] + list(palette[::-1])
    color_mapper = LinearColorMapper(palette = palette, low = 0, high = max_value)
    color_mapper.nan_color = 'darkgray'
    color_mapper.high_color = 'black'

    color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8, width=500, height=20,
                        border_line_color=None,
                        bar_line_color='black',
                        major_label_text_color='black',
                        location = (-10,0), 
                        orientation='horizontal')

    p = figure(title = description+" - "+datestring,
                match_aspect=True,
                plot_width=1200,
                x_axis_location=None,
                y_axis_location=None,
                tools="pan,box_zoom,wheel_zoom,reset,hover,save",
                tooltips=[ ("Name", "@county_name"), ("FIPS", "@fips"), ("5% Quantile Beta", "@q05_beta"), ("Mean Beta", "@mean_beta"), ("95% Quantile Beta", "@q95_beta"), ("(Long, Lat)", "($x, $y)") ]
                )

    p.hover.point_policy = "follow_mouse"
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.patches('xs','ys', 
                source=geosource, 
                fill_color={'field' :'mean_beta', 'transform' : color_mapper},
                line_color='black',
                line_width=0.25,
                fill_alpha=1)

    p.add_layout(color_bar, 'below')

    # widgets
    range_slider = RangeSlider(start=crange[0], end=crange[1], value=cvalue, value_throttled=cvalue, step=0.1, width=500)
    select_code = """
var maxval = cb_obj.value_throttled[1];
var minval = cb_obj.value_throttled[0];
    
color_mapper.high = maxval;
color_mapper.low = minval;

"""
    callback = CustomJS(args=dict(range_slider=range_slider, color_mapper=color_mapper, plot=p), code = select_code)
    range_slider.js_on_change('value_throttled', callback)

    text = PreText(text='The low/high of the color mapper will be set to the values of the range slider\nValues > max are shown in black\nValues < min are shown in white\nMissing values are shown in gray',width=800)
    
    # final plot layout
    final = gridplot([[p],[range_slider],[text]], toolbar_location="left")

    print("Creating file: "+output_html)
    output_file(output_html, mode='inline', title="US Choropleth Plot")
    save(final)
    if show_browser:
        show(final)


if __name__ == "__main__":
    import os.path
    import json
    if os.path.exists("../../../examples/collects/results_countydata5_FL_windows_mobility.json"):
        with open("../../../examples/collects/results_countydata5_FL_windows_mobility.json","r") as INPUT:
            results = json.load(INPUT)
        create_us_choropleth(results_json=results, value_key="beta", date="2020-04-02", description="Debugging", crange=(0,10), cvalue=(0,3))
    else:
        create_us_choropleth(results_json={}, value_key=None, value_name="FOO", description="Debugging", crange=(0,10), cvalue=(0,3), max_value=1)

