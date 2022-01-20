import OdlFile
from collections import namedtuple


def get_info(file_path):
    """
    Return file information about file_path as a named tuple

    Information includes file header, calibration coefficients (host storage), start time, file size,
    and number of temperature and orient (accel/mag) intervals.
    """

    odl_info = namedtuple('odl_info', 'header coefficients start_time file_size n_orient_intervals '
                                      'n_temperature_intervals')
    with open(file_path, 'rb') as f:
        odl_file = OdlFile.load_file(f)
        odl_info.header = odl_file.header
        odl_info.coefficients = odl_file.host_storage
        odl_info.start_time = odl_file.page_start_times[0]
        odl_info.file_size = odl_file.file_size
        odl_info.n_orient_intervals = odl_file.n_orient_intervals
        odl_info.n_temperature_intervals = odl_file.n_temperature_intervals

    return odl_info


def convert_xyz(file_path, out_path=None, start_time=None, end_time=None, avg_interval=None, header='default'):
    """
    Read accelerometer/magnetometer data from file and convert to calibrated SI values.

    Accelerometer/magnetometer data will have this units (g), (mG) respectively.

    Keyword arguments:
    out_path -- the output file path. If out_path == None, the input file name will be used and appended with _MA.txt
    start_time -- datetime object specifying where to start parsing the file. Parsing will begin at
        the first interval with a time greater than or equal to start_time. Data will not interpolate to start time
        if it does not fall on an interval.
    end_time -- datetime object specifying where to end parsing. end_time is exclusive, meaning that if an interval
        has the same time, it will not be parsed.
    avg_interval -- the time in seconds to average over. avg_interval must be a multiple of ORI.
    header -- if 'legacy' is selected, date and time will each be a separate column

    INTERNAL NOTE: convert_xyz has been compared against MatLoggerCommand and output is identical.
    """

    time_format = TimeFormat(header)
    with open(file_path, 'rb') as f:
        reader = OdlFile.OrientReader(f, start_time, end_time, avg_interval)
        if not reader.header['ACL'] and not reader.header['MGN']:
            raise RuntimeError('No orientation channels enabled.')
        if not out_path:
            out_path = file_path[:-4] + '_MA.txt'

        header_str = time_format.time_str
        format_str = '{}'  # placeholder for time which is formatted below
        if reader.header['ACL']:
            header_str += ',Ax (g),Ay (g),Az (g)'
            format_str += ',{:0.3f},{:0.3f},{:0.3f}'
        if reader.header['MGN']:
            header_str += ',Mx (mG),My (mG), Mz(mG)'
            format_str += ',{:0.2f},{:0.2f},{:0.2f}'
        format_str += '\n'

        with open(out_path, 'w') as w:
            w.write(header_str + '\n')
            for time, accel, mag in reader:
                time_str = time.strftime(time_format.format)[:-3]
                w.write(format_str.format(time_str, *accel+mag))


def convert_temperature(file_path, out_path=None, start_time=None, end_time=None, avg_interval=None, header='default'):
    """
    Read temperature data from file_path and write to out_path as plain text.

    Keyword arguments:
    out_path -- the output file path. If out_path == None, the input file name will be used and appended with _T.txt
    start_time -- datetime object specifying where to start parsing the file. Parsing will begin at
        the first interval with a time greater than or equal to start_time. Data will not interpolate to start time
        if it does not fall on an interval.
    end_time -- datetime object specifying where to end parsing. end_time is exclusive, meaning that if an interval
        has the same time, it will not be parsed.
    avg_interval -- the time in seconds to average over. avg_interval must be a multiple of TRI.
    """

    time_format = TimeFormat(header)
    with open(file_path, 'rb') as f:
        reader = OdlFile.TemperatureReader(f, start_time, end_time, avg_interval)
        if not out_path:
            out_path = file_path[:-4] + '_T.txt'
        with open(out_path, 'w') as w:
            w.write('{},Temperature (C)\n'.format(time_format.time_str))
            for time, temperature in reader:
                time = time.strftime(time_format.format)[:-3]
                w.write('{},{:0.3f}\n'.format(time, temperature))


def convert_flow(in_file, flow_profile, out_path=None, start_time=None, end_time=None, avg_interval=None,
                 header='default'):
    """
    Convert .lid/.lis file to flow speed components.

    Arguments:
    flow_profile -- a calibration file relating tilt angle to flow speed.
    out_path -- the output file path. If out_path == None, the input file name will be used and appended with _T.txt
    start_time -- datetime object specifying where to start parsing the file. Parsing will begin at
        the first interval with a time greater than or equal to start_time. Data will not interpolate to start time
        if it does not fall on an interval.
    end_time -- datetime object specifying where to end parsing. end_time is exclusive, meaning that if an interval
        has the same time, it will not be parsed.
    avg_interval -- the time in seconds to average over. avg_interval must be a multiple of TRI.
    """

    flow = OdlFile.load_flow_profile(flow_profile)
    with open(in_file, 'rb') as f:
        if not out_path:
            out_path = in_file[:-4] + '_CR.txt'
        orient_reader = OdlFile.OrientReader(f, start_time, end_time, avg_interval)
        time_format = TimeFormat(header)
        with open(out_path, 'w') as w:
            w.write('{},Velocity-N (cm/s),Velocity-E (cm/s)\n'.format(time_format.time_str))
            # format_str =
            for time, accel, mag in orient_reader:
                flow_n, flow_e = OdlFile.flow(accel, mag, flow)
                time_str = time.strftime(time_format.format)[:-3]
                w.write('{},{:0.2f},{:0.2f}\n'.format(time_str, flow_n, flow_e))


class TimeFormat(object):
    """
    Internal function. Consider replacing with named tuple.
    """
    def __init__(self, header_str):
        if header_str.lower() == 'default':
            self.time_str = 'Time'
            self.format = '%Y-%m-%dT%H:%M:%S.%f'
        elif header_str.lower() == 'legacy':
            self.time_str = 'Date,Time'
            self.format = '%Y-%m-%d,%H:%M:%S.%f'
        else:
            raise Exception('Unknown header type, {}'.format(header_str))