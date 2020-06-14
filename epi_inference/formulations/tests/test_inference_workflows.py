import pytest
import os
import os.path
import shutil

from pyomo.common import fileutils as fileutils
from pyutilib.misc import Options as Options
from epi_inference.engine import driver
from epi_inference.util import compare_json

try:
    import poek
    poek_available=True
except:
    poek_available=False

class TestInference():
    @classmethod
    def setup_class(cls):
        cls._origdir = os.getcwd()
        thisfiledir = fileutils.this_file_dir()
        os.chdir(thisfiledir)

    @classmethod
    def teardown_class(cls):
        os.chdir(cls._origdir)

    def test_mobility_window(self):
        args = Options()
        args.block = 'mobility_windows'
        args.config_file = './config_files/tests1.yml'
        args.verbose = True
        driver.run(args)
    
        # check that the json files match their baselines
        compare_json('./output/tests1_inference_unsampled_countydata1_all.json', './baseline/tests1_inference_unsampled_countydata1_all.json')

        compare_json('./output/tests1_inference_unsampled_countydata1_all_new.json', './baseline/tests1_inference_unsampled_countydata1_all.json')
        compare_json('./output/tests1_inference_unsampled_countydata1_all_pyomo_iterative.json', './baseline/tests1_inference_unsampled_countydata1_all.json', significant_digits=3)
    
        # cleanup the files we created
        os.remove('./output/tests1_inference_unsampled_countydata1_all.json')
        os.remove('./output/tests1_inference_unsampled_countydata1_all_meta.yml')
        os.remove('./output/tests1_inference_unsampled_countydata1_all_new.json')
        os.remove('./output/tests1_inference_unsampled_countydata1_all_new_meta.yml')
        os.remove('./output/tests1_inference_unsampled_countydata1_all_pyomo_iterative.json')
        os.remove('./output/tests1_inference_unsampled_countydata1_all_pyomo_iterative_meta.yml')

    @pytest.mark.skip('Skipping test because "poek" is not installed.')
    def test_mobility_window_poek(self):
        args = Options()
        args.block = 'mobility_windows_poek'
        args.config_file = './config_files/tests1.yml'
        args.verbose = True
        driver.run(args)
    
        # check that the json files match their baselines
        compare_json('./output/tests1_inference_unsampled_countydata1_all_poek.json', './baseline/tests1_inference_unsampled_countydata1_all.json')

        # cleanup the files we created
        os.remove('./output/tests1_inference_unsampled_countydata1_all_poek.json')
        os.remove('./output/tests1_inference_unsampled_countydata1_all_poek_meta.yml')

