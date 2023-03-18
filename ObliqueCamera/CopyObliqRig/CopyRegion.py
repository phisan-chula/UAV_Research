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
import exifread
import argparse
import tomli

class ObliqueBlock:
    def __init__(self, ARGS ):
        with open("OBLIQUE_SYS.toml", mode="rb") as fp:
            self.TOML = tomli.load(fp)
        self.ARGS = ARGS
        self.CACHE = Path('./CACHE')
        self.CACHE.mkdir(parents=True, exist_ok=True)
        dfPHO = self.HarvestPhoto( ARGS.FOLDER )
        gdfPHO = gpd.GeoDataFrame( dfPHO, crs='EPSG:4326', 
                geometry=gpd.points_from_xy( dfPHO.lng, dfPHO.lat ) ) 
        self.gdfPHO = gdfPHO

    def _getLL( self, tags ):
        latlng = []
        for t in ['GPS GPSLatitude', 'GPS GPSLongitude']:
            dms = list( tags[t].values )
            dms = dms[0] + dms[1]/60 + float(dms[2])/3600.
            latlng.append( dms )
        return latlng

    def HarvestPhoto(self, DIR ):
        FOLDER = self.TOML['model'][ARGS.model]['FOLDER']
        RIGPOS = self.TOML['model'][ARGS.model]['RIGPOS']
        LUT = dict( zip( FOLDER, RIGPOS )  )
        NDIGIT = self.TOML['model'][ARGS.model]['NDIGIT']
        jpegs = list( DIR.glob( '**/*.JPG' ) )
        df = pd.DataFrame( jpegs, columns=['PathJPEG'] )
        def MakePath( row, LUT, NDIGIT ):
            STEM = row.PathJPEG.stem
            f = open( row.PathJPEG, 'rb')
            tags = exifread.process_file(f)
            model = tags['Image Model'].values
            lat,lng = self._getLL( tags )
            rig_struct = self.TOML['model'][ARGS.model]
            folder = row.PathJPEG.parents[0].stem
            if folder not in rig_struct['FOLDER']:
                raise Warning( f'{folder} not in rig structure ')
            rigpos = LUT[ folder ]
            rignum = row.PathJPEG.stem[-NDIGIT:]
            pathjpeg = str( row.PathJPEG )
            return [pathjpeg, STEM,model,rigpos,rignum, lat,lng]
        df[['PathJPEG', 'STEM','model', 'RigPos', 'RigNum', 'lat','lng' ]] = df.apply( 
                          MakePath, axis=1, result_type='expand',args=(LUT,NDIGIT) )
        return df 

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
                src = Path(photo.PathJPEG)
                dst = CACHE_RIG.joinpath(  Path(photo.PathJPEG).name )
                #import pdb; pdb.set_trace()
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
parser.add_argument("FOLDER", help="folder of mission log file include folders of oblique images",
                    type=Path )
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

