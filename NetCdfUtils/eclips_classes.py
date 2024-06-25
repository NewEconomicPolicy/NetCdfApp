#-------------------------------------------------------------------------------
# Name:        eclips_classes.py
# Purpose:     Functions to create and write to netCDF files and return latitude and longitude indices
# Author:      Mike Martin
# Created:     25/01/2017
# Description: create dimensions: "longitude", "latitude" and "time"
#              create five ECOSSE variables i.e. 'n2o','soc','co2', 'no3', and 'ch4'
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'eclips_classes.py'
__version__ = '0.0.0'
__author__ = 's03mm5'

from os.path import isfile, join, isdir
from os import remove, makedirs
from time import strftime
from netCDF4 import Dataset
from numpy import arange, float32

from nc_low_level_fns import generate_mnthly_atimes

WARNING_STR = '*** Warning *** '

# should give 304 latitudes and 560 longitudes
# ============================================
HRMN_RESOL = 0.125  # degrees
HARMONIE_BBOX =   [-24.9375, 35.0625, 45.0625, 73.0625]     #  lon_ll, lat_ll, lon_ur, lat_ur
NYEARS = 41                                                 # should give 14,965 time steps if no leap years
NDAY_STRT = 25202; NDAY_END = 43098     # take days extents from HARMONIE daily datasets 41 years 365 + 12 leap years
MISSING_VALUE = -999.0

def create_eclips_nc(eclips_defn, clone_fn, metric):
    """
    create Eclips NC based on HARMONIE
    """
    func_name =  __prog__ + ' create_eclips_nc'

    eclips_fn = eclips_defn.nc_fname
    if isfile(eclips_fn):
        print(WARNING_STR + eclips_fn + ' already exists - will skip reconstruction')
        return eclips_fn

    # call the Dataset constructor to create file
    # ===========================================
    try:
        nc_dset = Dataset(eclips_fn, 'w', format='NETCDF4_CLASSIC')
    except PermissionError as err:
        print(err)
        return None

    clone_dset = Dataset(clone_fn, 'r')

    # create global attributes
    # ========================
    date_stamp = strftime('%H:%M %d-%m-%Y')
    nc_dset.attributation = 'Created at ' + date_stamp + ' from Spatial Ecosse'
    nc_dset.history = 'SuperG'

    clim_dset = 'dummy'
    data_used = 'Data used: HWSD soil and {} weather dataset'.format(clim_dset)
    nc_dset.weather_dataset = clim_dset
    nc_dset.dataUsed = data_used

    # expand bounding box to make sure all results are included
    # =========================================================
    lon_ll, lat_ll, lon_ur, lat_ur = eclips_defn.bbox
    resol = HRMN_RESOL

    # build lat long arrays
    # =====================
    alons = arange(lon_ll, lon_ur, resol, dtype=float32)
    alats = arange(lat_ll, lat_ur, resol, dtype=float32)
    num_alons = len(alons)
    num_alats = len(alats)
 
    # setup time dimension - asssume daily
    # ====================================
    atimes, atimes_strt, atimes_end = generate_mnthly_atimes(eclips_defn.strt_yr, eclips_defn.nmonths)  # create ndarrays

    mess = 'Number of longitudes: {}\tlatitudes: {}\tmonths: {}'.format(num_alons, num_alats, eclips_defn.nmonths)
    print(mess)

    # create dimensions
    # =================
    nc_dset.createDimension('lat', num_alats)
    nc_dset.createDimension('lon', num_alons)
    nc_dset.createDimension('time', len(atimes))
    nc_dset.createDimension('bnds', 2)

    # create the variable (4 byte float in this case)
    # createVariable method has arguments:
    #   first: name of the , second: datatype, third: tuple with the name (s) of the dimension(s).
    # ===================================
    lats = nc_dset.createVariable('lat', 'f4', ('lat',))
    lats.description = 'degrees of latitude North to South in ' + str(resol) + ' degree steps'
    lats.units = 'degrees_north'
    lats.long_name = 'latitude'
    lats.axis = 'Y'
    lats[:] = alats

    lons = nc_dset.createVariable('lon', 'f4', ('lon',))
    lons.description = 'degrees of longitude West to East in ' + str(resol) + ' degree steps'
    lons.units = 'degrees_east'
    lons.long_name = 'longitude'
    lons.axis = 'X'
    lons[:] = alons

    times = nc_dset.createVariable('time', 'f4', ('time',))
    times.units = 'days since 1900-01-01'
    times.calendar = 'standard'
    times.axis = 'T'
    times.bounds = 'time_bnds'
    times[:] = atimes

    # create time_bnds variable
    # =========================
    time_bnds = nc_dset.createVariable('time_bnds', 'f4', ('time', 'bnds'), fill_value=MISSING_VALUE)
    time_bnds._ChunkSizes = 1, 2
    time_bnds[:, 0] = atimes_strt
    time_bnds[:, 1] = atimes_end

    # create land-sea mask variable
    # =============================
    var_name = 'lsmask'
    lsmask = nc_dset.createVariable(var_name, 'i2', ('lat', 'lon'), fill_value=MISSING_VALUE)
    lsmask.long_name = clone_dset.variables[var_name].long_name
    lsmask.units = clone_dset.variables[var_name].units
    lsmask.comment = clone_dset.variables[var_name].comment

    # create the time dependent metrics and assign default data
    # =========================================================
    missing_value = clone_dset.variables[metric].missing_value
    var_metric = nc_dset.createVariable(metric, 'f4', ('time', 'lat', 'lon'), fill_value=missing_value)
    var_metric.long_name = 'Average temperature at surface'
    var_metric.units = 'Degrees C'
    var_metric.alignment = clone_dset.variables[metric].alignment
    var_metric.missing_value = missing_value

    # close netCDF file
    # ================
    nc_dset.sync()
    nc_dset.close()
    clone_dset.close()

    print('Created: ' + eclips_fn + '\n')
    # form.lgr.info()

    return eclips_fn

class EclipsNcDefn(object, ):
    '''
    instantiate new ECLIPS dataset based on HARMONIE
    '''
    def __init__(self, wthr_sets, metric_out, scenario, year_range, out_dir, delete_flag = True):
        """

        """
        if not isdir(out_dir):
            makedirs(out_dir)

        nc_fname =  join(out_dir, metric_out + '_' + scenario + year_range + '.nc')
        if isfile(nc_fname):
            if delete_flag:
                try:
                    remove(nc_fname)
                    print('Deleted: ' + nc_fname)
                except PermissionError:
                    print('File: {} already exists but could not delete'.format(nc_fname))
                    nc_fname = None
            else:
                print('File ' + nc_fname + ' already exists')

        self.nc_fname = nc_fname

        # deconstruct year range
        # ======================
        dummy, strt_yr, end_yr = year_range.split('_')
        strt_yr = int(strt_yr)
        end_yr = int(end_yr)
        self.strt_yr = strt_yr
        self.end_yr = end_yr
        self.nmonths = (end_yr - strt_yr + 1)*12

        # expand bounding box to make sure all results are included
        # =========================================================
        eclips_set = wthr_sets['ECLIPS2TMPLT_Mnth']
        harmonie_dict = wthr_sets['HARMONIE_Mnth']
        resol = HRMN_RESOL
        resol_d2 = resol / 2.0

        lon_ll = resol * int(eclips_set['lon_ll'] / resol) - resol_d2
        lat_ll = resol * int(eclips_set['lat_ll'] / resol) - resol_d2
        if lat_ll < harmonie_dict['lat_ll']:
            lat_ll = harmonie_dict['lat_ll']

        # Extend the upper right coords so that alons and alats arrays encompass data
        # ===========================================================================
        lon_ur = resol * int(eclips_set['lon_ur'] / resol) + resol + resol_d2
        lat_ur = resol * int(eclips_set['lat_ur'] / resol) + resol + resol_d2
        if lat_ur > harmonie_dict['lat_ur']:
            lat_ur = harmonie_dict['lat_ur']

        self.bbox = list([lon_ll, lat_ll, lon_ur, lat_ur])
