"""
#-------------------------------------------------------------------------------
# Name:        post_process_funcs.py
# Purpose:     script to read read and write the setup and configuration files
# Author:      Mike Martin
# Created:     31/07/2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
"""

__prog__ = 'post_process_funcs.py'
__version__ = '0.0.0'

# Version history
# ---------------
#
from os.path import isfile, join, isdir

from hwsd_mu_globals_fns import HWSD_mu_globals_csv

def subtract_turkey(form):
    '''
    this function is called to initiate the programme to process non-GUI settings.
    '''
    from glob import glob
    rslts_dir = 'G:\\GlblEcssOutptsMa\\EcosseOutputs'
    hwsd_csv_fname = 'E:\\GlobalEcosseData\\Hwsd_CSVs\\Turkey\\Turkey_hwsd.csv'

    # read CSV file using pandas and create obj
    hwsd_mu_globals = HWSD_mu_globals_csv(form, hwsd_csv_fname)

    # print('\n' + descriptor + ' configuration file ' + config_file)
    return