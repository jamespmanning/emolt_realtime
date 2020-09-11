# -*- coding: utf-8 -*-
"""
Created on Mon May 16 13:02:24 2016

@author: hxu
"""

import matplotlib.pyplot as plt
import matplotlib.dates as dates
import os
import pandas as pd
import numpy as np
from matplotlib.ticker import ScalarFormatter
from pandas import Timedelta


def list_all_files(rootdir):
    """get all files' path and name in rootdirectory"""
    _files = []
    list = os.listdir(rootdir) #列出文件夹下所有的目录与文件
    for i in range(0,len(list)):
           path = os.path.join(rootdir,list[i])
           if os.path.isdir(path):
              _files.extend(list_all_files(path))
           if os.path.isfile(path):
              _files.append(path)
    return _files

def plot_aq(fn,path,allfileimg,percent):
    '''draw picture for every raw csv file:
        time with temperature and time with depth.'''
    fpath,fname=os.path.split(fn)
    pngname=fname.replace('csv','png')
    fnout=os.path.join(path,pngname)
    if not os.path.exists(path):
        os.makedirs(path)
    if fnout in allfileimg:
        return fnout
    try:
        dft=pd.read_csv(fn,sep=',',nrows=5)
    except:
        print ('no data1 in '+fn)
        pic_name=''
        return pic_name
    dft.index=dft['Probe Type']
#    df_id_name=dft['Lowell']['Vessel Number']
#    tit='Vessel'+df_id_name 
    print ('this is fn : '+fn)
    ######################################
    def parse(datet):
        from datetime import datetime
        dt=datetime.strptime(datet,'%Y-%m-%d %H:%M:%S')
        return dt
    try: 
        df=pd.read_csv(fn,sep=',',skiprows=9,parse_dates={'datet(GMT)':[1]},index_col='datet(GMT)',date_parser=parse)#creat a new Datetimeindex
    except:
#        print ('no data2 in '+fn)
        pic_name=''
        return pic_name
    
#    df.index=df.index-pd.tseries.timedeltas.to_timedelta(4, unit='h')  #, chage it to UTC time
    df['yd']=df.index.dayofyear+df.index.hour/24.+df.index.minute/60./24.+df.index.second/60/60./24.-1.0 #creates a yrday0 field
    
    df=df.loc[(df['Depth(m)']>10.0)]
    df=df.loc[(df['Depth(m)']>percent*np.mean(df['Depth(m)']))]  # get rid of shallow data
    df=df.loc[(df['Depth(m)']>df.mean()['Depth(m)']-3*np.std(df['Depth(m)'])) & (df['Depth(m)']<np.mean(df['Depth(m)'])+3*np.std(df['Depth(m)']))] # reduces time series to deep obs
    if len(df)<10:
        return ''
    for o in list(reversed(range(len(df)))): # usually ,aquetec is collecting data every 1 minute, if the period between two collect above 30 minutes,we get rid of the previous one 
        if (df.index[o]-df.index[o-1])>=pd.Timedelta('0 days 00:30:00') or o==0: 
            df=df.iloc[o:]
            break
    if len(df)<10:
        return ''
    #start draw picture 
    fig=plt.figure(figsize=[9,6])
    ax1=fig.add_subplot(211)
    ax1.plot(df.index,df['Temperature(C)'],'red')
    ax1.set_ylabel('Temperature (Celius)')
    try:    
        if max(df.index)-min(df.index)>pd.Timedelta('0 days 04:00:00'):
            interval1=(max(df.index)-min(df.index)).days*24+int((max(df.index)-min(df.index)).seconds/3600)
            ax1.xaxis.set_major_locator(dates.HourLocator(interval=interval1))# for hourly plot
        else: 
            ax1.xaxis.set_major_locator(dates.MinuteLocator(interval=int((max(df.index)-min(df.index)).seconds/60)))# for minutely plot
    except:
        print (fn+'  data is too few')
        pic_name='few data'
        return pic_name
    ax1.xaxis.set_major_formatter(dates.DateFormatter('%D %H:%M'))
    ax1.set_xlabel('')
    try:
        ax1.set_xticklabels([])
    except:
        print (fn+'  data is too few2')
        pic_name='few data'
        return pic_name
    ax1.grid()
    ax12=ax1.twinx()
#    ax12.set_title(tit)
    ax12.set_ylabel('Fahrenheit')
    ax12.set_xlabel('')
    ax12.set_xticklabels([])
    ax12.set_ylim(np.nanmin(df['Temperature(C)'].values)*1.8+32,np.nanmax(df['Temperature(C)'].values)*1.8+32)
    maxtemp=str(int(round(max(df['Temperature(C)'].values),2)*100))
    if len(maxtemp)<4:
        maxtemp='0'+maxtemp
    mintemp=str(int(round(min(df['Temperature(C)'].values),2)*100))
    if len(mintemp)<4:
        mintemp='0'+mintemp
    meantemp=str(int(round(np.mean(df['Temperature(C)'].values),2)*100))
    if len(meantemp)<4:
        meantemp='0'+meantemp
    sdeviatemp=str(int(round(np.std(df['Temperature(C)'].values),2)*100))
    for k in range(4):
      if len(sdeviatemp)<4:
        sdeviatemp='0'+sdeviatemp
    
    time_len=str(int(round((df['yd'][-1]-df['yd'][0]),3)*1000))
    for k in range(3):
        if len(time_len)<3:
            time_len='0'+time_len
    meandepth=str(abs(int(round(np.mean(df['Depth(m)'].values),0))))
    rangedepth=str(abs(int(round(max(df['Depth(m)'].values-min(df['Depth(m)'].values)),0))))
    for k in range(3):
        if len(rangedepth)<3:
            rangedepth='0'+rangedepth
    for k in range(3):
        if len(meandepth)<3:
            meandepth='0'+meandepth
    ax1.text(0.95, 0.9, 'mean temperature='+str(round(np.mean(df['Temperature(C)'].values*1.8+32),1))+'F',
            verticalalignment='top', horizontalalignment='right',
            transform=ax1.transAxes,
            color='green', fontsize=15)   #set the label of mean temperature 
    ax2=fig.add_subplot(212)
    ax2.plot(df.index,df['Depth(m)'].values)
    ax2.invert_yaxis()
    ax2.set_ylabel('Depth (Meters)')
    ax2.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
    ax2.grid()
#    ax2.set_ylim(max(df['Depth(m)'].values),min(df['Depth(m)'].values))
    ax2.set_ylim((0.2+max(df['Depth(m)'].values)),(min(df['Depth(m)'].values)-0.2))
    ax2.text(0.95, 0.9, 'mean depth='+str(round(np.mean(df['Depth(m)'].values),0))+'m',
            verticalalignment='top', horizontalalignment='right',
            transform=ax2.transAxes,
            color='green', fontsize=15) #set the label of mean depth
    ax22=ax2.twinx()
    ax22.set_ylabel('Fathoms')
#    ax22.set_ylim(min(df['Depth(m)'].values)/1.8288,max(df['Depth(m)'].values)/1.8288)
    ax22.set_ylim((min(df['Depth(m)'].values)-0.2)/1.8288,(0.2+max(df['Depth(m)'].values))/1.8288)
    ax22.invert_yaxis()
    if max(df.index)-min(df.index)>Timedelta('0 days 04:00:00'):
        interval1=(max(df.index)-min(df.index)).days*24+int((max(df.index)-min(df.index)).seconds/3600)
        ax1.xaxis.set_major_locator(dates.HourLocator(interval=interval1))# for hourly plot
    else: 
        ax1.xaxis.set_major_locator(dates.MinuteLocator(interval=int((max(df.index)-min(df.index)).seconds/60)))# for minutely plot
    ax2.xaxis.set_major_formatter(dates.DateFormatter('%D %H:%M'))
    plt.gcf().autofmt_xdate()    
    ax2.set_xlabel('Local TIME')
    
    plt.savefig(fnout)
    plt.savefig(fnout.replace('.png','.ps'),orientation='landscape')
    plt.close()
    pic_name= fnout+'.png'
    return pic_name

