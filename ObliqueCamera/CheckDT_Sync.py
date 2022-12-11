#
#
# CheckDT_Sync.py : read all five-images from obique camera system,
#                   group and modified their datetime* 
#                   by synchronization.
#  P.Santitamnont ( 4 Dec 2022 )
#
#
import datetime
import numpy as np 
import pandas as pd
import geopandas as gpd
from pathlib import Path
from exif import Image

EXIF_DT_FMT = '%Y:%m:%d %H:%M:%S'

##########################################################################
def ReadAllJPEG( PATH_JPEG ):
    data = list()
    for cnt,i in enumerate( PATH_JPEG.glob('./*/*.JPG') ):
        if cnt%100==0: print( f'proecssing rig count={cnt}...' )
        with open( i , 'rb') as fd:
            image = Image( fd )
            dt, orient = image.datetime_digitized, image.orientation.value
        #if cnt==100: break
        data.append( [i, i.stem, i.stem[0] , i.stem[1:], dt , orient] )
    print( f'end of proecssing rig={cnt}...' )

    df = pd.DataFrame( data, columns=[ 'ImagePath',  'ImageName', 
                'RigPos', 'RigName', 'dt_digitized', 'orient' ] )
    def MakeDT(row):
        dt = pd.to_datetime( row.dt_digitized, format=EXIF_DT_FMT )
        return dt
    df['dt'] = df.apply( MakeDT, axis=1 )
    return df

##########################################################################
def AdjustExifDateTime( df, INCR_SEC=1 ):
    ''' Pix4D prefers ADSWX '''
    adj_row = [] ; error_5cam = []
    RUN_NO = 0
    RUN_DT = df.dt.min() 
    for rig_name, row in df.groupby( 'RigName' ):
        print( rig_name )
        if len(row)!=5:
            #print( f'@@@@@@@@@@@@@@@@@ rig name = {rig_name} @@@@@@@@@@@@@@@@@@@')
            #print( '*** ERROR *** number images in rig is not 5!...')
            error_5cam.append( row.ImageName.to_list() )
        if len(row.dt_digitized.unique()) != 1 and len(row)==5:
            #print( f'@@@@@@@@@@@@@@@@@ rig name = {rig_name} @@@@@@@@@@@@@@@@@@@')
            #print( '*** ERROR *** datetime_digitized not the same, adjusting to median()...')
            assert( int(rig_name)>RUN_NO ) 
            if INCR_SEC is None:
                dtAdj = row['dt'].median()
            else:
                dtAdj = RUN_DT + datetime.timedelta( seconds=INCR_SEC )
            row['dtAdj'] = dtAdj 
            #import pdb ; pdb.set_trace()
            #assert( dtAdj.timestamp() > RUN_DT )
            adj_row.append( row )
            RUN_DT = dtAdj
            RUN_NO = int(rig_name)
    print(f'Total JPEG ={len(df):,} ' )
    NRIG = len(adj_row)
    print(f'Total rig = {NRIG:,d}   head = {NRIG*5:,}...' )
    print(f'Total errors ERROR_5CAM={len(error_5cam)} and will be exclueded ...' )
    print( error_5cam )
    return pd.concat( adj_row )

##########################################################################
def ModifyCopyJPEG( dfADJ_DT, DO_COPY=False ):
    for i,row in dfADJ_DT.iterrows():
        infile = row.ImagePath
        outfile = Path('./CACHE').joinpath( infile )
        dtAdj = row.dtAdj.strftime( EXIF_DT_FMT )
        print( dtAdj )
        if DO_COPY==False:
            print('>>> SIMULATION no actual JPEG created ...<<<' )
        print( f'Reading original JPEG {infile} ...' )
        print( f'Update metadata EXIF_DateTime "{dtAdj}"..')
        print( f'Writing modified JPEG {outfile} ...' )
        ##############################################
        if DO_COPY:
            outfile.parent.mkdir(parents=True, exist_ok=True) 
            with open( infile, 'rb' ) as fd_in:
                img = Image( fd_in )
                img.copyright = 'MEA@Dec.2022'
                img.datetime           = dtAdj
                img.datetime_digitized = dtAdj
                img.datetime_original  = dtAdj
                with open( outfile, 'wb' ) as fd_out:
                    fd_out.write( img.get_file() )
     
###########################################################################
###########################################################################
###########################################################################
PATH_JPEG = Path('CA502_CU_SBR_SmallBlock/DATA_SmallBlock/' )
dfAllJPEG = ReadAllJPEG( PATH_JPEG )
dfAdjDT = AdjustExifDateTime( dfAllJPEG, INCR_SEC=1 )

###########################################################################
dt_rig = []  ; dtPrev = None
for grp_rig, row in dfAdjDT.groupby('RigName'):
    assert( len(row)==5 )
    assert( sorted( row.RigPos.to_list()) == ['A', 'D', 'S', 'W', 'X'] )
    diffs = (row.dtAdj - row.iloc[0].dtAdj).dt.total_seconds().to_list()
    assert(  np.allclose( diffs, 0.0) )
    if dtPrev is None:
        dtPrev = row.iloc[0].dtAdj
    else:
        dt_rig.append( (row.iloc[0].dtAdj-dtPrev).total_seconds() )
print( f'Recheck all {len( dfAdjDT):,} rig passed !!!...' )
print( dt_rig )
print( dfAdjDT )
###########################################################################
ModifyCopyJPEG( dfAdjDT, DO_COPY=True )
import pdb ; pdb.set_trace()

         
