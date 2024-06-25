#-------------------------------------------------------------------------------
# Name:        jinfeng_classes.py
# Purpose:     Functions to create and write to netCDF files and return latitude and longitude indices
# Author:      Mike Martin
# Created:     25/08/2022
# Description:
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'jinfeng_classes.py'
__version__ = '0.0.0'
__author__ = 's03mm5'

from os.path import isfile, join, isdir
from os import remove, makedirs
from time import time, strftime
from netCDF4 import Dataset
from numpy import arange, nan as NaN

ERROR_STR = '*** Error *** '
WARNING_STR = '*** Warning *** '

class NcFileDefn(object, ):
    '''
    instantiate new dataset based on Jinfeng lat/lon extents
    '''
    def __init__(self, nc_fname):
        """

        """
        nc_dset = Dataset(nc_fname, 'r')

        # expand bounding box to make sure all results are included
        # =========================================================
        lats = nc_dset.variables['LAT'][:, 0]
        nlats = len(lats)
        lat_ur = lats[0]
        lat_ll = lats[-1]
        resol_lats = (lat_ur - lat_ll) / (nlats - 1)

        lons = nc_dset.variables['LON'][0, :]
        nlons = len(lons)
        lon_ur = lons[-1]
        lon_ll = lons[0]
        resol_lons = (lon_ur - lon_ll) / (nlons - 1)

        if resol_lats != resol_lons:
            print(ERROR_STR + 'Resolution of lats: {}\tand longs: {} differ'.format(resol_lats, resol_lons))
        else:
            print('Dataset spatial resolution: {}'.format(resol_lats))

        self.nc_fname = nc_fname
        self.resol = resol_lats
        self.nlats = nlats
        self.lats = lats
        self.nlons = nlons
        self.lons = lons
        self.years = lons
        self.bbox = list([lon_ll, lat_ll, lon_ur, lat_ur])

        nc_dset.close()

def create_fert_nc(nc_fname, clone_defn, strt_year, nyears):
    '''
    createVariable method has arguments:
               first: variable name, second: datatype, third: tuple with the name(s) of the dimension(s)
    '''
    try:  # call the Dataset constructor to create file
        nc_dset = Dataset(nc_fname, 'w', format='NETCDF4_CLASSIC')
    except PermissionError as err:
        print(err)
        return None

    try:
        clone_dset = Dataset(clone_defn.nc_fname, 'r')
    except PermissionError as err:
        print(err)
        return None

    # create global attributes
    # =======================
    date_stamp = strftime('%H:%M %d-%m-%Y')
    nc_dset.attribution = 'Created at ' + date_stamp + ' for Spatial Ecosse SuperG grasslands project'
    nc_dset.history = 'SuperG'
    nc_dset.dataUsed = 'Jinfeng'

    # ==========================================================================
    data_used = 'Data used: from Jinfeng May 2022'
    nc_dset.dataUsed = data_used

    # expand bounding box to make sure all results are included
    # =========================================================
    lon_ll, lat_ll, lon_ur, lat_ur = clone_defn.bbox

    resol = clone_defn.resol

    # create dimensions
    # =================
    nc_dset.createDimension('lat', clone_defn.nlats)
    nc_dset.createDimension('lon', clone_defn.nlons)
    nc_dset.createDimension('time', nyears)

    # create the lat/lon variables (4 byte float in this case)
    # ========================================================
    lats = nc_dset.createVariable('lat', 'f4', ('lat',))
    lats.description = 'degrees of latitude North to South in ' + str(resol) + ' degree steps'
    lats.units = 'degrees_north'
    lats.long_name = 'latitude'
    lats.axis = 'Y'
    lats[:] = clone_defn.lats

    lons = nc_dset.createVariable('lon', 'f4', ('lon',))
    lons.description = 'degrees of longitude West to East in ' + str(resol) + ' degree steps'
    lons.units = 'degrees_east'
    lons.long_name = 'longitude'
    lons.axis = 'X'
    lons[:] = clone_defn.lons

    # setup time dimension - asssume daily
    # ====================================
    mess = 'Number of longitudes: {}\tlatitudes: {}\tyears: {}'.format(clone_defn.nlons, clone_defn.nlats, nyears)
    print(mess)

    times = nc_dset.createVariable('time', 'i4', ('time',))
    times.units = 'year'
    times.calendar = 'standard'
    times.axis = 'T'
    times[:] = arange(strt_year, strt_year + nyears)

    # Create N deposition, Nmanure and Nmineral variables
    # ===================================================
    var_name = 'Ndep'
    missing_value = clone_dset.variables[var_name].missing_value
    ndep = nc_dset.createVariable(var_name, 'f4', ('time', 'lat', 'lon'), fill_value=missing_value)
    ndep.long_name = 'Oxidised nitrogen'
    ndep.units = clone_dset.variables[var_name].units
    ndep.missing_value = NaN

    var_name = 'Nmanure'
    nmanure = nc_dset.createVariable(var_name, 'f4', ('time', 'lat', 'lon'), fill_value=missing_value)
    nmanure.long_name = 'manure'
    nmanure.units = clone_dset.variables[var_name].units
    ndep.missing_value = NaN    # previous: nmanure.missing_value = clone_dset.variables[var_name].missing_value

    var_name = 'Nmineral'
    nmineral = nc_dset.createVariable(var_name, 'f4', ('time', 'lat', 'lon'), fill_value=missing_value)
    nmineral.long_name = 'synthetic fertiliser'
    nmineral.units = clone_dset.variables[var_name].units
    ndep.missing_value = NaN

    # close netCDF files
    # ==================
    nc_dset.sync()
    nc_dset.close()
    clone_dset.close()

    print('Created: ' + nc_fname + '\n')
    return
