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
dfMRK = dfMRK[ [ 'EVENT',  'GPSTimeSec',  'N_CORR',  'E_CORR',  'H_CORR' ] ]
dfMRK['EVENT'] = dfMRK['EVENT'].astype(str)
print( dfMRK[['N_CORR', 'E_CORR', 'H_CORR']].describe() )

dfTRJ = ReadTrajectWP( TRJFILE )
dfTRJ['EVENT'] = 'TRAJECTORY'
gdfTRJ = gpd.GeoDataFrame( dfTRJ, crs='EPSG:4326', 
        geometry=gpd.points_from_xy( dfTRJ.Longitude, dfTRJ.Latitude) )

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
    g = Geod(ellps='WGS84')
    lng_N, lat_N, _ = g.fwd( row.Longitude, row.Latitude, 0.0, row.N_CORR )
    lng_E, lat_E, _ = g.fwd( row.Longitude, row.Latitude,90.0, row.E_CORR )
    return [ lat_N,lng_E, row['H-Ell']-row.H_CORR ]
dfPho[['Lat_EOP', 'Lng_EOP', 'h_EOP']] = dfPho.apply( MakeOffset,axis=1,result_type='expand')
gdfEOP = gpd.GeoDataFrame( dfPho, crs='EPSG:4326', 
               geometry=gpd.points_from_xy( dfPho.Lng_EOP, dfPho.Lat_EOP ) ).copy()
#import pdb ; pdb.set_trace()
###################################################################################
OUT = 'PrecGeoTag'
print( f'Writing {OUT}+ .gpkg and .csv ...')
gdfMRK.to_file( OUT+'.gpkg' , driver='GPKG', layer='EventMark' )
gdfTRJ.to_file( OUT+'.gpkg' , driver='GPKG', layer='Trajectory' )
gdfEOP.to_file( OUT+'.gpkg' , driver='GPKG', layer='EOP' )
#####################################################################
for col in [ 'Lat_EOP', 'Lng_EOP' ]:
    gdfEOP[col] = gdfEOP[col].map('{:.9f}'.format)
gdfEOP['h_EOP'] = gdfEOP['h_EOP'].map('{:.3f}'.format)
gdfEOP[ ['EVENT', 'Lat_EOP', 'Lng_EOP', 'h_EOP' ]].to_csv( OUT+'.csv' , index=False )

