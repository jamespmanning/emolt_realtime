#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 16 09:20:25 2019

@author: leizhao
"""
import pandas as pd
import time 
from datetime import datetime


def screen_emolt(start_time,end_time,path):
    '''function:give a start time and end time, screen out the data between start time and end time 
    input:
        start_time: start time, the format is datetime.datetime
        end_time: end time, the format is datetime.datetime
        path: the address of emolt data'''
    tele_df=read_telemetry(path)  # get the dataframe of storing emolt data
    valuable_tele_df=pd.DataFrame(data=None,columns=['vessel_n','esn','time','lon','lat','depth','temp'])#use to save the emolt data during start time and end time
    for i in tele_df.index:  #loop every line in dataframe
        tele_time_str=str(tele_df['year'].iloc[i])+'-'+str(tele_df['month'].iloc[i])+'-'+str(tele_df['day'].iloc[i])+' '+str(tele_df['Hours'].iloc[i])+':'+str(tele_df['minates'].iloc[i])+':'+'00'# create the string of time
        tele_time=datetime.strptime(tele_time_str,'%Y-%m-%d %H:%M:%S')  # covert the time string to the datetime.datetime
        if start_time<=tele_time<end_time:  #judge the time whether during the start time and the end time
            valuable_tele_df=valuable_tele_df.append(pd.DataFrame(data=[[tele_df['vessel_n'][i],tele_df['esn'][i],tele_time,tele_df['lon'][i],tele_df['lat'][i],\
                                                                         tele_df['depth'][i],tele_df['rangedepth'][i],tele_df['timerange'][i],tele_df['temp'][i],tele_df['stdtemp'][i]]],\
                                                                        columns=['vessel_n','esn','time','lon','lat','depth','rangedepth','timerange','temp','stdtemp']))  # storing worthy data
    valuable_tele_df.index=range(len(valuable_tele_df))  #reindex
    return valuable_tele_df
def read_telemetrystatus(path_name):
    """read the telementry_status, then return the useful data
    input:
        path_name: thestring that include telemetry status file path and name."""
    data=pd.read_csv(path_name)   #read file
    #find the data lines number in the file('telemetry_status.csv')
    for i in range(len(data['vessel (use underscores)'])):
        if data['vessel (use underscores)'].isnull()[i]:
            data_line_number=i
            break
    #read the data about "telemetry_status.csv"
    telemetrystatus_df=pd.read_csv(path_name,nrows=data_line_number)  #read the data that we need lines
    #rename the column name that write vessel name
    as_list=telemetrystatus_df.columns.tolist()  
    idex=as_list.index('vessel (use underscores)')
    as_list[idex]='Boat'
    telemetrystatus_df.columns=as_list
    #fix the format of the columns 'Lowell-SN','logger_change','Boat'
    for i in range(len(telemetrystatus_df)):
        telemetrystatus_df['Boat'][i]=telemetrystatus_df['Boat'][i].replace("'","")
        if not telemetrystatus_df['Lowell-SN'].isnull()[i]:
            telemetrystatus_df['Lowell-SN'][i]=telemetrystatus_df['Lowell-SN'][i].replace('，',',')
        if not telemetrystatus_df['logger_change'].isnull()[i]:
            telemetrystatus_df['logger_change'][i]=telemetrystatus_df['logger_change'][i].replace('，',',')
    return telemetrystatus_df

def read_telemetry(path):
    """read the emolt data and fix a standard format, the return the standard format data
    input: 
        path: the path of the emolt data"""
    while True:
        tele_df=pd.read_csv(path,sep='\s+',names=['vessel_n','esn','month','day','Hours','minates','fracyrday',\
                                          'lon','lat','dum1','dum2','depth','rangedepth','timerange','temp','stdtemp','year'])
        if int(tele_df['year'].iloc[-9])==int(datetime.now().year):   #If the year of the ninth line (starting from the end line) is not this year, the current data is being updated, it needs to wait 10 minutes and then reload.
            break
        print('read_telemetry redownload data')
        time.sleep(600)  #wait 10 minutes
    return tele_df