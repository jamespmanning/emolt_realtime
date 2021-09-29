# -*- coding: utf-8 -*-
"""
Created on Fri Apr 16 18:09:07 2021
Routine to process and plot calibration check using new "Fluke reference thermometer"
@author: James.manning
"""
import pandas as pd
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
from datetime import timedelta as td
from datetime import datetime as dt
import glob

dt1=dt(2021,4,27,17,30) #startime to compare
dt2=dt(2021,4,27,18,30)  # endtime

# Read in VEMCO Miniloag data
count=0
for file in glob.glob("Minilog*.csv"):
    #print(file)
    count=count+1
    if count==1:
        dfv=pd.read_csv(file,skiprows=8,header=None,names=['date', 'time', 'temp'])
        dfv['sn']=file[15:19]
        dfv['dtime']=pd.to_datetime(dfv['date']+' '+dfv['time'])+td(hours=4)# added 4 hours to get UTC
        dfv.set_index('dtime')
    else:
        #if (file[15:19]!='8787') & (file[15:19]!='8788'):
            dfv1=pd.read_csv(file,skiprows=8,header=None,names=['date', 'time', 'temp'])
            dfv1['sn']=file[15:19]
            dfv1['dtime']=pd.to_datetime(dfv1['date']+' '+dfv1['time'])+td(hours=4)
            dfv1.set_index('dtime')
            print(file[15:19]+' '+str(dfv1[(dfv1['dtime']>dt1) & (dfv1['dtime']<dt2)]['temp'].mean()))
            frames=[dfv,dfv1]
            dfv=pd.concat(frames,sort=False)

# Read in ONSET MX2204 data downloed from HoboLink
dfo=pd.read_csv('apr21_calprobe_mx2204_2.csv')
dfo=dfo.iloc[:,:-13]# removes unnecessary columns
dfo['dtime']=pd.to_datetime(dfo['Date'])#+td(hours=4)
dfo.set_index('dtime')

# Read in Lowell Data
dfl=pd.read_csv('li_750c_20210429_155000.csv',skiprows=8)
dfl['dtime']=pd.to_datetime(dfl['datet(GMT)'])
dfl.set_index('dtime')
dfl=dfl[dfl['dtime']>dt(2021,4,27,16,30,0)]
dfl=dfl[dfl['dtime']<dt(2021,4,27,21,0,0)]

# read in FLUKE readings
dff=pd.read_csv('apr21_calprobe_fluke_2.csv')
dff['date']='04/27/2021'
dff['dtime']=pd.to_datetime(dff['date'] + ' ' + dff['UTC'])+td(hours=4)+td(minutes=5)
dff.set_index('dtime')
dff.rename(columns={'Fluke':'Temp'},inplace=True)

# Calculate means at particular time ranges

mv=dfv[(dfv['dtime']>dt1) & (dfv['dtime']<dt2)]['temp'].mean()
#mo=dfo[(dfo['dtime']>dt1) & (dfo['dtime']<dt2)]['temp'].mean()
mf=dff[(dff['dtime']>dt1) & (dff['dtime']<dt2)]['Temp'].mean()
ml=dfl[(dfl['dtime']>dt1) & (dfl['dtime']<dt2)]['Temperature (C)'].mean()
print("VEMCO="+"{0:.2f}".format(mv)+"\nFluke="+"{0:.2f}".format(mf)+"\nLowell="+"{0:.2f}".format(ml))


fig, ax = plt.subplots(figsize=(12,10))
for k in list(set(dfv['sn'])):
    dfv1=dfv[dfv['sn']==k]
    ax.plot(dfv1['dtime'],dfv1['temp'],linewidth=3,label=k)# plot VEMCO
for j in dfo.columns[2:10]:
    ax.plot(dfo['dtime'],dfo[j],label=j[-3:])   #plot ONSET
    #print(j[-3:]+' '+str(dfo[j].mean()))
ax.plot(dfl['dtime'],dfl['Temperature (C)'],linewidth=3,label='Lowell')    
ax.plot(dff['dtime'],dff['Temp'],linestyle='--',linewidth=3,label='Fluke') #plot Fluke
for jj in range(len(dff)):
    if type(dff.modification.values[jj])==str:  
        #print(dff.modification.values[jj])
        ax.text(dff.dtime.values[jj],12.,dff.modification.values[jj],size=16,horizontalalignment='center',rotation=90)
plt.legend( title='SN', bbox_to_anchor=(1.1, 1), loc='upper right')
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
ax.set(ylabel='degC',xlabel='27 April 2021 (UTC)')
ax.set_title('Ice-Bath Calibration/Comparison of Fluke, Vemco (4-digit), Onset (3-digit), and Lowell Probes')
fig.savefig('calprobe_with_fluke_apr2021.png')

