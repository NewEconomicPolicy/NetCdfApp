#-------------------------------------------------------------------------------
# Name:        weather_aggregation.py
# Purpose:     Functions to create and write to netCDF files and return latitude and longitude indices
# Author:      Mike Martin
# Created:     25/01/2020
# Description: taken from netcdf_funcs.py in obsolete project PstPrcssNc
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'weather_aggregation.py'
__version__ = '0.0.0'
__author__ = 's03mm5'

from os import walk, remove
from os.path import join, isdir, isfile, normpath

from copy import copy
from time import sleep
from pandas import read_excel
from xlrd import XLRDError
from glob import glob
from time import time
import csv

from spec_utilities import make_id_seg, update_progress_post, display_headers

sleepTime = 5

FUT_CLIM_SCENS = ['A1B','A2']
WTHR_RSRCE = 'Cru'
GRANULARITY = 120 # HWSD resolution - each cell is 30 arc seconds
WRT_TO_DIR = 'E:\\temp'
COMMON_HEADERS = ['province', 'latitude', 'longitude', 'mu_global', 'climate_scenario', 'num_dom_soils', 'land_use', 'area_km2']
VAR_DEFNS = {'precip': '{0:.1f}','tair': '{0:.1f}'}
MAX_SUB_DIRS = 9999999

def _process_wthr_dir(clim_dir, region_wthr_name, sub_dirs, scenario, fut_start_year = 2000, fut_end_year = 2100):
    '''
    construct output files
    '''
    size_current = csv.field_size_limit(131072 * 4)

    # header record
    # =============
    last_time = time()
    start_time = time()

    hdr_rec = copy(COMMON_HEADERS)
    for year in range(fut_start_year, fut_end_year + 1):
        for month in range(1, 13):
            hdr_rec.append('{0}-{1:0>2}'.format(str(year), str(month)))

    # create output file
    # ==================
    fobjs_out = {}
    writers = {}
    out_fnames = {}
    for varname in VAR_DEFNS:
        out_fname = join(WRT_TO_DIR, region_wthr_name + '_' + varname + '.txt')
        if isfile(out_fname):
            remove(out_fname)
        out_fnames[varname] = out_fname

        fobjs_out[varname] = open(out_fname, 'w', newline='')
        writers[varname] = csv.writer(fobjs_out[varname], delimiter='\t')
        writers[varname].writerow(hdr_rec)

    # main weather file reading loop
    # ==============================
    nsub_dirs = len(sub_dirs)
    print('Found {:>7d} directories in {}'.format(nsub_dirs, clim_dir))
    ndone, skipped, failed, warning_count = 4*[0]

    for sub_dir in sub_dirs:
        gran_lat, gran_lon = sub_dir.split('_')
        lat = 90.0 - float(gran_lat)/GRANULARITY
        lon = float(gran_lon)/GRANULARITY - 180.0

        id_seg = make_id_seg(lat, lon, scenario)

        # for each weather cell, construct two records, one for each metric
        # =================================================================
        rslts = {}
        for varname in VAR_DEFNS:
            rslts[varname] = []

        wthr_cell_dir = join(clim_dir, sub_dir)
        met_files = glob(wthr_cell_dir + '\\met2*s.txt')    # should be 101   TODO: sort
        for met_file in met_files:
            with open(met_file, 'r') as fobj:
                lines = fobj.readlines()

            for line in lines:
                dum, precip, dum, tair = line.rstrip('\n').split('\t')
                rslts['precip'].append(precip)
                rslts['tair'].append(tair)

        for varname in VAR_DEFNS:
            writers[varname].writerow(id_seg + rslts[varname])

        last_time = update_progress_post(last_time, start_time, ndone, nsub_dirs, skipped, failed, warning_count)
        ndone += 1
        if ndone >= MAX_SUB_DIRS:
            break

    # clean up
    # ========
    for varname in VAR_DEFNS:
        print('\nWrote ' + out_fnames[varname])
        fobjs_out[varname].close()

    return

def wthr_aggreg(sims_dir, regions_fname):
    '''

    '''
    display_headers()
    regions = _read_regions_file(regions_fname)
    for wthr_dir in regions['Wthr dir']:
        for fut_clim_scen in FUT_CLIM_SCENS:
            region_wthr_name = wthr_dir + WTHR_RSRCE + fut_clim_scen
            clim_dir = normpath(join(sims_dir, region_wthr_name))
            if isdir(clim_dir):

                # Gather weather directories
                # ==========================
                for directory, subdirs_raw, files in walk(clim_dir):
                    break
                del directory
                del files
                if len(subdirs_raw) > 0:
                    _process_wthr_dir(clim_dir, region_wthr_name, subdirs_raw, fut_clim_scen)
            else:
                print(clim_dir + ' does not exist')

    return

def _read_regions_file(regions_fname):
    '''
    copied verbatim from E:\AbUniv\GlblEcosseSiteSpecSv\initialise_funcs.py
    '''
    print('Will use regions definition file: ' + regions_fname)
    try:
        data = read_excel(regions_fname, sheet_name='Regions', usecols=range(0, 6))
        regions = data.dropna(how='all')
    except (PermissionError, XLRDError) as e:
        print('Error {} reading regions definition file {}'.format(e, regions_fname))
        sleep(sleepTime)
        exit(0)

    return regions

