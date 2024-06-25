#-------------------------------------------------------------------------------
# Name:        ukcp18_fns.py
# Purpose:     Functions to create Miscanfor formatted metric files from UKCP18 RCP8.5 climate CSV files
# Author:      Mike Martin
# Created:     22/03/2020
# Description:
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'ukcp18_fns.py'
__version__ = '0.0.0'
__author__ = 's03mm5'

from os.path import isdir, split, exists, join, isfile, splitext
from time import time
from math import sqrt
from pandas import read_csv, DataFrame

from locale import setlocale, format_string, LC_ALL
setlocale(LC_ALL, '')

from spec_utilities import update_progress

MAX_VALS   = 500000
READ_FLAG = True

METEO_FN = 'E:\\CHESS_data_monthly\\miscanfor\\meteo_lat_lon_osgb.csv'
AOI_FN = 'E:\\GlobalEcosseData\\Hwsd_CSVs\\UK\\vault\\Wales_hwsd.csv'
AOI_FN = 'E:\\GlobalEcosseData\\Hwsd_CSVs\\UK\\GBR_hwsd.csv'
AOI_HEADERS = ['gran_lat', 'gran_lon', 'mu_global', 'lat', 'lon']

ERROR_STR = '*** Error *** '


def _find_nearset_chess_location(meteogrid_df, lat, lon):
    """
    read a CHESS file and write a lookup table to a CSV file
    """

    meteogrid_df['cdist'] = [(sqrt((lat - pnt[0]) ** 2 + (lon - pnt[1]) ** 2)) for pnt in meteogrid_df['point']]
    recid_nrst = meteogrid_df['cdist'].idxmin()
    xindx, yindx = meteogrid_df['xindx'][recid_nrst], yindx = meteogrid_df['yindx'][recid_nrst]

    return xindx, yindx

def _make_lookup_table_from_meteogrid_csv(meteogrid_df):
    """
    read a CHESS file and write a lookup table to a CSV file
    """

    mappings_df = DataFrame()
    aoi_df = read_csv(AOI_FN, sep=',', names=AOI_HEADERS)
    num_total = len(aoi_df)
    print('\nAOI HWSD file has {} records'.format(num_total))

    nmask = 0
    nunknwn = 0
    num_vals = 0
    last_time = time()

    lats = []
    lons = []
    nrthings = []
    estings = []
    x_indices = []
    y_indices = []
    for lat, lon in zip(aoi_df['lat'], aoi_df['lon']):

        lats.append(lat)
        lons.append(lon)

        # find_nearset_chess_location
        # ===========================
        meteogrid_df['cdist'] = [(sqrt((lat - pnt[0]) ** 2 + (lon - pnt[1]) ** 2)) for pnt in meteogrid_df['point']]
        rec_id_nrst = meteogrid_df['cdist'].idxmin()
        xindx = meteogrid_df['xindx'][rec_id_nrst]
        x_indices.append(xindx)
        esting = meteogrid_df['easting'][rec_id_nrst]
        estings.append(esting)

        yindx = meteogrid_df['yindx'][rec_id_nrst]
        y_indices.append(yindx)
        nrthing = meteogrid_df['northing'][rec_id_nrst]
        nrthings.append(nrthing)

        last_time = update_progress(last_time, num_vals, nmask, nunknwn, num_total)

        num_vals += 1
        if num_vals > MAX_VALS:
            print('\nnumber of vals: {}\texceeds requested: {}'.format(num_vals, MAX_VALS))
            break

    mappings_df['lat'] = lats
    mappings_df['lon'] = lons
    mappings_df['northing'] = [int(nrthng) for nrthng in nrthings]
    mappings_df['easting'] = [int(esting) for esting in estings]
    mappings_df['yindx'] = y_indices
    mappings_df['xindx'] = x_indices

    #mreturn mappings_df.sort_values(by=['lat', 'lon'], ascending=[False, True])
    return mappings_df

def make_chess_lookup_table(form):
    """

    """

    # =======================================
    meteogrid_df = read_csv(METEO_FN, sep=',')
    meteogrid_df['point'] = [(lat, lon) for lat, lon in zip(meteogrid_df['cell_lat'], meteogrid_df['cell_lon'])]

    mppngs_df = _make_lookup_table_from_meteogrid_csv(meteogrid_df)

    root_dir, short_fn = split(AOI_FN)
    root_name, dummy = splitext(short_fn)
    aoi_mppngs_fn = join(root_dir, root_name + '_lkup_tble.csv')
    try:
        mppngs_df.to_csv(aoi_mppngs_fn, index=False, header=True)
        mess = '\nOSGB lookup table creation complete having written {} mappings'.format(len(mppngs_df))
        mess += '\n\tto file: ' + aoi_mppngs_fn
        print(mess)

    except PermissionError as err:
        print('Could not create ' + aoi_mppngs_fn + ' due to: ' + str(err))

    return
