#
#
# OffsetPPK : read DJI/M300 camera marker file and Novatel WayPoint trajectory 
#             then apply the GNSS antenna offset to the CMOS camera.
# Author : P.Santitamnont : Chulalongkorn University
# Email  : phisan.chula@gmail.com
# Hisotry : v. 0.1  17 Nov 2022  Initial
#           v. 0.5  4Feb2023 refractoring to class DronePPK
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

class DronePPK:
    def __init__( self , ARGS ):
        self.ARGS = ARGS
        dfTRJ = self.ReadTrajectWP( )
        dfMRK = self.ReadCameraMRK( )
        #####################################
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
        dfTRJ = pd.concat( [dfTRJ, dfMRK], axis=0, ignore_index=True)
        dfTRJ.set_index( 'GPSTimeSec', drop=False, inplace=True, verify_integrity=True )
        dfTRJ.sort_index( axis=0, inplace=True )
        dfTRJ = dfTRJ[[ 'Latitude','Longitude', 'H-Ell','SDHoriz','SDHeight' , 
                         'Q','EVENT','N_CORR','E_CORR','H_CORR' ]]
        dfTRJ.interpolate(method='slinear', inplace=True)
        dfPho = dfTRJ[ ~dfTRJ.EVENT.isin( ['TRAJECTORY'] ) ].copy()
        self.gdfMRK = gpd.GeoDataFrame( dfPho,  crs='EPSG:4326',
                 geometry=gpd.points_from_xy( dfPho.Longitude, dfPho.Latitude ) ).copy()
        def MakeOffset( row ):
            lat,lng,hae = pm.enu2geodetic( row.E_CORR, row.N_CORR, -row.H_CORR,
                             row.Latitude, row.Longitude, row['H-Ell'] , ell=None, deg=True)
            return [ lat,lng,hae ]
        dfPho[['Lat_EOP', 'Lng_EOP', 'h_EOP']] = dfPho.apply( MakeOffset,axis=1,result_type='expand')
        self.gdfEOP = gpd.GeoDataFrame( dfPho, crs='EPSG:4326', 
                       geometry=gpd.points_from_xy( dfPho.Lng_EOP, dfPho.Lat_EOP ) ).copy()
        self.gdfTRJ, self.gdfTRJ_LIN = gdfTRJ, gdfTRJ_LIN

    def ReadCameraMRK( self ):
        HDR = ['EVENT', 'GPSTimeSec', 'GPS_Week', 'N_CORR', 'E_CORR', 'H_CORR', 
                 'RT_Lat', 'RT_Lng', 'RT_h', 'Std_N', 'Std_E', 'Std_h', 'Flag' ]
        df = pd.read_csv( self.ARGS.MRKFILE, header=None, names=HDR, delim_whitespace=True )
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

    def ReadTrajectWP( self ):
        HDR = '   UTCDate    UTCTimeWeeks     UTCTimeHMS   UTCTimeSec     GPSTimeHMS   GPSTimeSec   '\
                '    Latitude      Longitude        H-Ell      SDHoriz     SDHeight Q'.split()
        df = pd.read_csv( self.ARGS.TRJFILE, skiprows=19, header=None, names=HDR, delim_whitespace=True )
        return df

    def WriteResult( self, PREFIX ):
        self.gdfTRJ.to_file(     PREFIX+'.gpkg' , driver='GPKG', layer='Traj_Point' )
        self.gdfTRJ_LIN.to_file( PREFIX+'.gpkg' , driver='GPKG', layer='Traj_line' )
        self.gdfMRK.to_file(     PREFIX+'.gpkg' , driver='GPKG', layer='EventMark' )
        self.gdfEOP.to_file(     PREFIX+'.gpkg' , driver='GPKG', layer='EOP' )
        #####################################################################
        for col in [ 'Lat_EOP', 'Lng_EOP' ]:
            self.gdfEOP[col] = self.gdfEOP[col].map('{:.9f}'.format)
        self.gdfEOP['h_EOP'] = self.gdfEOP['h_EOP'].map('{:.3f}'.format)
        self.gdfEOP[ ['EVENT', 'Lat_EOP', 'Lng_EOP', 'h_EOP' ]].to_csv( PREFIX+'.csv' , index=False )

################################################################################
################################################################################
################################################################################
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=\
            'Read trajectory file e.g. Novatel/WP and DJI MRK file and calculate'\
            'the photo exposure station corresponding to the time mark and offset'\
            'from trajectory into the camera center.')
    parser.add_argument( 'TRJFILE',  type=argparse.FileType('r'),
            help="input precise TRJFILE from post-processed kinetics (moving baseline)  " )
    parser.add_argument( 'MRKFILE',  type=argparse.FileType('r'),
            help="input YAML configuration file for LCP detection and positioning" )
    ARGS = parser.parse_args()
    ppk = DronePPK( ARGS )
    #import pdb ; pdb.set_trace()
    ###################################################################################
    pathlib.Path('./CACHE').mkdir(parents=True, exist_ok=True)
    OUT = './CACHE/PrecGeoTag'
    print( f'Writing {OUT}+ .gpkg and .csv ...')
    ppk.WriteResult( OUT )
    print('******* end of OffsetPPK *******')

