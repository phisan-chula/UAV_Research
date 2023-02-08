#
#
#
#
#
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path


def MakeGeotag( FILE_TS, FILE_TRJ ): 
    dfTS = pd.read_csv( FILE_TS , delim_whitespace=True, header=None, 
            names=['Time','ImageName'] )
    dfTRJ = pd.read_csv( FILE_TRJ,delim_whitespace=True )
    dfTRJ = dfTRJ[ dfTRJ.columns[:-6] ].copy()

    ##########################################################################
    dfTRJ['ImageName'] = np.nan
    dfTRJ = pd.concat( [dfTRJ, dfTS], axis=0, ignore_index=True)
    dfTRJ.set_index( 'Time', drop=False, inplace=True, verify_integrity=True )
    dfTRJ.sort_index( axis=0, inplace=True)  # inset images into trajectory

    ##########################################################################
    print( dfTRJ[dfTRJ.ImageName.notnull()] )
    dfTRJ.interpolate(method='slinear', inplace=True)
    dfGeotag =  dfTRJ.dropna().copy()

    for col in ['X','Y','Z']:
        dfGeotag[col] = dfGeotag[col].map( '{:.3f}'.format )
    for col in ['Roll','Pitch','Heading']:
        dfGeotag[col] = dfGeotag[col].map( '{:.7f}'.format )
    dfGeotag['AccHor'] = 0.05
    dfGeotag['AccVer'] = 0.10
    STEM = Path( FILE_TS ).parents[0].stem
    print(f'Writing CSV {STEM}...' )
    dfGeotag[['ImageName','X','Y','Z','Heading','Pitch','Roll', 
                'AccHor', 'AccVer']].to_csv(f'{STEM}.csv', index=False) 

#############################################################################
F1_TS = 'Data/MapperPlus_TSV_20230125/RawImage/Flight_1/timestamp F1.dat'
F2_TS = 'Data/MapperPlus_TSV_20230125/RawImage/Flight_2/timestamp F2.dat'

F001_TRJ = 'Data/MapperPlus_TSV_20230125/PointCloud/OneFilePerStrip/Mapper+_CU Sandbox-20230124-180345-F001_trajectory.txt'
F002_TRJ = 'Data/MapperPlus_TSV_20230125/PointCloud/OneFilePerStrip/Mapper+_CU Sandbox-20230124-180345-F002_trajectory.txt'

#for ts,trj in ( [ F1_TS,F001_TRJ ], [ F2_TS, F002_TRJ ] ):
for ts,trj in ( [ F2_TS, F002_TRJ ], ):
    print(f'Input timestamp image file : {ts}...')
    print(f'Input trajectory file : {trj}...')
    MakeGeotag( ts, trj )

print('********** end of IntGeotag ************')
