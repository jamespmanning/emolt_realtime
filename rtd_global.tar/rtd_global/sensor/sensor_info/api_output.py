import serial.tools.list_ports as stlp
import sys
import serial
import pandas as pd
from sftp_aws import Transfer

pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


class output:

    def __init__(self, metadata, segment):
        self.metadata = metadata
        self.segment = segment
        self.transfer = Transfer('/home/ec2-user/rtd/segments_Flid/')
        self.salinity = True if 'SALINITY' in self.segment else False

    def wifi(self):
        if self.salinity:
            self.segment.to_csv('./segments/wifi/' + self.metadata,
                                columns=['DATETIME', 'TEMPERATURE', 'PRESSURE', 'SALINITY', 'LATITUDE', 'LONGITUDE'], index=False, header=True, float_format='%.6f')
        else:
            self.segment.to_csv('./segments/wifi/' + self.metadata,
                                columns=['DATETIME', 'TEMPERATURE', 'PRESSURE', 'LATITUDE', 'LONGITUDE'], index=False, header=True, float_format='%.6f')
        self.transfer.upload('segments/wifi/' + self.metadata, 'wifi/' + self.metadata)

    def GSM(self):
        if self.salinity:
            self.segment.to_csv('./segments/wifi/' + self.metadata,
                                columns=['DATETIME', 'TEMPERATURE', 'PRESSURE', 'SALINITY', 'LATITUDE', 'LONGITUDE'], index=False, header=True, float_format='%.6f')
        else:
            self.segment.to_csv('./segments/wifi/' + self.metadata,
                                columns=['DATETIME', 'TEMPERATURE', 'PRESSURE', 'LATITUDE', 'LONGITUDE'], index=False, header=True, float_format='%.6f')
        self.transfer.upload('segments/wifi/' + self.metadata, 'wifi/' + self.metadata)


    def list_ports(self, desc):
        if sys.platform.startswith('linux'):
            list_usb = serial.tools.list_ports.comports()
        for port in list_usb:
            try:
                if port.description == desc:
                    return port.device
            except (OSError, serial.SerialException):
                pass
        return
