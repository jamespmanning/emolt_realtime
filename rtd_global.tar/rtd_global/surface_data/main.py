###########################################################################################
###### MAIN SCRIPT
###########################################################################################

import time
import os
import serial
import pandas as pd
from merge import *
from ftp_reader import *
from gps_reader import *
import serial.tools.list_ports as stlp
import sys
from priority import Priority
from sftp_aws import Transfer
from datetime import datetime
import logging
import setup_rtd
import paramiko
from weather_station_reader import *
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(filename=setup_rtd.parameters['path'] + 'logs/main.log',
                    format='%(levelname)s %(asctime)s :: %(message)s',
                    level=logging.DEBUG)
logging.debug('Start recording..')

class Profile(object):
    def __init__(self, sensor_type):
        self.vessel_name = setup_rtd.parameters['vessel_name'] #depending on the vessel
        self.server_name = ''
        self.server_id = 4
        self.l_sensors = sensor_type
        self.tow_num = len(os.listdir(setup_rtd.parameters['path'] + 'merged'))
        self.path = setup_rtd.parameters['path']
        self.gear = setup_rtd.parameters['gear_type']

    def main(self):
        device = self.list_ports('USB-Serial Controller D')
        device_ws = self.list_ports('AIRMAR USB<=>RS485 SerialConverter')
        #gps = GPS(device, self.path)
        ws = WS(device_ws)

        for sensor in self.l_sensors:
            # NKE necessary variable
            if sensor == 'NKE':
                ftp_conn = sensor(self.path)

            # Moana necessary variables
            elif sensor == 'Moana':
                l_moana = os.listdir(self.path + 'logs/raw/Moana')
                l_moana = [(int(e.split('.')[0].split('_')[-1]), e) for e in l_moana if setup_rtd.parameters['Moana_SN'] in e]
                c_moana = len(l_moana)

            # Lowell necessary variable
            elif sensor == 'Lowell':
                l_lowell = os.listdir(self.path + 'logs/raw/Lowell')

        old_time = datetime.now()

        while True:
            curr_time = datetime.now()
            #gps.add_df()
            ws.add_df()
            if (curr_time - old_time).total_seconds()/60 > 4:
                logging.debug('Adding data to gps file')
                print('Adding data to gps file')
                #gps.store_all_csv()
                ws.store_csv('/home/pi/rtd_global/WS/')
                ws.store_all_csv('/home/pi/rtd_global/WS/')
                old_time = curr_time
                #stats = os.stat(self.path + 'gps/gps_merged.csv')
                #if stats.st_size > 1728000:
                #    gps.zip_file()

            for sensor in self.l_sensors:
                if sensor == 'NKE':
                    try:
                        if ftp_conn.file_received():
                            logging.debug('New file downloading: ')
                            l_rec_file = ftp_conn.transfer()
                            logging.debug('Downloading completed ' + l_rec_file[0])

                            logging.debug('Adding data to gps file')
                            print('Adding data to gps file')
                            gps.store_all_csv()

                            self.connect_wireless(l_rec_file)

                            ldata = Merge().merge(l_rec_file, sensor, self.gear) #set sensor type as WiFi or Bluetooth

                            self.cloud(ldata, sensor)

                            print('waiting...')
                            time.sleep(5)

                            ftp_conn = sensor(self.path)
                    except ftplib.all_errors:
                        ftp_conn.reconnect()

                elif sensor == 'Moana':
                    with open(self.path + 'status.txt') as f_ble:
                        l_moana = os.listdir(self.path + 'logs/raw/Moana')
                        l_moana = [(int(e.split('.')[0].split('_')[-1]), e) for e in l_moana if setup_rtd.parameters['Moana_SN'] in e]
                        if len(l_moana) != c_moana:
                            time.sleep(10)
                            if '1' in f_ble.readline():
                                l_moana.sort()
                                l_moana = [e[1] for e in l_moana if setup_rtd.parameters['Moana_SN'] in e[1]]
                                l_rec_file = l_moana[c_moana:]
                                c_moana = len(l_moana)
                                logging.debug('Adding data to gps file')
                                print('Adding data to gps file')
                                gps.store_all_csv()

                                self.connect_wireless(l_rec_file, sensor)

                                ldata = Merge().merge(l_rec_file, sensor, self.gear)  # set sensor type as WiFi or Bluetooth

                                #l_moana = os.listdir(self.path + 'sensor/Moana')
                                #ls = [(int(e.split('.')[0].split('_')[-1]), e) for e in l_moana if setup_rtd.parameters['Moana_SN'] in e]
                                #c_moana = len(ls)
                                self.cloud(ldata, sensor)
                                print('waiting for the next profile...')

                elif sensor == 'Lowell':  #there are more than one type of sensor onboard
                    ln_lowell = os.listdir(self.path + 'logs/raw/Lowell')
                    if len(ln_lowell) > len(l_lowell):
                        print('Data from Lowell logger')
                        n_lowell = [e for e in ln_lowell if e not in l_lowell]  # stores only new Lowell data
                        gps.store_all_csv()  # necessary to store any gps data between the 10 minutes gps gap
                        self.connect_wireless(n_lowell, 'Lowell')  # sends raw data to BDC endpoint
                        ldata = Merge().merge(n_lowell, sensor, self.gear)  # merges sensor data and GPS
                        ldata = [(e[0], self.add_eMOLT_header(e[0], e[1])) for e in ldata]  # adding header to lowell files

                        l_lowell = os.listdir(self.path + 'logs/raw/Lowell')

                        self.eMOLT_cloud(ldata)  # sends merged data to eMOLT endpoint
                        self.cloud(ldata, sensor)  # sends merged data to BDC endpoint

    def cloud(self, ldata, sensor):
        for filename, df in ldata:
            if len(df) < 10: continue
            conn_type = Priority(server_name=self.server_name, server_id=self.server_id).conn_type()
            if conn_type == 1 or conn_type == 2:  # wifi
                print('wifi or gsm aws')
                Transfer('/home/ec2-user/rtd/vessels/{vess}/merged/{sensor}/'.format(
                    vess=setup_rtd.parameters['vessel_name'], sensor=sensor)).upload(
                    'merged/{sensor}/'.format(sensor=sensor) + filename, filename)
            else:
                logging.debug('There is no network available')
                df.to_csv(self.path + 'queued/{sensor}'.format(sensor=sensor) + filename, index=False)
            self.tow_num += 1

    def connect_wireless(self, l_rec_file, sensor):
        conn_type = Priority(server_name=self.server_name, server_id=self.server_id).conn_type()
        if conn_type < 3:
            if conn_type == 1:
                print('On-board WiFi network available')
            elif conn_type == 2:
                print('Mobile network available')

            data_gps = pd.read_csv(self.path + 'gps/gps_merged.csv')
            gps_name = 'gps' + datetime.utcnow().strftime('%y%m%d') + '.csv'
            data_gps.to_csv(self.path + 'logs/gps/' + gps_name, index=False)
            try:
                Transfer('/home/ec2-user/rtd/vessels/' + self.vessel_name + '/').upload('logs/gps/' + gps_name, 'gps/' + gps_name)
            except paramiko.ssh_exception.SSHException:
                logging.debug('GPS data was not uploaded')

            for file in l_rec_file:
                print('/home/ec2-user/rtd/vessels/' + self.vessel_name + '/', 'logs/raw/{sensor}/'.format(sensor=sensor) + file)
                Transfer('/home/ec2-user/rtd/vessels/' + self.vessel_name + '/').upload(
                    'logs/raw/{sensor}/'.format(sensor=sensor) + file, 'sensor/{sensor}/'.format(sensor=sensor) + file)

    def eMOLT_cloud(self, ldata):
        for filename, df in ldata:
            print(os.listdir(self.path + 'merged/Lowell/'))
            u = self.path + 'merged/Lowell/{file}'.format(file=filename)
            # print u
            session = ftplib.FTP('66.114.154.52', 'huanxin', '123321')
            file = open(u, 'rb')
            session.cwd("/BDC")
            # session.retrlines('LIST')               # file to send
            session.storbinary("STOR " + filename, fp=file)  # send the file
            # session.close()
            session.quit()  # close file and FTP
            time.sleep(1)
            file.close()

    def add_eMOLT_header(self, filename, data):
        logger_timerange_lim = setup_rtd.metadata['time_range']
        logger_pressure_lim = setup_rtd.metadata['Fathom'] * 1.8288  # convert from fathom to meter
        transmit = setup_rtd.metadata['transmitter']
        MAC_FILTER = [setup_rtd.metadata['mac_addr']]
        MAC_FILTER[0] = MAC_FILTER[0].lower()
        boat_type = setup_rtd.metadata['gear_type']
        vessel_num = setup_rtd.metadata['vessel_num']
        vessel_name = setup_rtd.metadata['vessel_name']
        tilt = setup_rtd.metadata['tilt']
        header_file = open(self.path + 'header.csv', 'w')
        header_file.writelines('Probe Type,Lowell\nSerial Number,' + MAC_FILTER[0][
                                                                     -5:] + '\nVessel Number,' + vessel_num + '\nVessel Name,' + vessel_name + '\nDate Format,YYYY-MM-DD\nTime Format,HH24:MI:SS\nTemperature,C\nDepth,m\n')  # create header with logger number
        header_file.close()

        # AFTER GETTING THE TD DATA IN A DATAFRAME
        data.rename(columns={'DATETIME': 'datet(GMT)', 'TEMPERATURE': 'Temperature (C)', 'PRESSURE': 'Depth (m)', 'LATITUDE': 'lat', 'LONGITUDE': 'lon'},
                    inplace=True)

        data[:, 'HEADING'] = 'DATA'  # add header DATA line
        data.reset_index(level=0, inplace=True)
        data.index = data['HEADING']
        data = data[['datet(GMT)', 'lat', 'lon', 'Temperature (C)', 'Depth (m)']]
        data.to_csv(self.path + 'merged/Lowell/{file}'.format(file=filename[:-4]) + '_S1.csv')

        os.system('sudo cat ' + self.path + 'merged/Lowell/{file}_S1.csv >> ' + self.path + 'header.csv'.format(file=filename[:-4]))
        # os.system('rm ' + new_file_path + '_S1.csv')

    def list_ports(self, desc):
        list_usb = []
        if sys.platform.startswith('linux'):
            list_usb = serial.tools.list_ports.comports()
            
        for port in list_usb:
            try:
                if port.description == desc:
                    return port.device
            except (OSError, serial.SerialException):
                pass
        return
    
    def wifi_connection(self, server_id):
        os.system('wpa_cli -i wlan0 select_network {}'.format(
                server_id))


#when power on
while True:
    if True:#try:
        print("RPi started recording.\n")
        #set type of sensor 'WiFi' or 'Bluetooth' or both
        Profile(setup_rtd.parameters['sensor_type']).main()
    #except:
    #    print('Unexpected error:', sys.exc_info()[0])
    #    time.sleep(60)


