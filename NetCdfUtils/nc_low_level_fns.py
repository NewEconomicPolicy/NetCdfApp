#-------------------------------------------------------------------------------
# Name:        nc_low_level_fns.py
# Purpose:     Functions to create and write to netCDF files and return latitude and longitude indices
# Author:      Mike Martin
# Created:     25/01/2020
# Description: taken from netcdf_funcs.py in obsolete project PstPrcssNc
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'nc_low_level_fns.py'
__version__ = '0.0.0'
__author__ = 's03mm5'

from calendar import monthrange
from _datetime import datetime
from statistics import mean, StatisticsError
from numpy import arange

missing_value = -999.0
imiss_value = int(missing_value)

ROOT_WTHR = 'E:\\GlobalEcosseData\\'
HARMONIE = ROOT_WTHR + 'HARMONIE_V2\\Monthly\\'
ECLIPS_OUT = ROOT_WTHR + 'ECLIPS2_GlEc\\Monthly\\'

PREFIX = 'ECLIPS2_0_'
GCMS = ['CLMcom_CCLM', 'CLMcom_CLM', 'DMI_HIRAM','KMNI_RAMCO','MPI_CSC_REMO2009']
YEAR_RANGE = '_1961_2100'
SCENARIOS = {'RCP60':'_6.0', 'RCP45':'_4.5', 'RCP26':'_2.6', 'RCP85':'_8.5'}

def daily_to_monthly(val_list, metric, nmonths):
    '''
    take days extents from HARMONIE daily datasets 41 years 365 + 12 leap years
    '''
    indx1 = 0
    imnth = 1
    monthly_vals = []
    for indx_mnth in range(nmonths):
        frst_day, num_days = monthrange(2011, imnth)
        indx2 = indx1 + num_days
        if metric == 'soc':
            try:
                monthly_vals.append(mean(val_list[indx1:indx2]))
            except StatisticsError as err:
                print(err)
                return None
        else:
            monthly_vals.append(sum(val_list[indx1:indx2]))  # flux
        indx1 += num_days
        imnth += 1
        if imnth > 12:
            imnth = 1

    return monthly_vals

def generate_daily_atimes(fut_start_year):
    '''
    take days extents from HARMONIE daily datasets 41 years 365 + 12 leap years
    '''
    nday_strt = 25202; nday_end = 43098
    atimes = arange(nday_strt, nday_end + 1)     # create ndarray

    return atimes

def generate_mnthly_atimes(fut_start_year, num_months):
    '''
    expect 1092 for 91 years plus 2 extras for 40 and 90 year differences
    '''

    atimes = arange(num_months)     # create ndarray
    atimes_strt = arange(num_months)
    atimes_end  = arange(num_months)

    date_1900 = datetime(1900, 1, 1, 12, 0)
    imnth = 1
    year = fut_start_year
    prev_delta_days = -999
    for indx in arange(num_months + 1):
        date_this = datetime(year, imnth, 1, 12, 0)
        delta = date_this - date_1900   # days since 1900-01-01

        # add half number of days in this month to the day of the start of the month
        # ==========================================================================
        if indx > 0:
            atimes[indx-1] = prev_delta_days + int((delta.days - prev_delta_days)/2)
            atimes_strt[indx-1] = prev_delta_days
            atimes_end[indx-1] =  delta.days - 1

        prev_delta_days = delta.days
        imnth += 1
        if imnth > 12:
            imnth = 1
            year += 1

    return atimes, atimes_strt, atimes_end

def generate_yearly_atimes(fut_start_year, num_years):
    '''
    expect 1092 for 91 years plus 2 extras for 40 and 90 year differences
    '''

    atimes = arange(num_years)     # create ndarray
    atimes_strt = arange(num_years)
    atimes_end  = arange(num_years)

    date_1900 = datetime(1900, 1, 1, 12, 0)
    year = fut_start_year
    prev_delta_days = -999
    for indx in arange(num_years + 1):
        date_this = datetime(year, 1, 1, 12, 0)
        delta = date_this - date_1900   # days since 1900-01-01

        # add half number of days in this month to the day of the start of the month
        # ==========================================================================
        if indx > 0:
            atimes[indx-1] = prev_delta_days + int((delta.days - prev_delta_days)/2)
            atimes_strt[indx-1] = prev_delta_days
            atimes_end[indx-1] =  delta.days - 1

        prev_delta_days = delta.days
        year += 1

    return atimes, atimes_strt, atimes_end