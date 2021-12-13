# Routine to grab Lowell Instrument data from AWS 
# Original version by Carles w/some additions by JiM in Fall 2021
#
# Nov 2021 - JiM added GPS file grabbing
#
# WARNING:  
# This gets hungup for some reason in Spyder.  I need to run it from a command line.

import boto3
import sys
import os
import pandas as pd
import csv
import io
from io import StringIO
from matplotlib import pyplot as plt

## HARDCODES ###
scale_dep=1.0 # scale factor where originally it looked like I needed to devide by scale_dep=10.0
min_depth=15.0/scale_dep # minimum depth (meters) acceptable for a cast
mac='00-1e-c0-6c-74-f1/' # Mary Elizabeth
vessel='Mary Elizabeth'
#mac='00-1e-c0-6c-75-1d/' # Beast of Burden
# eMOLT credentials
access_key = ''
access_pwd = ''

s3_bucket_name = 'bkt-cfa'  # bucket name
path = 'aws_files/'  # path to store the data

"""Accessing the S3 buckets using boto3 client"""
s3_client = boto3.client('s3')
s3 = boto3.resource('s3',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=access_pwd)

""" Getting data files from the AWS S3 bucket as denoted above """
my_bucket = s3.Bucket(s3_bucket_name)
bucket_list = []
#for file in my_bucket.objects.filter(Prefix='00-1e-c0-6c-74-f1/'):  # write the subdirectory name
for file in my_bucket.objects.filter(Prefix=mac):  # write the subdirectory name mac add
    file_name = file.key
    if (file_name.find(".csv") != -1) or (file_name.find(".gps") != -1): # JiM added gps
        bucket_list.append(file.key)
length_bucket_list = (len(bucket_list))

# l_downloaded = os.listdir(path + 'WR_54/data') + os.listdir(path + 'WR_57/data')
# bucket_list = [e for e in bucket_list if e not in l_downloaded]
#
# """ Reading the individual files from the AWS S3 buckets and putting them in dataframes """
#
ldf_pressure = []  # Initializing empty list of dataframes
ldf_temperature = []
ldf_gps =[]

for file in bucket_list:
    obj = s3.Object(s3_bucket_name, file)
    data = obj.get()['Body'].read()
    try:
        if 'Temperature' in os.path.basename(file):
            df = pd.read_csv(io.BytesIO(data), header=0, delimiter=",", low_memory=False)
            ldf_temperature.append(df)
        elif 'Pressure' in os.path.basename(file):
            df = pd.read_csv(io.BytesIO(data), header=0, delimiter=",", low_memory=False)
            ldf_pressure.append(df)
        elif 'gps' in os.path.basename(file):
            df = pd.read_csv(io.BytesIO(data), header=0, delimiter=",", low_memory=False) # need to read this differently
            ldf_gps.append(df)
    except:
        print('Not working', file)

#print(ldf_pressure, ldf_temperature,ldf_gps) # these are lists of dataframes
# merging the dataframes

filenames = [i for i in bucket_list  if 'gps' in i] # where bucket_list is 3 times as many elements as filenames
for j in range(len(ldf_gps)):
    if max(ldf_pressure[j]['Pressure (dbar)']/scale_dep)>min_depth: # only process those that were submergedmore than 2 meters
        lat=ldf_gps[j].columns[0].split(' ')[1]# picks up the "column name" of an empty dataframe read by read_csv
        lon=ldf_gps[j].columns[0].split(' ')[2]
        ldf_temperature[j]['ISO 8601 Time']=pd.to_datetime(ldf_temperature[j]['ISO 8601 Time'])
        df=ldf_temperature[j].set_index('ISO 8601 Time')
        df['depth (m)']=ldf_pressure[j]['Pressure (dbar)'].values/scale_dep
        df['lat']=lat
        df['lon']=lon
        df.to_csv('aws_files/'+filenames[j][18:-4]+'.csv')
        fig=plt.figure(figsize=(8,5))
        ax = fig.add_subplot(211)
        ax.plot(df.index,df['Temperature (C)'],color='r')
        ax.set_ylim(min(df['Temperature (C)'].values),max(df['Temperature (C)'].values))
        TF=df['Temperature (C)'].values*1.8+32 # temp in farenheit
        ax.set_ylabel('degC')
        ax2=ax.twinx()
        ax2.set_ylim(min(TF),max(TF))
        ax2.plot(df.index,TF,color='r')
        ax2.set_ylabel('fahrenheit')
        #ax.xaxis.set_major_formatter(dates.DateFormatter('%M'))
        plt.title(vessel+' at '+str(lat[:-3])+'N, '+str(lon[:-3])+'W')# where we ignore the last 3 digits of lat/lon
        ax3 = fig.add_subplot(212)
        ax3.plot(df.index,-1*df['depth (m)'])
        ax3.set_ylabel('meters')
        DF=-1*df['depth (m)']/1.8288
        ax4=ax3.twinx()
        ax4.set_ylim(min(DF),max(DF))
        ax4.plot(df.index,TF,color='b')
        ax4.set_ylabel('fathoms')
        fig.autofmt_xdate()
        plt.savefig('aws_plots/'+filenames[j][18:-4]+'.png')
        #plt.close('all')
    

