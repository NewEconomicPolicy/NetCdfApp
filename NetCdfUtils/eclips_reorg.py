#-------------------------------------------------------------------------------
# Name:
# Purpose:     main function to process Spec results
# Author:      Mike Martin
# Created:     11/12/2015
# Licence:     <your licence>
# Comments:    Global warming potential(GWP)
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'eclips_reorg.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

from os.path import join, isfile, isdir, split
from netCDF4 import Dataset, date2index, date2num, num2date
from glob import glob
from copy import copy
from numpy.ma import masked as MaskedConstant
from time import time
from _datetime import datetime

from locale import format_string, setlocale, LC_ALL
setlocale(LC_ALL, '')

from spec_utilities import update_progress_post
from weather_datasets import read_wthr_dsets_detail, get_nc_coords
from eclips_classes import create_eclips_nc, EclipsNcDefn

sleepTime = 5

HECTARES_TO_M2 = 0.0001

ERROR_STR = '*** Error *** '
WARNING_STR = '*** Warning *** '

METRIC_DESCR = {'Precipalign':'precipitation', 'Tairalign':'temperature'}

ROOT_WTHR = 'E:\\GlobalEcosseData\\'
HARMONIE = ROOT_WTHR + 'HARMONIE_V2\\Monthly\\'
ECLIPS_OUT = ROOT_WTHR + 'ECLIPS2_GlEc\\Monthly\\'

ECLIPS_INP_DIR = 'E:\\Mohamed\\ECLIPS2.0_ncs\\'

YEAR_RANGE = '_1961_2100'

PREFIX = 'ECLIPS2_0_'
HIST_YR_RNG_LIST = ['196190','199110']
FUT_YR_RNG_LIST = list(['201120', '202140','204160', '206180', '208100'])

SCENARIOS = {'RCP60':'_6.0', 'RCP45':'_4.5', 'RCP26':'_2.6', 'RCP85':'_8.5'}
del SCENARIOS['RCP60']
del SCENARIOS['RCP26']

WTHR_SET_DEFNS = {'ECLIPS2':{'precip_var':'Precipalign', 'tas_var': 'Tairalign', 'glob_str':'[PPT-Tave]'},
                    'ECLIPS2TMPLT': {'precip_var':'Band1', 'tas_var': 'Band1', 'glob_str':'[PPT-Tave]'},
                    'EObs_v23': {'precip_var':'pp', 'tas_var': 'tg', 'glob_str':'[rr-tg]'},
                    'HARMONIE_V2': {'precip_var':'Precipalign', 'tas_var': 'Tairalign', 'glob_str':'cruhar_v3_1_19'}}
del(WTHR_SET_DEFNS['EObs_v23'])

def populate_eclips_dsets(form):
    """

    """
    scenario = form.w_combo10.currentText()
    gcm = form.w_combo11.currentText()
    populate_hist_flag = form.w_pop_hist.isChecked()
    populate_fut_flag = form.w_pop_fut.isChecked()

    if form.w_tave_only.isChecked():
        tave_only_flag = True
        print(WARNING_STR + 'only temperature will be processed')
    else:
        tave_only_flag = False

    # reduce time taken for reading weatherset details
    # ================================================
    wthr_defns = copy(WTHR_SET_DEFNS)
    for set_name in ['EObs_v23', 'HARMONIE_V2']:
        if set_name in wthr_defns:
            del wthr_defns[set_name]

    if not read_wthr_dsets_detail(form, wthr_defns):
        return None

    for wthr_set in ['ECLIPS2_Mnth', 'ECLIPS2TMPLT_Mnth']:
        if wthr_set not in form.wthr_sets:
            print(wthr_set + ' must be present in weather sets')
            return

    eclips_wthr_dict = form.wthr_sets['ECLIPS2_Mnth']
    tmplt_wthr_dict = form.wthr_sets['ECLIPS2TMPLT_Mnth']

    strt_yr_data, end_yr = _fetch_decades(HIST_YR_RNG_LIST[0])      # start year expected to be 1961

    # ========================= historic data ========================
    if not populate_hist_flag:
        print('*** populate historic weather flag not set - will skip ***')
    else:
        for fn_metric, metric_inp, metric in zip(['fn_precip', 'fn_tas'], ['PPT', 'Tave'], ['Precipalign', 'Tairalign']):

            # ski precipitation
            # =================
            if tave_only_flag and metric == 'Precipalign':
                continue

            # time step is monthly and index zero is Jan 1961
            # ===============================================
            for yr_rng in HIST_YR_RNG_LIST:
                nc_dir = join(ECLIPS_INP_DIR, PREFIX + yr_rng)
                nc_fns = glob(nc_dir + '\\' + metric_inp + '*.nc')
                print('Metric ' + metric_inp + ': {} files in '.format(len(nc_fns)) + nc_dir)

                strt_yr, end_yr = _fetch_decades(yr_rng)

                # loop to step through sets of 12 months
                # ======================================
                mess = 'Populating dataset ' + eclips_wthr_dict[fn_metric] + '\n\tmetric: ' + metric_inp
                mess += '\twith historic data for year range ' + yr_rng
                print(mess + '\n')
                if not populate_hist_flag:
                    print('*** populate flag not set - will skip ***')
                    continue

                for nc_fname in nc_fns:
                    imnth = _fetch_imnth(nc_fname, metric_inp)
                    if imnth is None:
                        break

                    ret_code = _slice_resize(form.lgr, tmplt_wthr_dict, nc_fname, eclips_wthr_dict, fn_metric, metric,
                                                        imnth, strt_yr_data, strt_yr, end_yr, process_data_flag = True)
                    if not ret_code:
                        return None

            print('End of historic data for metric ' + metric_inp + '\n')

    # ========================= future data ========================
    if not populate_fut_flag:
        print('*** populate future weather flag not set - will skip ***')
    else:
        # check NC files for this GCM exists
        # ==================================
        nc_dir = join(ECLIPS_INP_DIR, PREFIX + scenario, gcm + SCENARIOS[scenario])
        if not isdir(nc_dir):
            print(nc_dir + ' does not exist')
            return None

        print('Processing future data from: ' + nc_dir + ' scenario: ' + scenario + ' GCM: ' + gcm)

        for fn_metric, metric_inp, metric in zip(['fn_precip', 'fn_tas'], ['PPT', 'Tave'],
                                                                                ['Precipalign', 'Tairalign']):
            # skip precipitation
            # ==================
            if tave_only_flag and metric == 'Precipalign':
                continue

            print('Populating dataset ' + eclips_wthr_dict[fn_metric] + ' with future data')

            for yr_rng in FUT_YR_RNG_LIST:

                nc_fns = glob(nc_dir + '\\' + metric_inp + '*' + yr_rng + '.nc')
                print('{} files in '.format(len(nc_fns)) + nc_dir + ' for year range ' + yr_rng)

                strt_yr, end_yr = _fetch_decades(yr_rng)

                for nc_fname in nc_fns:
                    imnth = _fetch_imnth(nc_fname, metric_inp)
                    if imnth is None:
                        break

                    mess = 'Will copy ' + metric_inp + ' data from: ' + nc_fname + '\n\t'
                    mess += ' covering year range ' + yr_rng + ' and scenario ' + scenario
                    print(mess + '\n')
                    ret_code = _slice_resize(form.lgr, tmplt_wthr_dict, nc_fname, eclips_wthr_dict, fn_metric,
                                            metric, imnth, strt_yr_data, strt_yr, end_yr, process_data_flag=True)
                    if not ret_code:
                        return None

            print('End of future data for scenario: ' + scenario + ' metric: ' + metric_inp + '\n')

    return None

def _slice_resize(lggr, inpt_wthr_dict, inpt_fname, eclips_wthr_dict, fn_metric, metric,
                                                imnth, strt_yr_data, strt_yr, end_yr, process_data_flag = False):
    """
    step through each lat, lon from new weather dataset
    create a lat lon bbox for each grid point
    retrieve mini-slice from band_lice and average the mini-slice values and record in

    after creating one-mini slice copy to next 30 (or however many years) metric variable timesteps
    """
    eclips_fn = eclips_wthr_dict[fn_metric]
    try:
        eclips_dset = Dataset(eclips_fn, 'a')
    except TypeError as err:
        print('Unable to open output file {} error: {}'.format(eclips_fn, err))
        return False

    inpt_dset = Dataset(inpt_fname, 'r')

    strt_date = datetime(strt_yr, imnth, 15)
    mnth_name = strt_date.strftime("%B")
    mess = 'Generating ' + METRIC_DESCR[metric]
    print(mess + ' slices for {} for years {} to {}'.format(mnth_name, strt_yr, end_yr))
    nyears = end_yr - strt_yr + 1

    resol_d2 = eclips_wthr_dict['resol_lon']/ 2.0

    strt_time = time()
    last_time = time()
    nmasked = 0
    nout_of_area = 0
    nvalid = 0
    nwarns = 0
    lats = eclips_wthr_dict['latitudes']
    lons = eclips_wthr_dict['longitudes']
    nsize_grid = len(lats)*len(lons)
    time_indx = imnth - 1 + (strt_yr - strt_yr_data)*12

    # main loop to create a metric slice for this month
    # =================================================
    if process_data_flag:
        for lat in eclips_wthr_dict['latitudes']:
            for lon in eclips_wthr_dict['longitudes']:

                # check mask
                # ==========
                lat_indx, lon_indx = get_nc_coords(lggr, eclips_wthr_dict, lat, lon)
                if eclips_dset.variables['lsmask'][lat_indx,lon_indx] == 1:

                    lat_ll_indx, lon_ll_indx = get_nc_coords(lggr, inpt_wthr_dict, lat - resol_d2, lon - resol_d2)
                    lat_ur_indx, lon_ur_indx = get_nc_coords(lggr, inpt_wthr_dict, lat + resol_d2, lon + resol_d2)
                    if lat_ll_indx == 0 and lat_ur_indx == 0:
                        nout_of_area += 1

                    mini_slice = inpt_dset.variables['Band1'][lat_ll_indx:lat_ur_indx, lon_ll_indx:lon_ur_indx]
                    if mini_slice is MaskedConstant:
                        nmasked += 1
                    else:
                        val = mini_slice.mean()
                        eclips_dset.variables[metric][time_indx, lat_indx, lon_indx] = val
                        nvalid += 1

                    last_time = update_progress_post(last_time, strt_time, nvalid, nsize_grid, nout_of_area, nmasked, nwarns)

    inpt_dset.close()

    # copy slice for each of years
    # ============================
    print('\nreplicating slice for year {} to each of years from {} to {}'.format(strt_yr, strt_yr + 1, end_yr))
    if process_data_flag:
        this_slice = eclips_dset.variables[metric][time_indx, :, :]
        time_tmp_indx = time_indx
        for yr in range(strt_yr + 1, end_yr + 1):
            time_tmp_indx += 12
            eclips_dset.variables[metric][time_tmp_indx, :, :] = this_slice

    valid_str = format_string("%d", nvalid, grouping=True)
    mess = 'populated {}\twith {} years of '.format(split(eclips_fn)[1], nyears) + METRIC_DESCR[metric] + ' data'
    print('\n*** ' + mess + ' with ' + valid_str + ' valid values for each slice ***\n')

    eclips_dset.sync()
    eclips_dset.close()

    return True

def _fetch_decades(yr_rng):
    """
    typical directory substring: 199110
    """
    cntry = int(yr_rng[:2] + '00')
    strt_yr = int(yr_rng[:4])

    end_dcd = yr_rng[4:]
    if end_dcd == '10' and cntry == 1900:
        end_yr = int('20' + end_dcd)
    else:
        end_yr = int(yr_rng[:2] + end_dcd)
        if end_yr == 2000 and strt_yr > end_yr:
            end_yr += 100

    return strt_yr, end_yr

def _fetch_imnth(nc_fname, metric):
    """
    extract month from file name e.g. PPT04_196190.nc
    """
    shrt_fn = split(nc_fname)[1]
    prefix = shrt_fn.split('_')[0]
    try:
        imnth = int(prefix.lstrip(metric))
    except ValueError as err:
        print(ERROR_STR + 'Prefix ' + prefix + '\t' + str(err))
        return None

    return imnth
def _copy_land_sea_mask(lggr, fn_metric, eclips_wthr_dict, clone_wthr_dict):
    """

    """
    # open the newly created and clone NC files
    # =========================================
    eclips_fn = eclips_wthr_dict[fn_metric]
    try:
        eclips_dset = Dataset(eclips_fn, 'a', format='NETCDF4')
    except TypeError as err:
        print('Unable to open output file {} error: {}'.format(eclips_fn, err))
        return

    clone_fn = clone_wthr_dict[fn_metric]
    try:
        clone_dset = Dataset(clone_fn, 'r', format='NETCDF4')
    except TypeError as err:
        print('Unable to open clone file {} error: {}'.format(clone_fn, err))
        return

    # locate origin from where mask will be copied from clone dataset (HARMONIE)
    # =========================================================================
    lat_indx_min, lon_indx_min = get_nc_coords(lggr, clone_wthr_dict,
                                               eclips_wthr_dict['lat_ll'], eclips_wthr_dict['lon_ll'])

    lat_indx_max, lon_indx_max = get_nc_coords(lggr, clone_wthr_dict,
                                               eclips_wthr_dict['lat_ur'], eclips_wthr_dict['lon_ur'])
    # copy land-sea mask
    # ==================
    lat_indx_max += 1       # TODO: nail down this discrepancy
    lon_indx_max += 1
    try:
        slice = clone_dset.variables['lsmask'][lat_indx_min:lat_indx_max, lon_indx_min:lon_indx_max]
    except RuntimeWarning as err:
        print(err)

    try:
        eclips_dset.variables['lsmask'][:,:] = slice
    except (KeyError, ValueError) as err:
        print(ERROR_STR + 'copying land-sea mask: ' + str(err))

    clone_dset.close()
    eclips_dset.sync()
    eclips_dset.close()

    print('\n*** Finished - having copied land-sea mask to NC file: ' + eclips_fn + '\n')

    return

def make_empty_eclips_dsets(form):
    """

    """
    delete_flag = form.w_del_nc.isChecked()
    scenario = form.w_combo10.currentText()

    out_dir = join(form.settings['wthr_dir'], 'ECLIPS2', 'Monthly')

    # start with just two weather set definitions
    # ===========================================
    required_rsces = ['ECLIPS2TMPLT', 'HARMONIE_V2']
    wthr_set_defns = {rsrc: WTHR_SET_DEFNS[rsrc] for rsrc in required_rsces}
    if not read_wthr_dsets_detail(form, wthr_set_defns):
        return

    '''
        for wthr_rsce in required_rsces:
        if wthr_rsce not in form.wthr_sets:
            print(ERROR_STR + 'weather resource ' + wthr_rsce + ' must be present')
            return
    '''
    clone_wthr_dict = form.wthr_sets['HARMONIE_Mnth']
    
    # main loop
    # =========
    for fn_metric, metric_out, metric in zip(['fn_precip', 'fn_tas'], ['PPT', 'Tave'], ['Precipalign', 'Tairalign']):

        # deletes existing NC file if requested
        # =====================================
        eclips_defn = EclipsNcDefn(form.wthr_sets, metric_out, scenario, YEAR_RANGE, out_dir, delete_flag)
        if eclips_defn.nc_fname is None:
            continue    # applies when nc file already exists but could not delete

        if delete_flag or not isfile(eclips_defn.nc_fname):

            # remake nc file and copy land-sea mask from HARMONIE dataset
            # ===========================================================
            clone_fn = clone_wthr_dict[fn_metric]
            nc_fname = create_eclips_nc(eclips_defn, clone_fn, metric)
            if nc_fname is None:
                continue

    # reload weather set definitions
    # ==============================
    wthr_set_defns = {}
    for rsrc in ['ECLIPS2', 'HARMONIE_V2']:
        wthr_set_defns[rsrc] = WTHR_SET_DEFNS[rsrc]

    # reread definitions TODO: improve
    # ================================
    if read_wthr_dsets_detail(form, wthr_set_defns):

        # copy land-sea mask
        # ==================
        for fn_metric in ['fn_precip', 'fn_tas']:
            try:
                eclips_wthr_dict = form.wthr_sets['ECLIPS2']
            except KeyError as err:
                print(ERROR_STR + 'key ' + err + ' not present')
                break

            _copy_land_sea_mask(form.lgr, fn_metric, eclips_wthr_dict, clone_wthr_dict)

    return