# emolt_realtime
Most of this repository is obsolete python code used to acquire, process, visualize, telemeter, quality control, and serve realtime eMOLT data.
There are however some fairly recent routines added.  There is another repository with the non-realtime eMOLT code.

Note: In Dec 2021, the most up-to-date realtime code was stored in the "Huanxin" branch since he was afraid to overwrite JiMs earlier versions in the "Master" branch.

In 2022, we started posting some up-to-date code on George Maynard's repository https://github.com/GMaynard1/emolt_serverside and https://github.com/GMaynard1/emolt_deckbox

The main acquisition code (on board the vessels) was called "rock_getmatp.py".  Many of the other routines are associated with post-processing both the telemtered and the raw wified data
made change 2022.

In Jan 2024, additions were made to this emolt_realtime repository after the "emolt_rt_qaqc" ERDDAP server was put in place by ODN at http://54.208.149.221:8080/erddap/tabledap/eMOLT_RT_QAQC.html.
These are primarily JiM's post-processing routines like:

get_emolt_erddap.py  - generates a color coded map of surf or bot temps
get_emolt_rt_bottom_temp - generates a time series of realtime bottom temps given site code to compare with non-realtime cases
fvcom2xy_new.py - not yet operational version that includes the emolt_rt_qaqc data
plot_temp_profiles - generates a animation of profiles with a station map

