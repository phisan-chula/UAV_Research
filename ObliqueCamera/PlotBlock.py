#
#
PROG='''
PlotBlock.py : plot BBA/AT resulting from Pix4D by reading 'parameters folder'
            User supplies necessary configuration data via Tom's Obvious Minimal 
            Language (TOML) BLOCK_CONFIG.toml
 Author  : P.Santitamnont (Phisan.Chula@gmail.com)
 Version : 0.3  ( 2022-12-11 )
'''
#
#
import shutil
from pathlib import Path
from shapely.geometry import box,LineString,Polygon
import numpy as np 
import pandas as pd
import geopandas as gpd
import scipy.optimize 
import tomli
from Pix4D_Lib import *

##########################################################################################
class PlotBlock(Pix4dBlock):
    def __init__( self, ARGS, PIX4D_PATH ):
        super().__init__( PIX4D_PATH )
        self.ARGS = ARGS
        dfImg = self.SelectImageByRigOption()  # specified from self.ARGS
        self.PlotFootPrint( dfImg )  # only selected rig
        self.PlotBlock()
        if self.ARGS.copy: self.CopyRigImage( dfImg )

    def SelectImageByRigOption( self ):
        if self.ARGS.rig is None : 
            return self.dfImage
        if ',' in self.ARGS.rig:
            return self.dfImage[ self.dfImage.RigName.isin( self.ARGS.rig.split(',')) ]
        if ':' in self.ARGS.rig:
            fr,to = self.ARGS.rig.split(':')
            return self.dfImage[ self.dfImage.RigName.between( fr,to)]
        return self.dfImage[ self.dfImage.RigName==self.ARGS.rig ]

    def PlotBlock( self ):
        cen = self.dfImage[ self.dfImage.RigPos=='S' ]
        paths = []
        for i in range( len(cen)-1 ):
            paths.append(LineString( [cen.iloc[i].geometry,cen.iloc[i+1].geometry ] ) )    
        print(f'Plotting Pix4D block {self.BLOCK} ...' )
        dfTraj = gpd.GeoDataFrame( crs='EPSG:32647', geometry=paths  )
        COLS = list( set(cen.columns)-set( ['PMat','JPG_Path' ] ) )
        dfTraj.to_file( self.BLOCK, driver='GPKG', layer='Trajectory' )  
        self.dfImage[COLS].to_file( self.BLOCK, driver='GPKG', layer='Image' ) 

    def PlotFootPrint(self, dfIMAGE):
        ''' ARG.rig number to plot or retrieve images XXX or XXX,YYY,ZZZ or XXX:ZZZ '\
                    'if None, all images will be plotted') '''
        print(f'Plotting foot-print over block {self.BLOCK} ...' )
        fps = [] ; axis = [] ; centr = []
        SX,SY = self.CONFIG['SENSOR_SIZE']
        OFFSET = self.CONFIG['COV_TERRAIN'] if self.ARGS.terrain else self.CONFIG['COV_RELATIVE']
        for _,row in dfIMAGE.iterrows():
            if row.RigPos=='S':
                print( f'Calculation foot-print for rig {row.RigName}' )
            poly = [] 
            for corner in list(box(0,0,SX,SY).exterior.coords):
                xyz = self.Image2World( row.ImageStem, corner, [ row.X,row.Y ], Z=(row.Z-OFFSET) )
                poly.append( xyz )
            fps.append( [row.ImageStem, row.RigPos, row.RigName, Polygon(poly) ] )
            ft_xyz = self.Image2World( row.ImageStem, [SX/2,SY/2], [row.X,row.Y], Z=(row.Z-OFFSET) )
            axis.append( [ row.ImageStem, row.RigPos, row.RigName, 
                           LineString( [(row.X,row.Y,row.Z), (ft_xyz[0],ft_xyz[1],ft_xyz[2]) ]) ] )
            centr.append( [ row.ImageStem, row.RigPos, row.RigName,  Polygon(poly).centroid ] )
 
        dfFoot = pd.DataFrame( fps, columns=[ 'ImageStem','RigPos','RigName', 'geometry'] )
        for group,row in dfFoot.groupby( 'RigPos' ):
            gdf = gpd.GeoDataFrame( row, crs='epsg:32647', geometry=row.geometry ) 
            gdf.to_file( self.BLOCK, driver='GPKG', layer=f'FootPrint_{group}' ) 

        dfAxis = pd.DataFrame( axis, columns=[ 'ImageStem','RigPos','RigName','geometry'] )
        gdfAxis = gpd.GeoDataFrame( dfAxis, crs='epsg:32647', geometry=dfAxis.geometry )
        gdfAxis.to_file( self.BLOCK, driver='GPKG', layer='sensor_axis' )
        
        dfCentr = pd.DataFrame( centr, columns=[ 'ImageStem','RigPos','RigName','geometry'] )
        gdfCentr = gpd.GeoDataFrame( dfCentr, crs='epsg:32647', geometry=dfCentr.geometry )
        gdfCentr.to_file( self.BLOCK, driver='GPKG', layer='centroid_poly' )

        return

#######################################################################################
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=PROG)
    parser.add_argument( '-r','--rig', action='store',
            help='rig number to plot or retrieve images XXX or XXX,YYY,ZZZ or XXX:ZZZ '\
                    'if not specified , all images will be plotted')
    parser.add_argument( '-c','--copy', action='store_true',
            help='copy images to CACHE from specified rig number as specified by -r/--rig opetion ')
    parser.add_argument( '-t','--terrain', action='store_true',
            help='plot image foot-print on the terrain, otherwise plot underneath the sensor' )
    args = parser.parse_args()
    blk = PlotBlock( args, './CA502_CU_SBR_SmallBlock' )
    print('@@@@@@@@@@@@@@@@@@@@@@@ end @@@@@@@@@@@@@@@@@@@@@@@@@@' )

