"""
#-------------------------------------------------------------------------------
# Name:        initialise_netcdf_utils.py
# Purpose:     script to read read and write the setup and configuration files
# Author:      Mike Martin
# Created:     16/05/2020
# Licence:     <your licence>
#-------------------------------------------------------------------------------
"""

__prog__ = 'initialise_netcdf_utils.py'
__version__ = '0.0.0'

# Version history
# ---------------
# 
from os.path import isdir, exists, join, lexists, normpath
from os import getcwd, makedirs
import json
from glob import glob
from time import sleep
from set_up_logging import set_up_logging

sleepTime = 5
APPLIC_STR = 'netcdf_utils'
ERROR_STR = '*** Error *** '

def initiation(form):
    '''
    initiate the programme
    '''
    # retrieve settings
    # =================

    form.settings = _read_setup_file()
    form.settings['config_file'] = normpath(form.settings['config_dir'] + '/' + APPLIC_STR + '_config.json')
    set_up_logging(form, APPLIC_STR)

    return

def _read_setup_file():
    """
    read settings used for programme from the setup file, if it exists,
    or create setup file using default values if file does not
    """
    func_name =  __prog__ +  ' _read_setup_file'

    # validate setup file
    # ===================
    settings_list = ['config_dir', 'log_dir', 'fname_png', 'wthr_dir']
    fname_setup = APPLIC_STR + '_setup.json'

    setup_file = join(getcwd(), fname_setup)
    if exists(setup_file):
        try:
            with open(setup_file, 'r') as fsetup:
                setup = json.load(fsetup)

        except (OSError, IOError) as e:
                sleep(sleepTime)
                exit(0)
    else:
        setup = _write_default_setup_file(setup_file)

    # initialise vars
    # ===============
    settings = setup['setup']
    for key in settings_list:
        if key not in settings:
            print('*** Error *** setting {} is required in setup file {} '.format(key, setup_file))
            sleep(sleepTime)
            exit(0)

    settings['APPLIC_STR'] = APPLIC_STR

    # make sure directories exist
    # ===========================
    config_dir = settings['config_dir']
    if not lexists(config_dir):
        makedirs(config_dir)

    log_dir = settings['log_dir']
    if not lexists(log_dir):
        makedirs(log_dir)

    # report settings
    # ===============
    print('Resource location:')
    print('\tconfiguration file: ' + config_dir)
    print('')

    return settings

def read_config_file(form):
    """
    read widget settings used in the previous programme session from the config file, if it exists,
    or create config file using default settings if config file does not exist
    """
    func_name =  __prog__ +  ' read_config_file'

    config_file = form.settings['config_file']
    if exists(config_file):
        try:
            with open(config_file, 'r') as fconfig:
                config = json.load(fconfig)
                print('Read config file ' + config_file)
        except (OSError, IOError) as e:
                print(e)
                return False
    else:
        config = _write_default_config_file(config_file)

    min_gui_list = ['results_dir', 'overwrite', 'resume_frm_prev', 'out_dir', 'scenario_indx', 'gcm_indx',
                            'fert_dir', 'pop_hist_flag', 'pop_fut_flag']
    grp = 'user_settings'
    for key in min_gui_list:
        if key not in config[grp]:
            print(ERROR_STR + 'attribute {} required for group {} in config file {}'.format(key, grp, config_file))
            sleep(sleepTime)
            exit(0)

    # displays detail
    # ===============
    form.w_lbl_src.setText(config[grp]['results_dir'])
    form.w_lbl_outdir.setText(config[grp]['out_dir'])
    form.w_combo10.setCurrentIndex(config[grp]['scenario_indx'])
    form.w_combo11.setCurrentIndex(config[grp]['gcm_indx'])

    fert_dir = config[grp]['fert_dir']
    form.w_lbl_fertdir.setText(fert_dir)
    report_nc_files(form, fert_dir)

    # set check boxes
    # ===============
    if config[grp]['resume_frm_prev']:
        form.w_resume.setCheckState(2)
    else:
        form.w_resume.setCheckState(0)

    if config[grp]['overwrite']:
        form.w_del_nc.setCheckState(2)
    else:
        form.w_del_nc.setCheckState(0)

    if config[grp]['pop_hist_flag']:
        form.w_pop_hist.setCheckState(2)
    else:
        form.w_pop_hist.setCheckState(0)

    if config[grp]['pop_fut_flag']:
        form.w_pop_fut.setCheckState(2)
    else:
        form.w_pop_fut.setCheckState(0)

    return True

def write_config_file(form, message_flag = True):
    """
    # write current selections to config file
    """
    config_file = form.settings['config_file']

    config = {
        'user_settings': {
            'overwrite':  form.w_del_nc.isChecked(),
            'pop_fut_flag': form.w_pop_fut.isChecked(),
            'pop_hist_flag': form.w_pop_hist.isChecked(),
            'resume_frm_prev': form.w_resume.isChecked(),
            'results_dir': form.w_lbl_src.text(),
            'scenario_indx': form.w_combo10.currentIndex(),
            'gcm_indx': form.w_combo11.currentIndex(),
            'fert_dir': form.w_lbl_fertdir.text(),
            'out_dir': form.w_lbl_outdir.text()
        }
    }

    with open(config_file, 'w') as fconfig:
        json.dump(config, fconfig, indent=2, sort_keys=True)
        print('Wrote configuration file: ' + config_file)

    return

def _write_default_config_file(config_file):
    """
    stanza if config_file needs to be created
    """
    default_config = {
        'user_settings': {
            'gcm_indx':0,
            'overwrite': True,
            'pop_fut_flag': True,
            'pop_hist_flag': True,
            'resume_frm_prev': True,
            'results_dir': '',
            'scenario_indx':0,
            'sims_dir': ''
        }
    }
    # create configuration file
    # =========================
    with open(config_file, 'w') as fconfig:
        json.dump(default_config, fconfig, indent=2, sort_keys=True)
        print('Wrote default configuration file: ' + config_file)

    return default_config

def _write_default_setup_file(setup_file):
    """
    stanza if setup_file needs to be created - TODO: improve
    """
    root_dir = None

    for drive in list(['E:\\','C:\\']):
        if isdir(drive):
            root_dir = join(drive, 'AbUniv\\GlobalEcosseSuite')
            break

    default_setup = {
        'setup': {
            'config_dir': join(root_dir, 'config'),
            'log_dir'   : join(root_dir, 'logs'),
            'fname_png' : join(root_dir, 'Images', 'World_small.PNG')
        }
    }
    # create setup file
    # =================
    with open(setup_file, 'w') as fsetup:
        json.dump(default_setup, fsetup, indent=2, sort_keys=True)
        print('Wrote default setup file: ' + setup_file)

    return default_setup

def report_nc_files(form, dir_ncs):

    num_ncs = len(glob(dir_ncs + '*/era*.nc'))
    if num_ncs > 0:
        mess = 'Found {} era NC files'.format(num_ncs)
        form.w_cncte_fert.setEnabled(True)
    else:
        mess = 'No era NC files'
        form.w_cncte_fert.setEnabled(False)

        num_ncs = len(glob(dir_ncs + '*/n_available_*.nc'))
        if num_ncs > 0:
            mess = 'Found {} N available from grazing NC files'.format(num_ncs)
            form.w_cncte_graze.setEnabled(True)
        else:
            mess = 'No N available from grazing NC files'
            form.w_cncte_graze.setEnabled(True)

    form.w_lbl_fertfns.setText(mess)

    return