'''
Get gps from bu353S4
Author: Huanxin Xu, 
version 0.0.1
For further questions ,please contact 508-564-8899, or send email to xhx509@gmail.com
'''
def func_readgps():
    import time
    import serial
    import numpy as np
    #'%Y-%m-%dT%H:%M:%S'
    def readgps(lat,lon,ser2):
            a=0
            while a<90:
                a=a+1
                line=ser2.readline()
                if "GPRMC" in line:
                    #print line
                    #lat =line[20:32]
                    #lon= line[32:44]
                    lat=line.split(',')[3]+line.split(',')[4]+','
                    lon=line.split(',')[5]+line.split(',')[6]
                    times='20'+line.split(',')[9][4:6]+'-'+line.split(',')[9][2:4]+'-'+line.split(',')[9][0:2]+'T'+line[7:9]+':'+line[9:11]+':'+line[11:13]
                    #times=line[57:63]+''+line[7:13]
                    return (lat,lon,times)
                if a==90:
                    return (lat,lon)
    def gps_name_generate(ports,lat,lon):
        import socket
        ser2=serial.Serial('/dev/'+ports,4800,timeout=1)
        lat,lon,times=readgps(lat,lon,ser2)
        #print lat,lon,times

        return lat,lon,times
    lat=''
    lon=''
    times=''
    ports='tty-huanxingps'

    df=open('/home/pi/Desktop/control_file.txt','r')
    for line in df:
            if line[:2]=='00':
               logger_name=line[9:11]+line[12:14]+line[15:17]     
    df.close()
    while True:
        
        lat,lon,times=gps_name_generate(ports,lat,lon)
        if len(lat)>4:
                f=open('/home/pi/Desktop/gps_location/'+logger_name+times[:4]+'_'+times[5:7]+'.txt','a+')
                f.writelines(times+','+lat+lon+'\n')
                time.sleep(1) 
                f.close()
                return
        time.sleep(29)#cause there is 1 seconds delay , 29 means 30 seconds


