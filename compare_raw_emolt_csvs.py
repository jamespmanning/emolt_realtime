#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routine to compare raw TDR data from different instruments .

Input: folder with each vessels' raw csv data are stored
Output: time series plots of temp and depth for each vessel called "<vessel_name>_raw_ts.png""


@author: JiM
Oct 2021
"""
import matplotlib.pyplot as plt
import glob
import pandas as pd
import matplotlib.dates as dates
import numpy as np

#Hardcodes
inputdir='' # where inputdir has the csv files in subfolders by vessel_name
vessel_list=['Illusion']


def plot(vessel,df,dfa,dpi=300):
        # where vessel_lists is just that 
        # where df has the combined dataframe for lowell and dfa has aquatec

        MIN_T=min(df['Temperature (C)'])
        MAX_T=max(df['Temperature (C)'])
        MIN_D=min(df['Depth (m)'])
        MAX_D=max(df['Depth (m)'])
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
        fig.suptitle('Probe comparison on F/V '+vessel,fontsize=3*size, fontweight='bold')
        ax1=fig.add_subplot(211)
        ax2=fig.add_subplot(212)
        ax1.set_title(df['datet(GMT)'].values[0][0:10]+' to '+df['datet(GMT)'].values[len(df)-1][0:10])
        ax1.plot(df['datetime'][0::60],df['Temperature (C)'][0::60],color='b',label='Lowell mean ='+'%0.2f' % np.mean(df['Temperature (C)'])+' degC')
        ax1.plot(dfa.index[0::60],dfa['degC'][0::60],color='r',label='Aquatec mean ='+'%0.2f' % np.mean(dfa['degC'])+' degC')
        ax1.legend(prop={'size': 1.5*size})
        ax1.set_ylabel('Celsius',fontsize=2*size)
        ax1.set_ylim(MIN_T-textend_lim,MAX_T+textend_lim)
        ax1.axes.get_xaxis().set_visible(False)
        ax2.plot(df['datetime'][0::60],df['Depth (m)'][0::60],color='b',label='Lowell mean ='+'%0.0f' % np.mean(df['Depth (m)'])+' meters')
        ax2.plot(dfa.index[0::60],dfa['m'][0::60],color='r',label='Aquatec mean ='+'%0.0f' % np.mean(dfa['m'])+' meters')
        ax2.legend(prop={'size':1.5* size})
        ax2.set_ylabel('Depth (m)',fontsize=2*size)
        ax2.set_ylim(MAX_D+dextend_lim,MIN_D-dextend_lim)
        ax2.xaxis.set_major_locator(plt.MaxNLocator(10))
        #ax2.xaxis.set_major_locator(plt.AutoLocator())
        plt.gca().xaxis.set_major_formatter(dates.DateFormatter('%Y-%m-%d'))
        plt.gcf().autofmt_xdate()
        plt.savefig(vessel+'_compare_raw.png',dpi=dpi,orientation='landscape')
        plt.show()
        
############# MAIN #########################
#Loop through all vessels
for i in range(len(vessel_list)):
    # Loop through all the files for this vessel and combine files
    k=0
    files_lowell=glob.glob('li*')
    files_aquatec=glob.glob('Lo*')
    for file in files_lowell:
        k=k+1
        if k==1:
            df=pd.read_csv(file,skiprows=8) # assumes this is Lowell
            df=df.loc[(df['Depth (m)']>0.85*max(df['Depth (m)']))]  #get "bottom" data
            df=df[10:] # skip first 10 minutes while probe equilibrates to bottom environment
        else:
            df1=pd.read_csv(file,skiprows=8)
            df1=df1.loc[(df1['Depth (m)']>0.85*max(df1['Depth (m)']))]  #get "bottom" data
            df1=df1[10:] # skip first 10 minutes while probe equilibrates to bottom environment
            df=pd.concat([df,df1],axis=0) 
    df['datetime']=pd.to_datetime(df['datet(GMT)'])#change the time style to datetime
    df.set_index('datetime')
    k=0
    for file in files_aquatec:
        print(file)
        k=k+1
        if k==1:
            dfa=pd.read_csv(file,skiprows=33,header=None)#,names=['UNITS','datehour','	Raw1','degC','Raw2','	 V','Raw3','bar','Raw4','m'])      
            dfa=dfa.loc[(dfa[9]>0.85*max(dfa[9]))]
            dfa['dtime']=pd.to_datetime(dfa[1])#+td(hours=4) # where I have manually editted header line to read this
            dfa=dfa.set_index('dtime')
        else:
            dfa1=pd.read_csv(file,skiprows=33,header=None)#,names=['UNITS','datehour','	Raw1','degC','Raw2','	 V','Raw3','bar','Raw4','m'])
            dfa1=dfa1.loc[(dfa1[9]>0.85*max(dfa1[9]))]  #get "bottom" data
            dfa1['dtime']=pd.to_datetime(dfa1[1])#+td(hours=4) # where I have manually editted header line to read this
            dfa1=dfa1.set_index('dtime')
            dfa=pd.concat([dfa,dfa1],axis=0)
    dfa.rename(columns={3:'degC',9:'m'}, inplace=True)
    plot(vessel_list[i],df,dfa,dpi=300)  
        

                    
