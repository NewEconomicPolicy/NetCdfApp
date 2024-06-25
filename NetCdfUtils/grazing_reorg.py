#-------------------------------------------------------------------------------
# Name:
# Purpose:     main function to process Spec results
# Author:      Mike Martin
# Created:     11/12/2015
# Licence:     <your licence>
# Comments:    Global warming potential(GWP)
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'grazing_reorg.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

from os.path import join, isfile, isdir, split, splitext, normpath
from os import mkdir, remove
from netCDF4 import Dataset
from glob import glob
from time import time, strftime
from numpy import count_nonzero, zeros, int32, float32, float64, arange
from numpy.ma.core import MaskedConstant, MaskedArray

from locale import format_string, setlocale, LC_ALL
setlocale(LC_ALL, '')

from grazing_classes import GrazeNcDefn, create_graze_nc
from shape_funcs import calculate_area
from spec_utilities import update_progress

sleepTime = 5

KM2_TO_HECTARES = 100.0

ERROR_STR = '*** Error *** '
WARNING_STR = '*** Warning *** '

GRAZE_FN ='n_available_'

def _create_grid_cell_area_array(graze_nc, clone_defn):
    '''
    create array of cell areas
    '''
    graze_dset = Dataset(graze_nc, 'r')

    lats = graze_dset.variables['lat']
    nlats = len(lats)

    lons = graze_dset.variables['lon']
    nlons = len(lons)

    arr_tmp = arange(nlats*nlons)
    areas = arr_tmp.reshape(nlats, nlons)
    areas.dtype = float32

    resol_d2 = clone_defn.resol_d2


    for lat_indx, lat in enumerate(lats):
        lat_ll = lat - resol_d2
        lat_ur = lat + resol_d2

        bbox = list([lons[0], lat_ll, lons[1], lat_ur])
        area = calculate_area(bbox) * KM2_TO_HECTARES

        areas[lat_indx, :] = nlons*[area]       # fill longitudes for each latitude with same area
        tmp = areas[lat_indx, :10]              # for debugging

    return areas

def _integrate_grazing_dsets(lvstck_nc_fn, graze_ncs, areas):
    '''
    laboriously step through each cell
    '''
    try:  # call the Dataset constructor
        lvstck_dset = Dataset(lvstck_nc_fn, 'a')
    except PermissionError as err:
        print(err)
        return None

    for graze_nc in graze_ncs:
        graze_dset = Dataset(graze_nc, 'r')

        data = graze_dset.variables['Band1']
        nlats = graze_dset.variables['lat'].size
        nlons = graze_dset.variables['lon'].size

        root_name = splitext(split(graze_nc)[1])[0]
        anml_type = root_name.split('_')[-1]
        var_name = 'N' + anml_type
        print('\nProcessing ' + var_name)

        last_time = time()
        nvalid = 0
        nmask = 0
        nunknwn = 0
        nsize_grid = nlons*nlats

        for lat_indx in range(nlats):

            for lon_indx in range(nlons):
                val = data[lat_indx, lon_indx]

                if isinstance(val, MaskedConstant):
                    lvstck_dset.variables[var_name][lat_indx, lon_indx] = val
                    nmask += 1

                elif isinstance(val, MaskedArray):      # used isinstance(val, float32) for 1.4.2 of netCDF4 module
                    nkg_ha_ma = val / areas[lat_indx, lon_indx]  # N per hectare
                    nkg_ha = nkg_ha_ma.item()

                    lvstck_dset.variables[var_name][lat_indx, lon_indx] = nkg_ha
                    nvalid += 1

                else:
                    if nunknwn == 0:
                        print(ERROR_STR + 'unknown data type: {} at lat/lon: {} {}'.format(type(val), lat_indx, lon_indx))

                    nunknwn += 1

                last_time = update_progress(last_time, nvalid, nmask, nunknwn, nsize_grid)

            lat_indx += 1

        graze_dset.close()

    lvstck_dset.sync()
    lvstck_dset.close()

    print('\nWrote ' + lvstck_nc_fn)

    return

def integrate_grazing_dsets(form):
    """

    """
    graze_dir = form.w_lbl_fertdir.text()
    delete_flag = form.w_del_nc.isChecked()

    # check new file name and remove if necessary
    # ===========================================
    lvstck_nc_fn = join(graze_dir, GRAZE_FN + 'livestock.nc')
    if isfile(lvstck_nc_fn):
        if delete_flag:
            try:
                remove(lvstck_nc_fn)
            except PermissionError as err:
                print(err)
                return None

            print('Deleted: ' + lvstck_nc_fn)
        else:
            print(WARNING_STR + 'NC file: ' + lvstck_nc_fn + ' already exists')
            return None

    # ====================================
    graze_ncs = glob(graze_dir + '\\' + GRAZE_FN + '*.nc')
    if lvstck_nc_fn in graze_ncs:
        del(graze_ncs[lvstck_nc_fn])

    clone_defn = GrazeNcDefn(graze_ncs[-1])

    create_graze_nc(lvstck_nc_fn, clone_defn)
    areas = _create_grid_cell_area_array(graze_ncs[0], clone_defn)
    _integrate_grazing_dsets(lvstck_nc_fn, graze_ncs, areas)

    return

