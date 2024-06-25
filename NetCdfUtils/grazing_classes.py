#-------------------------------------------------------------------------------
# Name:
# Purpose:     Functions to create and write to netCDF files and return latitude and longitude indices
# Author:      Mike Martin
# Created:     25/08/2022
# Description:
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'grazing_classes.py'
__version__ = '0.0.0'
__author__ = 's03mm5'

from os.path import isfile, join, isdir
from os import remove, makedirs
from time import time, strftime
from netCDF4 import Dataset
from numpy import arange, float32

ERROR_STR = '*** Error *** '
WARNING_STR = '*** Warning *** '

class GrazeNcDefn(object, ):
    '''
    instantiate new dataset based on Jinfeng lat/lon extents
    '''
    def __init__(self, nc_fname):
        """

        """
        nc_dset = Dataset(nc_fname, 'r')

        # expand bounding box to make sure all results are included
        # =========================================================
        lats = nc_dset.variables['lat'][:]
        nlats = len(lats)
        lat_ur = lats[-1]
        lat_ll = lats[0]
        resol_lats = (lat_ur - lat_ll) / (nlats - 1)

        lons = nc_dset.variables['lon'][:]
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
        self.resol_d2 = resol_lats/2
        self.nlats = nlats
        self.lats = lats
        self.nlons = nlons
        self.lons = lons
        self.years = lons
        self.bbox = list([lon_ll, lat_ll, lon_ur, lat_ur])

        nc_dset.close()

def create_graze_nc(nc_fname, clone_defn):
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
    nc_dset.dataUsed = 'N added by grazing animals: https://www.fao.org/gleam/resources/en/'

    # ==========================================================================
    data_used = 'Data used: from FAO May 2022'
    nc_dset.dataUsed = data_used

    # expand bounding box to make sure all results are included
    # =========================================================
    lon_ll, lat_ll, lon_ur, lat_ur = clone_defn.bbox

    resol = clone_defn.resol

    # create dimensions
    # =================
    nc_dset.createDimension('lat', clone_defn.nlats)
    nc_dset.createDimension('lon', clone_defn.nlons)

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
    mess = 'Number of longitudes: {}\tlatitudes: {}'.format(clone_defn.nlons, clone_defn.nlats)
    print(mess)
  
    # Create N deposition, Nmanure and Nmineral variables
    # ===================================================
    units = 'kg of N (produced by livestock) per cell'
    var_name = 'Ncattle'
    missing_value = clone_dset.variables['Band1']._FillValue
    ncattle = nc_dset.createVariable(var_name, 'f4', ('lat', 'lon'), fill_value=missing_value)
    ncattle.long_name = 'cattle'
    ncattle.units = units
    ncattle.missing_value = missing_value

    var_name = 'Ngoats'
    ngoats = nc_dset.createVariable(var_name, 'f4', ('lat', 'lon'), fill_value=missing_value)
    ngoats.long_name = 'goats'
    ngoats.units = units
    ngoats.missing_value = missing_value

    var_name = 'Nsheep'
    nsheep = nc_dset.createVariable(var_name, 'f4', ('lat', 'lon'), fill_value=missing_value)
    nsheep.long_name = 'sheep'
    nsheep.units = units
    nsheep.missing_value = missing_value

    # close netCDF files
    # ==================
    nc_dset.sync()
    nc_dset.close()
    clone_dset.close()

    print('Created: ' + nc_fname + '\n')
    return
