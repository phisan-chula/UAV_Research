#
# ChkLCP_strip.py : read all point-cloud (.las) from each overlapping
#                   strips , creat convex hull around each strip then
#                   intersects with LCP. The result of LCP presents in
#                   any strip will be write down in YAML file.
#
import laspy
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiPoint
from pathlib import Path

YAML_HDR ='''VERSION : "0.3"
# configuration and data file for lidar control plane
#
# LCP defintion
BASE  : 1.100     # m separation of the two planes from field
WIDTH : 0.65     # m  of the future board
LENGTH : 1.220   # m  of the future board
#
#
BUFF_RIDGE : 1.2   # %buffer from actual LCP size
BUFF_LFRT  : [0.1,0.8]   # %buffer to the left&right of  LCP ridge line 
#
# Lidar sensor response via "pyransac3d"
MINPOINTS : 100
THRESH    : 0.05   # meter
MAXITER   : 1000
'''
class LidarBlock:
    def __init__(self, FILE_LAS):
        FILE_RTK = '**/LCP_RTKh.csv' 
        Path('./CACHE').mkdir(parents=True, exist_ok=True)

        dfStrip = self.CreateStrip( FILE_LAS, BUF=-3 )
        LCP_RTK = list(Path( FILE_LAS ).parents[1].glob(FILE_RTK))
        assert( len(LCP_RTK)==1 )
        dfLCP = pd.read_csv( LCP_RTK[0] )
        dfLCP = gpd.GeoDataFrame( dfLCP, crs='EPSG:32647', 
                geometry=gpd.points_from_xy( dfLCP.Easting, dfLCP.Northing ) )
        self.dfStripLCP = gpd.sjoin( dfStrip, dfLCP, how='inner', predicate='intersects' )
        self.dfStripLCP.reset_index( drop=True, inplace=True )
        self.dfStrip = dfStrip
        self.dfLCP = dfLCP

    def CreateHull(self, INFILE ):
        # Open the point cloud file using laspy
        with laspy.open(INFILE,mode='r') as inFile:
            xyz = inFile.read().xyz
            # Create a pandas dataframe from the coordinates
            df = pd.DataFrame({'x': xyz[:,0], 'y': xyz[:,1], 'z': xyz[:,2] })
            df = df.sample( n= int(len(df)/1000) )  # n-times reduced
        hull = MultiPoint(df[['x','y']].values).convex_hull
        npnt = len(hull.exterior.coords)
        return hull,npnt

    def CreateStrip(self, PATTERN,BUF ):
        data =list()
        for INFILE in sorted( Path('.').glob( PATTERN) ):
            hull,npnt = self.CreateHull( INFILE )
            print('Creating hull from strip {} with {} points'.\
                    format(INFILE, npnt))
            data.append( [ str(INFILE), INFILE.stem, npnt, hull.buffer(BUF) ] )
            #if len(data)==2: break
        df = pd.DataFrame( data , columns=['infile', 'strip', 'npnt', 'geometry'] )
        gdf = gpd.GeoDataFrame( df, crs='EPSG:32647', geometry=df.geometry )
        return gdf

    def WriteBlock( self ):
        FILE_GPCK = './CACHE/LidarBlock.gpkg'
        print(f'Writing "{FILE_GPCK}" ...')
        self.dfLCP.to_file( FILE_GPCK, driver='GPKG', layer='LCP' )
        for idx in self.dfStrip.index:
            strip = self.dfStrip.iloc[idx:idx+1] 
            strip.to_file( FILE_GPCK, driver='GPKG', layer=f'{strip.iloc[0].strip}' )

    def WriteYAML( self ):
        FILE_YAML = 'CACHE/PARAMETER_LCP.yaml'
        print(f'Writing "{FILE_YAML}"...')
        with open( FILE_YAML,'w') as f:
            f.write( YAML_HDR )
            f.write('FLIGHT_LINE :\n')
            for name,dflcp in self.dfStripLCP.groupby('strip'):
                f.write( '{}"{}"\n'.format( 4*' ', dflcp.iloc[0].infile ) )
                for idx,lcp in dflcp.iterrows():
                    f.write( '{} - [ {},{},{},{},{} ]\n'.format( 8*' ', 
                        lcp.NAME, lcp.Easting, lcp.Northing , lcp.HAE, lcp.AZ ) )

#######################################################################
#######################################################################
#######################################################################
FILE_LAS = './Data/AA450/Las File/AA450-*.las'

lb = LidarBlock( FILE_LAS )
lb.WriteBlock()
lb.WriteYAML()

print('******* end of ChkLCP_strip.py ********')
#import pdb ; pdb.set_trace()

