#
#
# OffsetPPK : read DJI/M300 camera marker file and Novatel WayPoint trajectory 
#             then apply the GNSS antenna offset to the CMOS camera.
# Author : P.Santitamnont : Chulalongkorn University
# Email  : phisan.chula@gmail.com
# Hisotry : 17 Nov 2022
#
#
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point,LineString
import pymap3d as pm
import argparse
import pathlib

FLAG = { 0: 'no positioning', 16: 'single-point mode', 34: 'floating solution', 
        50: 'fixed solution' }
################################################################################
def ReadCameraMRK( MRK_FILE ):
    HDR = ['EVENT', 'GPSTimeSec', 'GPS_Week', 'N_CORR', 'E_CORR', 'H_CORR', 
             'RT_Lat', 'RT_Lng', 'RT_h', 'Std_N', 'Std_E', 'Std_h', 'Flag' ]
    df = pd.read_csv( MRK_FILE, header=None, names=HDR, delim_whitespace=True )
    def SplitVal( arg ):
        val,param = arg.split( ',')
        if param in ['N','E','V']:
            return float( val )/1000.  # mm to meter 
        else:
            return float( val ) 
    for col in ['N_CORR','E_CORR','H_CORR','RT_Lat','RT_Lng','RT_h','Std_N','Std_E' ]:
        df[col] = df[col].apply( SplitVal )
    #import pdb ; pdb.set_trace()
    return df

################################################################################
def ReadTrajectWP( TRJ_FILE ):
    HDR = '   UTCDate    UTCTimeWeeks     UTCTimeHMS   UTCTimeSec     GPSTimeHMS   GPSTimeSec   '\
            '    Latitude      Longitude        H-Ell      SDHoriz     SDHeight Q'.split()
    df = pd.read_csv( TRJ_FILE, skiprows=19, header=None, names=HDR, delim_whitespace=True )
    return df
    #import pdb ; pdb.set_trace()
################################################################################
################################################################################
################################################################################
if 0:
    TRJFILE = './M300_PPK_SBR/PPK_Trajectory.txt'
    MRKFILE = 'M300_PPK_SBR/Rover/DJI_202211061253_001_Timestamp.MRK'
    dfTRJ = ReadTrajectWP( TRJFILE )
    dfMRK = ReadCameraMRK( MRKFILE )
else:
    parser = argparse.ArgumentParser(description=\
            'Read trajectory file e.g. Novatel/WP and DJI MRK file and calculate'\
            'the photo exposure station corresponding to the time mark and offset'\
            'from trajectory into the camera center.')
    parser.add_argument( 'TRJFILE',  type=argparse.FileType('r'),
            help="input precise TRJFILE from post-processed kinetics (moving baseline)  " )
    parser.add_argument( 'MRKFILE',  type=argparse.FileType('r'),
            help="input YAML configuration file for LCP detection and positioning" )
    ARGS = parser.parse_args()
    dfTRJ = ReadTrajectWP( ARGS.TRJFILE )
    dfMRK = ReadCameraMRK( ARGS.MRKFILE )
#    import pdb ; pdb.set_trace()
dfMRK = dfMRK[ [ 'EVENT',  'GPSTimeSec',  'N_CORR',  'E_CORR',  'H_CORR' ] ]
dfMRK['EVENT'] = dfMRK['EVENT'].astype(str)
print( '========= summary of DJI/P1 offset ========')
print( dfMRK[['N_CORR', 'E_CORR', 'H_CORR']].describe() )

dfTRJ['EVENT'] = 'TRAJECTORY'
gdfTRJ = gpd.GeoDataFrame( dfTRJ, crs='EPSG:4326', 
        geometry=gpd.points_from_xy( dfTRJ.Longitude, dfTRJ.Latitude) )
trj_lin = list()
for i in range( len(gdfTRJ)-1 ):
    p,q = gdfTRJ.iloc[i], gdfTRJ.iloc[i+1]
    trj_lin.append( LineString( [ p.geometry, q.geometry ] ) )
gdfTRJ_LIN = gpd.GeoDataFrame( crs='EPSG:4326', geometry=trj_lin ) 
#import pdb ; pdb.set_trace()

################################################################################
dfTRJ = pd.concat( [dfTRJ, dfMRK], axis=0, ignore_index=True)
dfTRJ.set_index( 'GPSTimeSec', drop=False, inplace=True, verify_integrity=True )
dfTRJ.sort_index( axis=0, inplace=True )
dfTRJ = dfTRJ[[ 'Latitude','Longitude', 'H-Ell','SDHoriz','SDHeight' , 
                 'Q','EVENT','N_CORR','E_CORR','H_CORR' ]]
dfTRJ.interpolate(method='slinear', inplace=True)
dfPho = dfTRJ[ ~dfTRJ.EVENT.isin( ['TRAJECTORY'] ) ].copy()
gdfMRK = gpd.GeoDataFrame( dfPho,  crs='EPSG:4326',
         geometry=gpd.points_from_xy( dfPho.Longitude, dfPho.Latitude ) ).copy()
def MakeOffset( row ):
    lat,lng,hae = pm.enu2geodetic( row.E_CORR, row.N_CORR, -row.H_CORR,
                     row.Latitude, row.Longitude, row['H-Ell'] , ell=None, deg=True)
    return [ lat,lng,hae ]
dfPho[['Lat_EOP', 'Lng_EOP', 'h_EOP']] = dfPho.apply( MakeOffset,axis=1,result_type='expand')
gdfEOP = gpd.GeoDataFrame( dfPho, crs='EPSG:4326', 
               geometry=gpd.points_from_xy( dfPho.Lng_EOP, dfPho.Lat_EOP ) ).copy()
###################################################################################
pathlib.Path('./CACHE').mkdir(parents=True, exist_ok=True)
OUT = './CACHE/PrecGeoTag'
print( f'Writing {OUT}+ .gpkg and .csv ...')
gdfTRJ.to_file(     OUT+'.gpkg' , driver='GPKG', layer='Traj_Point' )
gdfTRJ_LIN.to_file( OUT+'.gpkg' , driver='GPKG', layer='Traj_line' )

gdfMRK.to_file( OUT+'.gpkg' , driver='GPKG', layer='EventMark' )
gdfEOP.to_file( OUT+'.gpkg' , driver='GPKG', layer='EOP' )
#####################################################################
for col in [ 'Lat_EOP', 'Lng_EOP' ]:
    gdfEOP[col] = gdfEOP[col].map('{:.9f}'.format)
gdfEOP['h_EOP'] = gdfEOP['h_EOP'].map('{:.3f}'.format)
gdfEOP[ ['EVENT', 'Lat_EOP', 'Lng_EOP', 'h_EOP' ]].to_csv( OUT+'.csv' , index=False )

