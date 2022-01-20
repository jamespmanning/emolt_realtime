import odlfile
import datetime


'''

This script can parse a lid file with temperature and pressure enabled ONLY.
TRI must equal ORI
Pressure bursts are supported but are NOT resolved in time. All samples in a pressure burst will have the same time.

'''
def parse_li(file_path):

    # Put the path to your file here
    #file_path = 'C:/Users/Nick Lowell/Google Drive/Lowell Instruments/Wireless MAT/NMFS Documents/Binary File Conversion/Version 4 for MATP Only/S4321_Temp&Press_(2).lis'


    fid = open(file_path, 'rb')
    out_temp = file_path[:-4] + '_T.txt'
    out_pres = file_path[:-4] + '_P.txt'

    this_file = odlfile.load_file(fid)  # returns the appropriate odl file object (lid or lis)
    converter = this_file.converter  # a "converter" is a host storage object complete with raw to si methods
    start_time = this_file.page_start_times[0]
    interval = this_file.major_interval_seconds

    with open(out_temp, 'w') as out_fid:
        out_fid.write('Datetime,Temperature (C)\n')
        for i in range(this_file.n_temperature_intervals):
            sample_raw = this_file.read_temperature(i)
            time = start_time + i * datetime.timedelta(seconds=interval)
            out_fid.write('{},{:0.2f}\n'.format(time.strftime('%Y-%m-%dT%H:%M:%S.000'), converter.temp_to_si(sample_raw)))
        out_fid.close()
    with open(out_pres, 'w') as out_fid:
        out_fid.write('Datetime,Pressure (psia)\n')
        for i in range(this_file.n_temperature_intervals):
            time = start_time + i * datetime.timedelta(seconds=interval)
            for pres in this_file.read_pressure(i):
                out_fid.write('{},{:0.2f}\n'.format(time.strftime('%Y-%m-%dT%H:%M:%S.000'), converter.pressure_to_psi(pres)))
        out_fid.close()
    return
