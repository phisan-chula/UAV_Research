#
#
#
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from sklearn.neighbors import KDTree
from pathlib import Path
import io
from Pix4D_Lib import *

class ObliqueView( Pix4dBlock ):
    def __init__(self, ARGS, PIX4D_PATH ):
        PIX4D_PATH = Path( PIX4D_PATH )
        FP_FILE = list(PIX4D_PATH.glob('./dfPix4dBlock_FootPrint.gpkg'))[0]
        TP_FILE = list(PIX4D_PATH.glob('./params/*_tp_pix4d.txt'))[0]
        super().__init__( PIX4D_PATH )
        dfTiePnt = self.ReadP4D_TP( TP_FILE )
        dfFootPr = gpd.read_file( FP_FILE, layer='centroid_poly' )
        self.KDTrees = {}
        for rig in ['S','A','D','W','X']:
            df = dfFootPr[dfFootPr.RigPos==rig].copy()
            df.reset_index( inplace=True )
            pnts = df[df.RigPos==rig].geometry
            self.KDTrees[rig] = [df, KDTree( np.array(list( zip( pnts.x,pnts.y )))) ]
        self.dfTiePnt = dfTiePnt
        self.dfFootPr = dfFootPr
        pass

    def ReadP4D_TP( self, TP_FILE ):
        with open(TP_FILE, 'r') as tp:
            IMG_BEG = 0
            dfs = []
            lines = tp.readlines()
            for i,line in enumerate(lines):
                if line.strip()=='-99':
                    img_lines =  ''.join( lines[IMG_BEG+1:i] )
                    df = pd.read_csv( io.StringIO( img_lines), delim_whitespace=True, 
                           index_col=None, header=None, names=['col','row', 'qlt_key'] )
                    df['image'] =  lines[IMG_BEG].strip()
                    dfs.append( df )
                    IMG_BEG = i+1
        df = pd.concat ( dfs )
        df.reset_index( drop=False, inplace=True) 
        df.rename( columns={'index':'keypnt'} , inplace=True )
        df['keypnt'] = df['keypnt'].astype(str)
        return  df

    def SearchObqView(self, XY ):
        view = []
        for rig, (df,kdTree) in self.KDTrees.items():
            result = kdTree.query( np.array([XY]), k=1)
            dist = result[0][0][0]; kpnt = result[1][0][0]; 
            v = df.iloc[kpnt]
            view.append( [v.RigPos, v.RigName, v.ImageStem, dist] )
        df = pd.DataFrame( view, columns=['RigPos', 'RigName', 'ImageStem', 'dist_m'] )
        return df

    def CopyViewImage( self, dfView ):
        CACHE_VIEW = self.CACHE.joinpath(f'./OBQ_VIEW')
        CACHE_VIEW.mkdir(parents=True, exist_ok=True)
        for i,row in dfView.iterrows():
            src = self.dfImage[ self.dfImage.ImageStem==row.ImageStem ].JPG_Path.iloc[0]
            dst = Path(CACHE_VIEW).joinpath( src.name )
            print( f'CopyRigImage: copying  {src} to {dst}...' )
            shutil.copyfile( src, dst )

##################################################################################
#   S0795
LCP_19 = 717551.850,1606212.081,  5.141
GCP_07 = 717504.492,1606286.262,3.901, 33.619    # N, E , HAE, MSL
args = None
view = ObliqueView( args, './CA502_CU_SBR_SmallBlock' )
df = view.SearchObqView( LCP_19[0:2] ) 
#df = view.SearchObqView( GCP_07[0:2] ) 
print( df )
view.CopyViewImage( df )
#import pdb ; pdb.set_trace()
