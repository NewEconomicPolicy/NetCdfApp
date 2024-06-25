#-------------------------------------------------------------------------------
# Name:        weather_datasets.py
# Purpose:     script to create weather object and other functions
# Author:      Mike Martin
# Created:     31/07/2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'weather_datasets.py'
__version__ = '0.0.0'

# Version history
# ---------------
# 
from os import remove
from os.path import join, normpath, isfile, lexists
from numpy import zeros
from numpy.ma.core import MaskedArray

from netCDF4 import Dataset, num2date

from glob import glob
from unidecode import unidecode

sleepTime = 5

SCENARIOS = sorted(list(['RCP6.0', 'RCP4.5', 'RCP2.6','RCP8.5']))
PERIOD_DEFNS = {'Monthly':'Mnth', 'Daily':'Day'}
ERROR_STR = '*** Error *** '
WARNING_STR = '*** Warning *** '

def get_nc_coords(lggr, wthr_dict, latitude, longitude, print_flag = False):
    '''

    '''
    max_lat_indx = len(wthr_dict['latitudes']) - 1
    max_lon_indx = len(wthr_dict['longitudes']) - 1

    lon_ll, lat_ll, lon_ur, lat_ur = wthr_dict['bbox']
    lat_indx = round((latitude  - lat_ll)/wthr_dict['resol_lat'])
    lon_indx = round((longitude - lon_ll)/wthr_dict['resol_lon'])

    # validate lats
    # =============
    if lat_indx < 0 or lat_indx > max_lat_indx:
        mess = WARNING_STR + 'latitude index {} out of bounds'.format(lat_indx)
        mess += ' for latitude {}\tmax indx: {} - will correct'.format(round(latitude, 4), max_lat_indx)
        if print_flag:
            print(mess)
        lggr.info(mess)

        # TODO: make optional?
        # ====================
        if lat_indx < 0:
            lat_indx = 0
        if lat_indx > max_lat_indx:
            lat_indx = max_lat_indx

    # validate lons
    # =============
    if lon_indx < 0 or lon_indx > max_lon_indx:
        mess = WARNING_STR + 'longitude index {} out of bounds'.format(lon_indx)
        mess += ' for latitude {}\tmax indx: {} - will correct'.format(round(longitude, 4), max_lon_indx)
        if print_flag:
            print(mess)
        lggr.info(mess)

        # TODO: make optional?
        # ====================
        if lon_indx < 0:
            lon_indx = 0
        if lon_indx > max_lon_indx:
            lon_indx = max_lon_indx

    return lat_indx, lon_indx

def _average_slice(slice):

    ndays, nlats, nlons = slice.shape
    new_slice = zeros(ndays)

    for indx_day in range(ndays):
        day_slice = slice[indx_day, :, :]
        new_val = day_slice.mean()
        new_slice[indx_day] = new_val

    return new_slice

def _open_output_files(admin_div, out_dir, start_year, end_year):

    # delete files if exists, then open
    # =================================
    admin_div = unidecode(admin_div.replace(' ','_'))     # remove spaces and awkward characters
    fname = join(out_dir, admin_div + '_' + str(start_year) + '_' + str(end_year) + '.100')
    clim_file = normpath(fname)
    if isfile(clim_file):
        remove(clim_file)
        print('\nDeleted ' + clim_file)

    fhand_clim = open(clim_file, 'w')

    return fhand_clim, clim_file

def _fetch_weather_nc_parms(nc_fname, rsrc_name, wthr_rsrce, resol_time, time_var_name = 'time'):
    '''
    create a data record and lat/lon lists from weather datasets
        raw ECLIPS2 datasets do not have a time dimension
    '''
    nc_fname = normpath(nc_fname)
    nc_dset = Dataset(nc_fname, 'r')

    calendar_attr = 'standard'
    if time_var_name in nc_dset.variables:
        time_var = nc_dset.variables[time_var_name]
        if 'calendar' in time_var.ncattrs():
            calendar_attr = time_var.calendar
    else:
        time_var = None

    # standard names
    # ==============
    if rsrc_name == 'NASA' or rsrc_name == 'EObs':
        lat = 'latitude'
        lon = 'longitude'
    else:
        lat = 'lat'
        lon = 'lon'

    if lat not in nc_dset.variables:
        print('Latitude variable not found {} in {}'.format(lat, nc_fname))
        return None

    lat_var = nc_dset.variables[lat]
    lon_var = nc_dset.variables[lon]

    # create lat/lon lists taking into account particularities of each resource
    # =========================================================================
    if rsrc_name == 'EObs':
        lats = [round(float(lat), 3) for lat in lat_var]
        lons = [round(float(lon), 3) for lon in lon_var]
    else:
        lats = [float(lat) for lat in lat_var]
        lons = [float(lon) for lon in lon_var]

    # bounding box
    # ============
    lon_ll = min(lons)
    lon_ur = max(lons)
    lat_ll = min(lats)
    lat_ur = max(lats)

    # resolutions
    # ===========
    '''
    resol_lon = round((lon_var[-1] - lon_var[0])/(len(lon_var) - 1), 5)
    resol_lat = round((lat_var[-1] - lat_var[0])/(len(lat_var) - 1), 5)
    '''
    resol_lon = round((lons[-1] - lons[0])/(len(lons) - 1),9)
    resol_lat = round((lats[-1] - lats[0])/(len(lats) - 1),9)
    if abs(resol_lat) != abs(round(resol_lon,9)):
        print('Warning - weather resource {} has different lat/lon resolutions: {} {}'
                                                        .format(wthr_rsrce, resol_lat, resol_lon))
    if rsrc_name == 'ECLIPS2' or time_var is None:
        start_date = DummyDate()
        end_date = DummyDate()
    else:
        # Get the start and end date of the time series (as datetime objects):
        # ====================================================================
        time_var_units = time_var.units
        if isinstance(time_var[0], MaskedArray):
            start_day = int(time_var[0].item())
        else:
            start_day = time_var[0]
        try:
            start_date = num2date(start_day, units = time_var_units, calendar = calendar_attr)
        except (TypeError) as err:
            print(ERROR_STR + str(err) + ' deriving start and end year for dataset: ' + nc_fname)
            return None

        end_day = int(time_var[-1])
        end_date = num2date(end_day, units = time_var_units, calendar = calendar_attr)

    nc_dset.close()

    data_rec = {'start_year': start_date.year,  'end_year': end_date.year,
            'resol_lat': resol_lat, 'lat_frst': lats[0], 'lat_last': lats[-1], 'lat_ll': lat_ll, 'lat_ur': lat_ur,
            'resol_lon': resol_lon, 'lon_frst': lons[0], 'lon_last': lons[-1], 'lon_ll': lon_ll, 'lon_ur': lon_ur,
                    'resol_time': resol_time, 'daycent_dates': []}

    print('{} start and end year: {} {}\tresolution: {} degrees'
            .format(wthr_rsrce, data_rec['start_year'],  data_rec['end_year'], abs(data_rec['resol_lat'])))

    return data_rec, lons, lats

class DummyDate:
    def __init__(self):
        self.year = None

def read_wthr_dsets_detail(form, wthr_set_defns):
    '''
    ascertain the year span for historic datasets
    potential weather dataset resources are:
    EObs - Monthly:  from 1980-01-31 to 2017-12-31      Daily:  from 1950-01-01 to 2017-12-31
    '''
    wthr_sets = {}
    wthr_dir = form.settings['wthr_dir']
    form.scenarios = SCENARIOS

    valid_wthr_dset_rsrces = []
    for root_dir in wthr_set_defns:
        glob_str= wthr_set_defns[root_dir]['glob_str']
        precip_var = wthr_set_defns[root_dir]['precip_var']
        tas_var = wthr_set_defns[root_dir]['tas_var']

        rsrc_name = root_dir.split('_')[0]

        # check daily and monthly dsets
        # =============================
        resource_valid_flag = True
        for period_name in PERIOD_DEFNS:
            period_abbrev = PERIOD_DEFNS[period_name]

            period_dir = wthr_dir + '\\' + root_dir + '\\' + period_name
            if lexists(period_dir):

                wthr_rsrce = rsrc_name + '_' + period_abbrev
                nc_fnames = glob(period_dir + '/*' + glob_str + '*.nc')
                if len(nc_fnames) >= 2:
                    ret_code =  _fetch_weather_nc_parms(nc_fnames[0], rsrc_name, wthr_rsrce, period_name)
                    if ret_code is None:
                        resource_valid_flag = False
                        continue

                    data_rec, lons, lats = ret_code
                    wthr_sets[wthr_rsrce] = data_rec
                    wthr_sets[wthr_rsrce]['longitudes'] = lons
                    wthr_sets[wthr_rsrce]['latitudes']  = lats
                    wthr_sets[wthr_rsrce]['base_dir']   = period_dir
                    wthr_sets[wthr_rsrce]['fn_precip']  = nc_fnames[0]
                    wthr_sets[wthr_rsrce]['precip_var'] = precip_var
                    wthr_sets[wthr_rsrce]['fn_tas']     = nc_fnames[1]
                    wthr_sets[wthr_rsrce]['tas_var']    = tas_var
                    wthr_sets[wthr_rsrce]['bbox'] = list([data_rec['lon_ll'], data_rec['lat_ll'],
                                                                                data_rec['lon_ur'], data_rec['lat_ur']])
                else:
                    mess = WARNING_STR + 'Weather resource: ' + rsrc_name + ' ' + period_name.lower() + ' '
                    mess += 'Must be exactly two datasets present in ' + period_dir
                    print(mess)
                    resource_valid_flag = False
                    continue
            else:
                print(rsrc_name + ' ' + period_name.lower() + ' folder ' + period_dir + ' does not exist')
                resource_valid_flag = False
                break

        if resource_valid_flag:
            valid_wthr_dset_rsrces.append(rsrc_name)

    form.valid_wthr_dset_rsrces = sorted(valid_wthr_dset_rsrces)
    form.wthr_sets = wthr_sets

    print('')
    return True

def report_aoi_size(wthr_sets, resource, lon_ll, lat_ll, lon_ur, lat_ur):
    '''
    '''
    func_name =  __prog__ + ' report_aoi_size'

    # ====================================
    wthr_set = wthr_sets[resource]
    resol_lat = wthr_set['resol_lat']
    lat0 = wthr_set['lat0']
    resol_lon = wthr_set['resol_lon']
    lon0 = wthr_set['lon0']

    lat_indx_ll = int(round((lat_ll - lat0)/resol_lat))
    lon_indx_ll = int(round((lon_ll - lon0)/resol_lon))

    lat_indx_ur = int(round((lat_ur - lat0)/resol_lat))
    lon_indx_ur = int(round((lon_ur - lon0)/resol_lon))

    lat_indx_min = min(lat_indx_ll, lat_indx_ur)
    lat_indx_max = max(lat_indx_ll, lat_indx_ur)
    nlats = lat_indx_max - lat_indx_min + 1

    lon_indx_min = min(lon_indx_ll, lon_indx_ur)
    lon_indx_max = max(lon_indx_ll, lon_indx_ur)
    nlons = lon_indx_max - lon_indx_min + 1

    # get slice for each dataset metric
    # =================================
    mess = 'will retrieve weather for {} locations - nlats/nlons: {} x {} '.format(nlats*nlons, nlats, nlons)

    print(mess)

    return
