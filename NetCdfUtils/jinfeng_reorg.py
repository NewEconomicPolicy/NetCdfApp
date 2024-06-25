#-------------------------------------------------------------------------------
# Name:        jinfeng_reorg.py
# Purpose:     main function to process Spec results
# Author:      Mike Martin
# Created:     11/12/2015
# Licence:     <your licence>
# Comments:    Global warming potential(GWP)
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'jinfeng_reorg.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

from os.path import join, isfile, isdir, split, splitext, normpath
from os import mkdir, remove
from netCDF4 import Dataset
from glob import glob
from time import time, strftime
from numpy import any, array, nan as NaN

from locale import format_string, setlocale, LC_ALL
setlocale(LC_ALL, '')

from spec_utilities import update_progress_post, update_progress2
from jinfeng_classes import NcFileDefn, create_fert_nc

sleepTime = 5

HECTARES_TO_M2 = 0.0001

ERROR_STR = '*** Error *** '
WARNING_STR = '*** Warning *** '

def _concatenate_fert_files(nc_fname, fert_ncs):
    '''

    '''
    try:  # call the Dataset constructor
        all_dset = Dataset(nc_fname, 'a')
    except PermissionError as err:
        print(err)
        return None

    nlats = len(all_dset.dimensions['lat'])
    nlons = len(all_dset.dimensions['lon'])
    nsize_grid = nlats*nlons

    strt_time = time()
    last_time = time()
    nmasked = 0
    nout_of_area = 0
    nwarns = 0
    nvalid = 0
    for tstep, fert_nc in enumerate(fert_ncs):
        read_dset = Dataset(fert_nc, 'r')

        for var_name in list(['Ndep', 'Nmanure', 'Nmineral']):
            all_dset.variables[var_name][tstep, :, :] =  read_dset.variables[var_name][:, :, :, :]

        read_dset.close()
        last_time = update_progress_post(last_time, strt_time, nvalid, nsize_grid, nout_of_area, nmasked, nwarns)

    identify_zero_cells = True
    if identify_zero_cells:

        # stanza to identify all zero cells
        # =================================
        ntsteps = len(all_dset.dimensions['time'])
        nan_slice = array(ntsteps * [NaN])

        for var_name in list(['Ndep', 'Nmanure', 'Nmineral']):
            print('\nProcessing variable: ' + var_name)
            nzeros = 0
            ndata = 0

            for lat_indx in range(nlats):
                for lon_indx in range(nlons):
                    vals = all_dset.variables[var_name][:, lat_indx, lon_indx]
                    if any(vals):
                        ndata += 1
                    else:
                        nzeros += 1
                        all_dset.variables[var_name][:, lat_indx, lon_indx] = nan_slice

                    last_time = update_progress2(last_time, ndata, nzeros, nsize_grid)

            print('\nVariable: ' + var_name + '\tdata points with data: {}\twithout data: {}'.format(ndata, nzeros))

    all_dset.sync()
    all_dset.close()

    return

def concat_jinfeng_dsets(form):
    """

    """
    fert_dir = form.w_lbl_fertdir.text()
    delete_flag = form.w_del_nc.isChecked()

    retcode = _sort_fname_and_start_year(fert_dir, delete_flag)
    if retcode is None:
        return

    nc_fname, strt_year, nyears, fert_ncs = retcode

    clone_defn = NcFileDefn(fert_ncs[-1])
    create_fert_nc(nc_fname, clone_defn, strt_year, nyears)

    _concatenate_fert_files(nc_fname, fert_ncs)

    return

def _sort_fname_and_start_year(fert_dir, delete_flag):
    '''
    gather detail and file name for new NC file
    '''
    out_dir = join(fert_dir, 'concat_dset')     # prepare directory
    if not isdir(out_dir):
        mkdir(out_dir)

    fert_ncs = glob(fert_dir + '*/era*.nc')     # gather existing Nmanure and Nmineral NC files
    nyears = len(fert_ncs)

    # take arbritary file name and construct new file name
    # ====================================================
    fert_fn = fert_ncs[0]
    short_fn = split(fert_fn)[1]
    root_name = splitext(short_fn)[0]
    fn_lst = root_name.split('_')
    strt_year = int(fn_lst[-1])
    nc_fname = join(out_dir, '_'.join(fn_lst[:-1]) + '.nc')

    # check new file name and remove if necessary
    # ===========================================
    if isfile(nc_fname):
        if delete_flag:
            try:
                remove(nc_fname)
            except PermissionError as err:
                print(err)
                return None

            print('Deleted: ' + nc_fname)
        else:
            print(WARNING_STR + 'NC file: ' + nc_fname + ' already exists')
            return None

    return (nc_fname, strt_year, nyears, fert_ncs)
