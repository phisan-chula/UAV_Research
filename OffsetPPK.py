#
#
# OffsetPPK : read DJI/M300 camera marker file and Novatel WayPoint trajectory 
#             then apply the GNSS antenna offset to the CMOS camera.
# P.Santitamnont : Chulalongkorn University
# email : phisan.chula@gmail.com
#
#
import numpy as np
import pandas as pd
import geopandas as gpd
from pyproj import Geod

FLAG = { 0: 'no positioning', 16: 'single-point mode', 34: 'floating solution', 
        50: 'fixed solution' }

################################################################################
def ReadCameraMRK( MRK_FILE ):
    HDR = ['PHOTO', 'UTCTimeSec', 'GPS_Week', 'N_CORR', 'E_CORR', 'H_CORR', 
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
MRKFILE = 'M300_PPK_SBR/Rover/DJI_202211061253_001_Timestamp.MRK'
TRJFILE = './M300_PPK_SBR/PPK_Trajectory.txt'

dfMRK = ReadCameraMRK( MRKFILE )
dfMRK = dfMRK[ [ 'PHOTO',  'UTCTimeSec',  'N_CORR',  'E_CORR',  'H_CORR' ] ]
dfMRK['PHOTO'] = dfMRK['PHOTO'].astype(str)
print( dfMRK[['N_CORR', 'E_CORR', 'H_CORR']].describe() )

dfTRJ = ReadTrajectWP( TRJFILE )
dfTRJ['PHOTO'] = '_EPOCH_'
gdfTRJ = gpd.GeoDataFrame( dfTRJ, crs='EPSG:4326', 
        geometry=gpd.points_from_xy( dfTRJ.Longitude, dfTRJ.Latitude) )
#import pdb ; pdb.set_trace()

################################################################################
dfTRJ = pd.concat( [dfTRJ, dfMRK], axis=0, ignore_index=True)
dfTRJ.set_index( 'UTCTimeSec', drop=True, inplace=True, verify_integrity=True )
dfTRJ.sort_index( axis=0, inplace=True )
dfTRJ = dfTRJ[[ 'GPSTimeSec','Latitude','Longitude', 'H-Ell','SDHoriz','SDHeight' , 
                 'Q','PHOTO','N_CORR','E_CORR','H_CORR' ]]
dfTRJ.interpolate(method='slinear', inplace=True)

dfMRK = dfTRJ[ ~dfTRJ.PHOTO.isin( ['_MRK_'] ) ].copy()
def MakeOffset( row ):
    g = Geod(ellps='WGS84')
    lng_n, lat_n, _ = g.fwd(row.Longitude, row.Latitude,  0.0, row.N_CORR )
    lng,lat,_       = g.fwd(lng_n, lat_n, 90.0, row.E_CORR )
    #import pdb ; pdb.set_trace()
    return [ lat,lng, row['H-Ell']-row.H_CORR ]
dfMRK[['Lat_Cam', 'Lng_Cam', 'h_Cam']] = dfMRK.apply( MakeOffset,axis=1, result_type='expand')
gdfPhoto = gpd.GeoDataFrame( dfMRK, crs='EPSG:4326', 
               geometry=gpd.points_from_xy( dfMRK.Lng_Cam, dfMRK.Lat_Cam ) )
###################################################################################
OUT = 'PrecGeoTag'
print( f'Writing {OUT}+ .gpkg and .csv ...')
gdfTRJ.to_file( OUT+'.gpkg' , driver='GPKG', layer='Trajectory' )
gdfPhoto.to_file( OUT+'.gpkg' , driver='GPKG', layer='Photo' )
#####################################################################
gdfPhoto[ ['PHOTO', 'Lat_Cam', 'Lng_Cam', 'h_Cam' ]].to_csv( OUT+'.csv' , index=False )
#import pdb ; pdb.set_trace()

