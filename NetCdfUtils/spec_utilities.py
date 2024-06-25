# utilities to support spec.py
#
__prog__ = 'spec_utilities.py'
__version__ = '0.0.0'
__author__ = 's03mm5'

from os.path import split, join, isfile
from locale import format_string, setlocale, LC_ALL
import json
import time
from sys import stdout
import csv
from nc_low_level_fns import daily_to_monthly

setlocale(LC_ALL, '')

SUMMARY_VARNAMES = {'soc':'total_soc', 'ch4':'ch4_c', 'co2':'co2_c', 'no3':'no3_n', 'npp':'npp_adj', 'n2o':'n2o_n'}
SUMMARY_VARNAMES = {'soc':'total_soc', 'co2':'co2_c', 'no3':'no3_n', 'n2o':'n2o_n'}
NLINES_EXPECTATION = 14965
ERROR_STR = '*** Error *** '
WARNING_STR = '*** Warning *** '

class EcosseDialect(csv.excel):
    """Dialect class for reading in ECOSSE output files with the csv module."""
    delimiter = ' '
    skipinitialspace = True

class SpecError(Exception):
    pass

def make_id_seg(lat, lon, scenario, mu = -999, province = 'province', landuse = 'ara', ndom_soils = 1, area = '-999'):

    id_mod = list([province, str(lat), str(lon), mu, scenario, str(ndom_soils), landuse, area])
    return id_mod

def make_id_mod(id_, latitude, area_grid_cell, gran_lon):

    id_mod = list([id_[0], str(round(latitude,6))])
    longitude = (gran_lon/120) - 180.0
    id_mod.append(str(round(longitude,6)))
    id_mod = id_mod + id_[3:]
    id_mod.append(area_grid_cell)

    return id_mod

def deconstruct_sim_dir(sim_dir, scenario, land_use):

    directory = split(sim_dir)[1]
    parts = directory.split('_')
    lat_id = parts[0].strip('lat')
    lon_id = parts[1].strip('lon')
    # Get rid of leading zeros before the minus sign:
    lat_id = str(int(lat_id))
    lon_id = str(int(lon_id))
    #
    mu_global = parts[2].strip('mu')
    mu_global = mu_global.lstrip('0')

    soil_id = parts[3].lstrip('s')
    soil_id = soil_id.lstrip('0')
    lut = land_use   # from study definition file

    return [lat_id, lon_id, mu_global, scenario, soil_id, lut]

def retrieve_soil_results_ss(sim_dir):
    '''
    TODO: rewrite
    '''

    # split directory name to retrieve the mu global
    # =============================================
    mu = int(sim_dir.split('_mu')[1].split('_s')[0])

    input_txt = join(sim_dir, sim_dir, str(mu) + '.txt')
    if not isfile(input_txt):
        return -1

    result_for_soil = {'s_C_content': [], 's_bulk_dens': [],  's_pH': [], 's_clay': [], 's_silt': [],'s_sand': []}
    metric_lookup = {'C_content':'s_C_content', 'Bulk_dens':'s_bulk_dens', '%_clay':'s_clay', 'pH':'s_pH',
                                                                    '%_sand':'s_sand', '%_silt':'s_silt'}

    with open(input_txt, 'r') as fobj:
        mu_detail = json.load(fobj)

    for key in mu_detail:
        if key.find('soil_lyr') == 0:
            for metric in mu_detail[key]:
                map_metric = metric_lookup[metric]
                val = mu_detail[key][metric]
                result_for_soil[map_metric].append(val)

    return result_for_soil

def retrieve_soil_results(sim_dir, failed):

    func_name =  __prog__ + ' retrieve_soil_results'

    """
    for limited data mode only
    read soil parameters and plant input from the mu global file for example: 6093.txt
    """
    #
    soil_properties = list(['s_C_content','s_bulk_dens','s_pH','s_clay','s_silt','s_sand'])

    input_txt = join(sim_dir,'input.txt')
    if not isfile(input_txt):
        return -1

    with open(input_txt, 'r') as fobj:
        lines = fobj.readlines()

    nlayers = int(lines[1].split()[0])
    if nlayers < 1 or nlayers > 2:
        print('Check ' + sim_dir + ' - number of layers must be 1 or 2' )
        return -1

    nline = 2 + nlayers
    soil_parms = {}
    for property in soil_properties:
        soil_parms[property] = list([])

    for ilayer in range(nlayers):
        for property in soil_properties:
            line = lines[nline]
            soil_parms[property].append(float(line.split()[0]))
            nline += 1

    # look for plant input
    # ====================
    for nline, line in enumerate(lines):
        str_ngrow, descrip = line.split('#')
        if descrip.find('Number of growing seasons') >= 0:
            ngrow = int(str_ngrow)
            break

    # step through each land use and plant input (PI) pair until we find a non-zero PI
    # ================================================================================
    nline += 1
    for iyear, line in enumerate(lines[nline:nline + ngrow]):
        lu_yield, dummy = line.split('#')
        lu, pi = lu_yield.split(',')
        plant_input = float(pi)
        if plant_input > 0.0:
            break

    return soil_parms, iyear, plant_input

def read_summary_out(sim_dir, nmonths, daily_to_monthly_flag = True):
    """
    extract necessary results from the completed simulation's output file
    """
    fname = join(sim_dir, 'SUMMARY.OUT')
    if not isfile(fname):
        return None

    summary = {}
    with open(fname, 'r') as f:
        reader = csv.reader(f, dialect = EcosseDialect)
        next(reader)  # Skip the units description line
        columns = next(reader)
        for column in columns:
            summary[column] = []
        for row in reader:
            for i, val in enumerate(row):
                summary[columns[i]].append(float(val))

    # trap non-compliant OUT file
    # ===========================
    nlines = len(summary['year'])
    if nlines < NLINES_EXPECTATION:
        print(WARNING_STR + 'check lines in: ' + fname + '\tactual: {}\tshould be: {}'.format(nlines, NLINES_EXPECTATION))
        return None

    # build result
    # ============
    full_result = {}
    for sv_name, lv_name in SUMMARY_VARNAMES.items():
        if lv_name in summary:
            full_result[sv_name] = daily_to_monthly(summary[lv_name], sv_name, nmonths)   # sv_name = short variable name; lv_name = long

    return full_result

def load_manifest(lgr, sim_dir):
    '''
    '''

    # construct the name of the manifest file and read it
    # last 4 characters of simulations directory indicates soil, so ignore
    root_dir, locator_segment = split(sim_dir[0:-4])
    manifest_fname = join(root_dir,'manifest_' + locator_segment + '.txt')
    if isfile(manifest_fname):
        lgr.info('manifest file ' + manifest_fname + ' exists')
        try:
            with open(manifest_fname, 'r') as fmani:
                manifest = json.load(fmani)
        except (OSError, IOError) as e:
            print(e)
            manifest = None
    else:
        print('manifest file ' + manifest_fname + ' does not exist')
        manifest = None

    return manifest

def update_progress2(last_time, ndata, nzeros, nsize_grid):
    '''
    Update progress bar
    '''
    this_time = time.time()
    if (this_time - last_time) > 5.0:
        remain_str = format_string("%d", nsize_grid - ndata - nzeros, grouping=True)
        nzeros_str = format_string("%d", nzeros, grouping=True)
        ndata_str = format_string("%d", ndata, grouping=True)

        stdout.flush()
        stdout.write('\r                                                                                          ')
        stdout.write('\rWith data: {}  no data: {}  remaining: {}'.format(ndata_str, nzeros_str, remain_str))
        return this_time

    return last_time

def update_progress(last_time, nvalid, nmask, nunknwn, nsize_grid):
    '''
    Update progress bar
    '''
    this_time = time.time()
    if (this_time - last_time) > 5.0:
        ncomplete = nvalid + nmask + nunknwn
        remain_str = format_string("%d", nsize_grid - ncomplete, grouping=True)
        cmplt_str = format_string("%d", ncomplete, grouping=True)
        valid_str = format_string("%d", nvalid, grouping=True)
        mask_str = format_string("%d", nmask, grouping=True)
        unknwn_str = format_string("%d", nunknwn, grouping=True)

        stdout.flush()
        stdout.write('\r                                                                                          ')
        stdout.write('\rComplete: {}  Remaining: {}  Valid: {}  Masked: {}  Unknown: {}'
                                    .format(cmplt_str, remain_str, valid_str, mask_str, unknwn_str))
        return this_time

    return last_time

def update_progress_post(last_time, start_time, num_grid_cells, num_manifests, skipped, failed, warning_count):
    '''
    Update progress bar
    '''
    this_time = time.time()
    if (this_time - last_time) > 5.0:
        remain_str = format_string("%d", num_manifests - num_grid_cells, grouping=True)
        cmplt_str = format_string("%d", num_grid_cells, grouping=True)
        stdout.flush()
        stdout.write('\r                                                                                          ')
        stdout.write('\rComplete: {} Skip: {} Warnings: {} Remaining: {}'
                                                                .format(cmplt_str, skipped, warning_count, remain_str))
        return this_time

    return last_time

def _within_times(dt, starthour, startminute, endhour, endminute):
    """Deterines if the time is within the specified boundaries.
    dt    - [datetime object] the time to be checked
    """
    within = False
    if dt.hour > starthour and dt.hour < endhour:
        within = True
    elif dt.hour == starthour:
        if dt.minute >= startminute:
            within = True
    elif dt.hour == endhour and dt.minute <= endminute:
        within = True
    return within

def _seconds2hms(seconds):
    """
    Converts a time period in seconds to hours, minutes and seconds.
    """
    hours = int(seconds / 3600)
    seconds -= hours * 3600
    mins = int(seconds / 60)
    secs = seconds % 60
    return hours, mins, secs

def display_headers(form = None):
    """Writes a header to the screen and logfile."""
    print('')
    print('spec {}'.format(__version__))
    print('')
    print('   ####   ###      #   #  ###  #####      ### #      ###   #### #####   # #')
    print('   #   # #   #     ##  # #   #   #       #    #     #   # #     #       # #')
    print('   #   # #   #     # # # #   #   #      #     #     #   #  ###  #####   # #')
    print('   #   # #   #     #  ## #   #   #       #    #     #   #     # #')
    print('   ####   ###      #   #  ###    #        ### #####  ###  ####  #####   # #')
    print('')
    if form is not None:
        form.lgr.info('Starting simulations')