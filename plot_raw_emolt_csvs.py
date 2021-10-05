#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified version of Mingchao's program by JiM in Oct 2021
Plots each vessel's raw data after combining them into single .

Input: folder with each vessels' raw csv data are stored
Output: time series plots of temp and depth for each vessel called "<vessel_name>_raw_ts.png""

Note: If running this on a local machine, you might want to first  run "get_matp_csv.py" to download the csv files

@author: Mingchao & JiM
"""
import matplotlib.pyplot as plt
import glob
import pandas as pd
import matplotlib.dates as dates

#Hardcodes
inputdir='./data/' # where inputdir has the csv files in subfolders by vessel_name
vessel_list=['Terri_Ann']


def plot(vessel,df,dpi=300):
        # where vessel_lists is just that 
        # where df has the combined dataframe for this vessel
        df['datetime']=pd.to_datetime(df['Datet(GMT)'])#change the time style to datetime
        df.set_index('datetime')
        MIN_T=min(df['Temperature(C)'])
        MAX_T=max(df['Temperature(C)'])
        MIN_D=min(df['Depth(m)'])
        MAX_D=max(df['Depth(m)'])
        diff_temp=MAX_T-MIN_T
        diff_depth=MAX_D-MIN_D
        if diff_temp==0:
            textend_lim=0.1
        else:
            textend_lim=diff_temp/8.0
        if diff_depth==0:
            dextend_lim=0.1
        else:
            dextend_lim=diff_depth/8.0
        fig=plt.figure(figsize=[11.69,8.27])
        size=min(fig.get_size_inches())        
        fig.suptitle('F/V '+vessel,fontsize=3*size, fontweight='bold')
        ax1=fig.add_subplot(211)
        ax2=fig.add_subplot(212)
        ax1.set_title(df['Datet(GMT)'].values[0][0:10]+' to '+df['Datet(GMT)'].values[len(df)-1][0:10])
        ax1.plot(df['datetime'][0::60],df['Temperature(C)'][0::60],color='b')
        ax1.legend(prop={'size': 1.5*size})
        ax1.set_ylabel('Celsius',fontsize=2*size)
        ax1.set_ylim(MIN_T-textend_lim,MAX_T+textend_lim)
        ax1.axes.get_xaxis().set_visible(False)
        ax2.plot(df['datetime'][0::60],df['Depth(m)'][0::60],color='R')
        ax2.legend(prop={'size':1.5* size})
        ax2.set_ylabel('Depth(m)',fontsize=2*size)
        ax2.set_ylim(MAX_D+dextend_lim,MIN_D-dextend_lim)
        ax2.xaxis.set_major_locator(plt.MaxNLocator(10))
        #ax2.xaxis.set_major_locator(plt.AutoLocator())
        plt.gca().xaxis.set_major_formatter(dates.DateFormatter('%Y-%m-%d'))
        plt.gcf().autofmt_xdate()
        plt.savefig(vessel+'_raw_ts.png',dpi=dpi,orientation='landscape')
        plt.show()
        
############# MAIN #########################
#Loop through all vessels
for i in range(len(vessel_list)):
    # Loop through all the files for this vessel and combine files
    k=0
    files=glob.glob(inputdir+vessel_list[i]+'/*')
    for file in files:
        k=k+1
        if k==1:
            df=pd.read_csv(file,skiprows=9)
            df=df.loc[(df['Depth(m)']>0.85*max(df['Depth(m)']))]  #get "bottom" data
            df=df[10:] # skip first 10 minutes while probe equilibrates to bottom environment
        else:
            df1=pd.read_csv(file,skiprows=9)
            df1=df1.loc[(df1['Depth(m)']>0.85*max(df1['Depth(m)']))]  #get "bottom" data
            df1=df1[10:] # skip first 10 minutes while probe equilibrates to bottom environment
            df=pd.concat([df,df1],axis=0)   
    plot(vessel_list[i],df,dpi=300)  
        

                    
