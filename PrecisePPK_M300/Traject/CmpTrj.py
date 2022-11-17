#
#
#
#
#
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point,LineString
import pymap3d as pm

def ReadTrajectWP( TRJ_FILE ):
    HDR = '   UTCDate    UTCTimeWeeks     UTCTimeHMS   UTCTimeSec     GPSTimeHMS   GPSTimeSec   '\
            '    Latitude      Longitude        H-Ell      SDHoriz     SDHeight Q'.split()
    df = pd.read_csv( TRJ_FILE, skiprows=19, header=None, names=HDR, delim_whitespace=True )
    df.set_index( 'GPSTimeSec' , drop=False, inplace=True )
    return df
    #import pdb ; pdb.set_trace()

##############################################################################################
FILE1 = 'PPK_5Hz.txt'
FILE2 = 'PPK_5Hz_apply_pricise clk_orbit.txt'
FILE3 = 'PPP-Kinematic_5Hz_apply_precise clk_orbit.txt'

df1 = ReadTrajectWP( FILE1 )
df2 = ReadTrajectWP( FILE2 )
df3 = ReadTrajectWP( FILE3 )
df12 = df1.merge( df2, how='inner', left_index=True, right_index=True )
df13 = df1.merge( df3, how='inner', left_index=True, right_index=True )
def CalcENU( row ):
    ENU = pm.geodetic2enu( row.Latitude_x, row.Longitude_x, row['H-Ell_x'],  
            row.Latitude_y, row.Longitude_y, row['H-Ell_y'] )
    return ENU

for df in [df12,df13]:
    df[ ['E','N','U'] ] = df.apply( CalcENU, axis=1, result_type='expand' ) 
    print( df[['E','N','U']].describe() )

import pdb; pdb.set_trace()
