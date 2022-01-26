#!/usr/bin/env python
# coding: utf-8
# JiM modification of Carles code to plot raw data profiles in post processing mode
# i.e. not in realtime mode
# step 1:  read raw file and "standardize" it using Carles "Standardize" function
# step 2: call Plotting.plot_profile in the same way that Carles "merge" program does

############  HARDCODES #####
file='rawfiles/MOANA_0057_39.csv' # last haul of the day at 4:21 PM local (20:21 GMT)

import numpy as np
import matplotlib.pyplot as plt
import time
import pandas as pd
from datetime import timedelta, datetime
import os
import setup_rtd

def parse_segments(df):  # parse the dataframe into profiling down, fishing and profiling up
        df['DATETIME'] = pd.to_datetime(df['DATETIME'])
        df['DATEINT'] = (df['DATETIME'] - df['DATETIME'].min())
        df['DATEINT'] = df.apply(lambda row: row['DATEINT'].total_seconds(), axis=1)
        df['PRESSURE'] = df['PRESSURE'].astype(float)
        df['GAP_PRESSURE'] = abs(df['PRESSURE'] - df['PRESSURE'].quantile(0.9))

        # df['delta_time'] = df['DATETIME'].diff(periods=-1) / pd.offsets.Second(1)
        # df['vel'] = df['PRESSURE'].diff(periods=-1) / df['delta_time'] * 1000
        # df['vel_smooth'] = df['vel'].rolling(7, center=True, min_periods=1).mean()

        df['type'] = 3

        # True down and False up
        df['direction'] = df['PRESSURE'].shift(1) < df['PRESSURE']
        df['dir'] = df['direction'].rolling(10, center=True, min_periods=1).mean()

        # Direction and pressure
        df.loc[(df['dir'] > 0.5) & (df['GAP_PRESSURE'] > 0.5 * df['GAP_PRESSURE'].max()), 'dir'] = 1
        df.loc[(df['dir'] < 0.5) & (df['GAP_PRESSURE'] > 0.5 * df['GAP_PRESSURE'].max()), 'dir'] = 0

        df.loc[(df['dir'] == 1) & (df['GAP_PRESSURE'] > 0.5 * df['GAP_PRESSURE'].max()), 'direction'] = True
        df.loc[(df['dir'] == 0) & (df['GAP_PRESSURE'] > 0.5 * df['GAP_PRESSURE'].max()), 'direction'] = False

        std_bottom = df[(df['DATETIME'] > df['DATETIME'].quantile(0.1)) & (
                df['DATETIME'] < df['DATETIME'].quantile(0.9))]['PRESSURE'].std()

        nodown, noup = False, False
        if std_bottom < 0.2:
            # Smooth size to find the inflection point
            min_seg_size = 1
            max_down_pressure = df['PRESSURE'].iloc[:min_seg_size].max()
            while max_down_pressure < 0.9 * df['PRESSURE'].max():
                min_seg_size += 1
                max_down_pressure = df['PRESSURE'].iloc[:min_seg_size].max()

            if min_seg_size == 1:
                nodown = True

            min_seg_size = 1
            max_up_pressure = df['PRESSURE'].iloc[-min_seg_size:].max()
            while max_up_pressure < 0.9 * df['PRESSURE'].max():
                min_seg_size += 1
                max_up_pressure = df['PRESSURE'].iloc[-min_seg_size:].max()

            if min_seg_size == 1:
                noup = True

        else:
            # Smooth size to find the inflection point
            min_seg_size = 1
            max_down_pressure = df['PRESSURE'].iloc[:min_seg_size].max()
            while max_down_pressure < 0.5 * df['PRESSURE'].max():
                min_seg_size += 1
                max_down_pressure = df['PRESSURE'].iloc[:min_seg_size].max()

            min_seg_size = 1
            max_up_pressure = df['PRESSURE'].iloc[-min_seg_size:].max()
            while max_up_pressure < 0.5 * df['PRESSURE'].max():
                min_seg_size += 1
                max_up_pressure = df['PRESSURE'].iloc[-min_seg_size:].max()

        df.loc[:min_seg_size, 'direction'] = True
        df.loc[len(df) - min_seg_size:, 'direction'] = False

        lim_pressure = df[~df['direction']].iloc[0], df[df['direction']].iloc[-1]

        df.loc[:lim_pressure[0].name - 1, 'type'] = 2  # Profiling down
        df.loc[lim_pressure[1].name + 1:, 'type'] = 1  # Profiling up

        if nodown:
            df.loc[df['type'] == 2, 'type'] = 3

        if noup:
            df.loc[df['type'] == 1, 'type'] = 3

        gap_rows = (df['DATETIME'].iloc[-1] - df['DATETIME'].iloc[0]).total_seconds() / 60 / (len(df) - 1)
        if gap_rows > 25:
            df['type'] = 3

        return df


# JiM modification:

#data = pd.read_csv(path + 'logs/raw/Moana/' + filename, header=9)
data = pd.read_csv(file, header=9)
data['DATETIME'] = pd.to_datetime(data.Date + ' ' + data.Time, format='%Y-%m-%d %H:%M:%S')
data.rename(columns={'Temperature C': 'TEMPERATURE', 'Depth Decibar': 'PRESSURE'}, inplace=True)
data['TEMPERATURE'] = pd.to_numeric(data['TEMPERATURE'])
data['PRESSURE'] = pd.to_numeric(data['PRESSURE'])
data['TEMPERATURE'] = data.apply(lambda x: round(x['TEMPERATURE'], 4), axis=1)
data['PRESSURE'] = data.apply(lambda x: round(x['PRESSURE'], 3), axis=1)

df=parse_segments(data)
df['TEMPERATURE'] = df['TEMPERATURE'] * 1.8 + 32
df['PRESSURE'] = df['PRESSURE'] * 0.546807
#df['DATETIME'] += timedelta(hours=setup_rtd.parameters['local_time'])
filename = df.iloc[-1]['DATETIME'].strftime('%y-%m-%d %H:%M')

dfrbr=pd.read_csv('rawfiles/RBR.csv', header=0) # reads RBR data and adds 5 hours to make GMT
dfrbr=dfrbr[0::100]# subsample
dfrbr['DATETIME'] = pd.to_datetime(dfrbr.Time, format='%m/%d/%Y %H:%M:%S')+timedelta(hours=5)
#dfrbr.rename(columns={'Temperature': 'TEMPERATURE', 'Pressure': 'PRESSURE'}, inplace=True)
dfrbr.rename(columns={'Temperature': 'TEMPERATURE', 'Depth': 'PRESSURE'}, inplace=True)
dfrbr['TEMPERATURE'] = pd.to_numeric(dfrbr['TEMPERATURE'])
dfrbr['PRESSURE'] = pd.to_numeric(dfrbr['PRESSURE'])
dfrbr['TEMPERATURE'] = dfrbr.apply(lambda x: round(x['TEMPERATURE'], 4), axis=1)
dfrbr['PRESSURE'] = dfrbr.apply(lambda x: round(x['PRESSURE'], 3), axis=1)
dfrbr=dfrbr[dfrbr['DATETIME']>df['DATETIME'].values[0]]
dfrbr=dfrbr[dfrbr['DATETIME']<df['DATETIME'].values[-1]]

#dfrbr=parse_segments(dfrbr)
dfrbr['TEMPERATURE'] = dfrbr['TEMPERATURE'] * 1.8 + 32
dfrbr['PRESSURE'] = dfrbr['PRESSURE'] * 0.546807

fig, ax_c = plt.subplots(figsize=(15, 9))

lns1 = ax_c.plot(df['DATETIME'], df['PRESSURE'], '-', color='deepskyblue', label="pressure",
                         zorder=20,
                         linewidth=10)

ax_c.set_ylabel(setup_rtd.parameters['depth_unit'], fontsize=20)
ax_c.set_xlabel('Local time', fontsize=20)
ax_c.set_xlim(min(df['DATETIME']) - timedelta(minutes=5),
              max(df['DATETIME']) + timedelta(minutes=5))  # limit the plot to logged data
ax_c.set_ylim(min(df['PRESSURE']) - 0.5, max(df['PRESSURE']) + 0.5)
plt.tick_params(axis='both', labelsize=15)
ax_f = ax_c.twinx()
lns2 = ax_f.plot(df['DATETIME'], df['TEMPERATURE'], '--', color='r', label="temperature", zorder=10,
                         linewidth=10)
ax_f.set_xlim(min(df['DATETIME']) - timedelta(minutes=5),
              max(df['DATETIME']) + timedelta(minutes=5))  # limit the plot to logged data
ax_f.set_ylim(min(df['TEMPERATURE']) - 0.5, max(df['TEMPERATURE']) + 0.5)
ax_c.set_ylim(ax_c.get_ylim()[::-1])
plt.title('{vessel} data'.format(vessel=setup_rtd.parameters['vessel_name']), fontsize=20)
ax_f.set_ylabel(setup_rtd.parameters['tem_unit'], fontsize=20)
fig.autofmt_xdate()
lns = lns1 + lns2
labs = [l.get_label() for l in lns]
ax_c.legend(lns, labs, fontsize=15)
plt.tick_params(axis='both', labelsize='large')
#plt.savefig('/home/pi/Desktop/Profiles/' + filename + '/' + filename + '_profile.png')
#plt.savefig(filename + '/' + filename + '_profile.png')
plt.savefig(file[9:22]+'_time_series.png')
plt.close()

#plot up and down
df_down = df[df['type'] == 2].reset_index(drop=True)
df_up = df[df['type'] == 1][::-1].reset_index(drop=True)

#dfr_down = dfrbr[dfrbr['type'] == 2].reset_index(drop=True)
#dfr_up = dfrbr[dfrbr['type'] == 1][::-1].reset_index(drop=True)

# plot discrepancy temperatures over time
fig, ax = plt.subplots(figsize=(12, 12))
mintem_row = df_down.loc[df_down['TEMPERATURE'].idxmin()]
mintem = mintem_row['TEMPERATURE']
dep_mintem = mintem_row['PRESSURE']
# get the row of max value
maxtem_row = df_down.loc[df_down['TEMPERATURE'].idxmax()]
maxtem = maxtem_row['TEMPERATURE']
dep_maxtem = maxtem_row['PRESSURE']
plt.plot(df_down['TEMPERATURE'], df_down['PRESSURE'], 'green', label='Moana down', alpha=0.5, linewidth=10,
                 zorder=1)
tem = plt.scatter(df['TEMPERATURE'], df['PRESSURE'], c=df['TEMPERATURE'],
                          cmap='coolwarm', label='temperature', linewidth=5, zorder=3)
plt.plot(dfrbr['TEMPERATURE'], dfrbr['PRESSURE'], 'red', label='RBR ', alpha=0.5, linewidth=10,
                 zorder=1)
# min_tem = plt.scatter(mintem, -dep_mintem, c='blue')
plt.annotate(round(mintem, 1), (mintem, dep_mintem), fontsize=20, weight='bold')
# max_tem = plt.scatter(maxtem, -dep_maxtem, c='green')
plt.annotate(round(maxtem, 1), (maxtem, dep_maxtem), fontsize=20, weight='bold')
mintem_row1 = df_up.loc[df_up['TEMPERATURE'].idxmin()]
mintem1 = mintem_row1['TEMPERATURE']
dep_mintem1 = mintem_row1['PRESSURE']
# get the row of max value
maxtem_row1 = df_up.loc[df_up['TEMPERATURE'].idxmax()]
maxtem1 = maxtem_row1['TEMPERATURE']
dep_maxtem1 = maxtem_row1['PRESSURE']
plt.plot(df_up['TEMPERATURE'], df_up['PRESSURE'], 'purple', label='Moana up', alpha=0.5, linewidth=10,
                 zorder=1)
plt.annotate(round(mintem1, 1), (mintem1, dep_mintem1), fontsize=20, weight='bold')
plt.annotate(round(maxtem1, 1), (maxtem1, dep_maxtem1), fontsize=20, weight='bold')
ax.set_xlabel("Temperature ({tem_unit})".format(tem_unit=setup_rtd.parameters['tem_unit']), fontsize=20)
ax.set_ylabel("Depth ({depth_unit})".format(depth_unit=setup_rtd.parameters['depth_unit']), fontsize=20)
ax.set_ylim(ax.get_ylim()[::-1])
plt.title("F/V Mister G probe comparison "+datetime.utcfromtimestamp(df['DATETIME'].values[-1].tolist()/1e9).strftime("%m/%d/%Y, %H:%M")+' UTC', fontsize=20)
plt.legend(fontsize=15)
cbar = plt.colorbar(tem, shrink=0.5, aspect=20)
cbar.ax.tick_params(labelsize='large')
plt.tick_params(axis='both', labelsize=15)
#plt.savefig('/home/pi/Desktop/Profiles/' + filename + '/' + filename + '_up_down.png')
plt.savefig(file[9:22] + '_up_down.png')

#plt.close()