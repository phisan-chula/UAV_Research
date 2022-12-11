#
#
# Pix4D.py : plot result BBA/AT resulted from Pix4D by reading from 'parameters folder'
#            user supplies necessary configuration data via Tom's Obvious Minimal 
#            Language (TOML) BLOCK_CONFIG.toml
# Author : P.Santitamnont (Phisan.Chula@gmail.com)
# Version : 0.2  ( 2022-12-05 )
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

##########################################################################################
class Pix4dBlock:
    def __init__( self,PIX4D_PATH ):
        PIX4D_PATH = Path( PIX4D_PATH )
        with open(  PIX4D_PATH.joinpath('BLOCK_INFO.toml'), mode='rb') as fp:
            self.CONFIG = tomli.load(fp)
        print( self.CONFIG ) 
        self.CACHE = Path( './CACHE' )
        self.BLOCK = self.CACHE.joinpath( './dfPix4dBlock.gpkg' )

        PROJCS = list( PIX4D_PATH.glob('./params/*_wkt.prj') )[0]
        with open (PROJCS, 'r') as f : self.PROJCS = f.read()
        #############################################
        PMATRIX = list(PIX4D_PATH.glob('./params/*_pmatrix.txt'))[0]
        dfPMat = pd.read_csv( PMATRIX, delim_whitespace=True, header=None )
        def MakeMat( row ):
            return  np.matrix( row[1:13] ).reshape( 3,4 )
        dfPMat['PMat' ]= dfPMat.apply( MakeMat, axis=1)
        #############################################
        dfJPG = pd.DataFrame( list(PIX4D_PATH.glob('./*/*/*.JPG')), columns=['JPG_Path'] )
        def MakeJPG( row ):
            return  [ row[0].stem, row[0].name , row[0].stem[1:], row[0].stem[0] ]
        dfJPG[ [ 'ImageStem', 'ImageName', 'RigName', 'RigPos' ] ] = \
                                  dfJPG.apply( MakeJPG, axis=1, result_type='expand') 
        #############################################
        EXT_PAR = list(PIX4D_PATH.glob('./params/*_calibrated_external_camera_parameters.txt'))[0]
        dfExt = pd.read_csv( EXT_PAR,  delim_whitespace=True )
        dfImage = pd.merge( dfExt, dfPMat[[0,'PMat']] , how='inner', left_on='imageName', right_on=0 )
        dfImage = pd.merge( dfImage, dfJPG , how='inner', left_on='imageName', right_on='ImageName' )
        self.dfImage = gpd.GeoDataFrame( dfImage, crs='EPSG:32647', 
                       geometry=gpd.points_from_xy( dfImage.X, dfImage.Y, dfImage.Z ) )
        self.dfImage.drop( labels=[0,'imageName'], axis=1, inplace=True )
        self.dfImage.sort_values( by=['RigName','RigPos'], inplace=True )
        #############################################
        OFFSET = list( PIX4D_PATH.glob('./params/*_offset.xyz') )[0]
        self.OFFSET = np.matrix( np.loadtxt( OFFSET ) ).T

    def CopyRigImage( self, RIG_NAME ):
        if type(RIG_NAME) is str: 
            dfIMAGE = self.dfImage[self.dfImage.RigName==RIG_NAME]
        else: 
            dfIMAGE = RIG_NAME
        for grp,row in dfIMAGE.groupby( 'RigName' ):
            CACHE_RIG = self.CACHE.joinpath(f'./{grp}')
            CACHE_RIG.mkdir(parents=True, exist_ok=True)
            for _,img in row.iterrows(): 
                src = img.JPG_Path 
                dst = CACHE_RIG.joinpath( img.ImageName )
                print( f'CopyRigImage: copying  {src} to {dst}...' )
                shutil.copyfile( src, dst ) 

    def World2Image( self, IMAGE_STEM, XYZ ):
        ''' calculate undistorted image coordinate from object coordinate'''
        df = self.dfImage[ self.dfImage.ImageStem==IMAGE_STEM ]
        XYZ_ = XYZ - self.OFFSET
        XYZt = df.iloc[0].PMat * np.vstack( [XYZ_,[[1.]]] )
        uv = XYZt[0,0]/XYZt[2,0], XYZt[1,0]/XYZt[2,0]
        return uv

    def Image2World( self, IMAGE_STEM, UV, XY_APPROX, Z ):
        ''' calculate object coordinate XYZ from image (row,col) 
            given Z must be prior known e.g. from DTM  '''
        def Image2World_CB(  XY, IMAGE_STEM, UV, Z ):
            XYZ = np.matrix( [*XY,Z] ).T
            UV_ = np.array( self.World2Image( IMAGE_STEM, XYZ ) )
            return UV_-np.array( UV )
        X,Y = scipy.optimize.fsolve( Image2World_CB, XY_APPROX, 
                                         args=( IMAGE_STEM,UV,Z) )
        return X,Y,Z 

#######################################################################################
if __name__ == "__main__":
    blk = Pix4dBlock( './CA502_CU_SBR_SmallBlock' )
    df  = blk.CopyRigImage( '0734' )
    print( df )
    ###################################################
    Pnt = np.matrix( [717_480.123, 1_606_280.456 , 6.789 ]).T  # meter
    UV = blk.World2Image( 'S0734', Pnt ) 
    np.set_printoptions(suppress=True)
    print( f'Input  XYZ :   {Pnt.T}' )
    print( f'Output uv :   {UV}' )
    ###################################################
    xyz = blk.Image2World( 'S0734', UV, 
                           [ 717_500,1_606_000 ], Z=6.789 ) 
    print('From image UV to XYZ:\n',  xyz )
    ###################################################

