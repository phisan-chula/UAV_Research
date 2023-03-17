#
#
# CopyRegion : Read oblique block from CSV log, plot GPKG and
#              copy photos within ROI to their 'rig' directory.
# Author : P.Santitamnont ( 17 Mar 2023)
#
#
import pandas as pd
import geopandas as gpd
import fiona
import shutil
from pathlib import Path
import argparse
import tomli

class ObliqueBlock:
    def __init__(self, ARGS ):
        with open("OBLIQUE_SYS.toml", mode="rb") as fp:
            self.TOML = tomli.load(fp)
        PREFIX = self.TOML['model'][ARGS.model]['PREFIX']
        NDIGIT = self.TOML['model'][ARGS.model]['NDIGIT']
        self.ARGS = ARGS
        self.CACHE = Path('./CACHE')
        self.CACHE.mkdir(parents=True, exist_ok=True)
        dfPHO = pd.read_csv( ARGS.FILE_LOG )
        gdfPHO = gpd.GeoDataFrame( dfPHO, crs='EPSG:4326', 
                geometry=gpd.points_from_xy( dfPHO.Longitude, dfPHO.Latitude ) ) 
        def MakeRig( row ):
            pos = Path(row.Name).stem[0:-NDIGIT]
            if pos not in PREFIX:
                raise Warning( '***ERROR*** unkown rig position "{pos}"...' )
            cnt = Path(row.Name).stem[-NDIGIT:] 
            return [ pos,cnt ]
        gdfPHO[['RigPos','RigNum']] = gdfPHO.apply( MakeRig, axis=1, result_type='expand' )
        self.gdfPHO = gdfPHO
        #import pdb; pdb.set_trace()

    def Step1_CheckPlot( self):
        print('1. Check rig integrity 5 photos per rig ...' )
        print( self.gdfPHO['RigPos'].value_counts() )
        for rig,grp in self.gdfPHO.groupby(['RigNum']):
            if len(grp) != 5:
                print( f'***ERROR*** rig number "{rig}" has wrong rig postions...' )
                print( grp )
        BLK_PLT = self.CACHE.joinpath( 'ObliqueBlock.gpkg' ) 
        print( f'Plotting oblique block "{BLK_PLT}"...')
        self.gdfPHO.to_file( BLK_PLT , driver='GPKG')

    def Step2_MakeROI(self):
        print('2. Spatial join ROI over photos ...' )
        print(f'Reading ROI from "{ARGS.FILE_ROI}"...' )
        gdfROI = gpd.read_file( ARGS.FILE_ROI )
        dfPHO_ROI = gpd.sjoin( self.gdfPHO,gdfROI, how='inner', predicate='intersects')
        print( f'Number of photos found in ROI = {len(dfPHO_ROI)} ....')
        RigNum_ROI = dfPHO_ROI['RigNum'].unique()
        print( f'Found "{len(RigNum_ROI)}" rigs within the ROI ...')
        gdfPHO_ROI_rig = self.gdfPHO[ self.gdfPHO.RigNum.isin( RigNum_ROI ) ].copy()
        print( f'Number of "rig" photos found in ROI = {len(gdfPHO_ROI_rig)} ....')
        return gdfPHO_ROI_rig
    
    def Step3_CopyPhoto(self, dfPHO ):
        print(f'3. Copy "{len(dfPHO)} photos" to CACHE/PHOTO_RIG/ ...')
        for rigpos,grp in dfPHO.groupby(['RigPos']):
            CACHE_RIG = self.CACHE.joinpath(f'./PHOTO_RIG/{rigpos}' )
            CACHE_RIG.mkdir(parents=True, exist_ok=True)
            for i,photo in grp.iterrows():
                src = Path( photo.Name )
                dst = CACHE_RIG.joinpath( src )
                if self.ARGS.copy:
                    print( f'Copying [{i:05d}]: {src} -> {dst}...' )
                    shutil.copyfile( src, dst ) 
                else:
                    print( f'Planned! copying [{i:05d}]: {src} -> {dst}...' )

##############################################################
##############################################################
##############################################################
#LOG_FILE = 'TransformedPOS8.txt'
#ROI_FILE = 'ROI.geojson'

parser = argparse.ArgumentParser( description='Read oblique block, plot GPKG and '\
        'copy photos within ROI to another directory' )
parser.add_argument("FILE_LOG", help="input log file from oblique camera",
                    type=argparse.FileType('r') )
parser.add_argument("-m", "--model", dest='model', help="oblique camera [ CA502, SHARE_V1, SHARE_V3 ]",
                           ) 
parser.add_argument("-r", "--roi", dest='FILE_ROI', help="input ROI in geojason format",
                    type=argparse.FileType('r'))
parser.add_argument("-c", "--copy", action='store_true', help="do copying files" )

ARGS = parser.parse_args()
print( ARGS )

o_blk = ObliqueBlock( ARGS )
MODEL = o_blk.TOML['model'].keys()
o_blk.Step1_CheckPlot()

if ARGS.FILE_ROI:
    dfROI = o_blk.Step2_MakeROI( )
    o_blk.Step3_CopyPhoto( dfROI )
else:
    o_blk.Step3_CopyPhoto( o_blk.gdfPHO )
print( '======================= finish =======================' )
#import pdb; pdb.set_trace()

