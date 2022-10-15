#
#
#   EstimLCP : estimate position of an LCP by optiminzing planes of a 
#              Gabel roof. EstimLCP make use of RANSAC to reject point-
#              cloud anomally and uncertain low-quality point-cloud from
#              the ULS.
#
#  Author: Phisan Santitamnont
#          Faculty of Engineer, Chulalongkorn University
#  History : 15 Oct 2022 : initial , version 0.1
#
import pandas as pd
import geopandas as gpd
import numpy as np 
import skspatial.objects as sko
import shapely.geometry as shpgeom
import shapely.affinity as affinity
import yaml
import matplotlib.pyplot as plt
import laspy 
import pyransac3d as pyrsc
import argparse
from pathlib import Path 
plt.switch_backend('TkAgg')

#############################################################################
XYZ = ['x','y','z'] 
class GableRoof:
    """ Levelled gabel roof estation from lidar point-cloud. User input 
        point-clud fall onto the two planes of gabel roof. Software will
        estimate best fit of two planes in which they intersect a ridge
        line segment and its orientation. The centroid of ridge is the solution.
        """
    def __init__(self, ARGS):
        self.ARGS = ARGS
        self.BUFF_CIRC = 2.   # 200% buffered circle 
        self.YAML = yaml.load( ARGS.YAML, Loader=yaml.loader.SafeLoader)
        BAS,WID,LEN = self.YAML['BASE'],self.YAML['WIDTH'],self.YAML['LENGTH']
        self.YAML['HEIGHT'] = np.sqrt( WID**2-(BAS/2)**2 ) 
        self.YAML['RADIUS'] = np.sqrt( (BAS/2)**2+(LEN/2)**2 ) 

    def DoEstimateLCP(self, LCP, FLT_LINE ):
        BAS,WID,LEN = self.YAML['BASE'],self.YAML['WIDTH'],self.YAML['LENGTH']
        HEI,RAD     = self.YAML['HEIGHT'],self.YAML['RADIUS']
        print( f'Reading point cloud by flight-line : "{FLT_LINE}"... ')
        self.LCP_APPROX = LCP
        X,Y,AZI = LCP[0],LCP[1],np.radians(LCP[2])
        self.FLT_LINE  =  FLT_LINE
        if self.ARGS.cache: # hidden option for debugging pupose
            gdfCIRC = self.ReadTarget_CACHE( self.FLT_LINE, X, Y )
        else:
            gdfCIRC = self.ReadTarget( self.FLT_LINE, X, Y )
        print( f'Point cloud on target circle : {len(gdfCIRC):,} ' )
        bnd =gdfCIRC.total_bounds
        print( f'Target circle size (meter) : {bnd[2]-bnd[0]:.1f} x {bnd[3]-bnd[1]:.1f} ' )
        if ARGS.plot: self.PlotRoof([LCP[0],LCP[1],gdfCIRC.z.max()],gdfCIRC,
                    TITLE=f'Target {LCP[0]:.1f},{LCP[1]:.1f}  Circle {self.BUFF_CIRC:.1f}m')
        ##################################################################
        BFLR = self.YAML['BUFF_LFRT'];  BFRD = self.YAML['BUFF_RIDGE']
        Ridge = shpgeom.LineString( [(0,-BFRD*LEN/2),(0,+BFRD*LEN/2) ]) 
        rot = affinity.translate( Ridge, xoff=X, yoff=Y )
        Ridge = affinity.rotate( rot, -AZI, origin=(X,Y), use_radians=True)
        polyL = Ridge.buffer( +BFLR*BAS/2, cap_style=2, single_sided=True )
        polyR = Ridge.buffer( -BFLR*BAS/2, cap_style=2, single_sided=True )
        dfpoly = pd.DataFrame( {'SIDE':['L','R'],'geometry':[polyL,polyR] } )
        gdfpoly = gpd.GeoDataFrame( dfpoly, crs='epsg:32647', geometry=dfpoly.geometry )
        gdfPC = gpd.sjoin( gdfCIRC, gdfpoly, how='inner', predicate='intersects')
        gdfPC.reset_index( drop=True, inplace=True)
        #if ARGS.plot:
        #    self.PlotRoof( [LCP[0],LCP[1],gdfPC.z.max()] ,gdfPC )
        gdfPC.drop(['index_right'],axis=1,inplace=True )
        gdfPC, dfRIDGE = self.FitRoof( gdfPC ) 
        return gdfPC, dfRIDGE 

    def ReadTarget_CACHE( self, FLI_LIN, X, Y ):
        LAS_CIRCLE = Path( 'CACHE/gdfCIRCLE.pkl')
        if LAS_CIRCLE.is_file() and LAS_CIRCLE.exists(): 
            print(f'Reading cached "{LAS_CIRCLE}" ...')
            gdfCIRCLE = pd.read_pickle( LAS_CIRCLE )
        else:
            print(f'Refreshing "{LAS_CIRCLE}" and save cache ...')
            gdfCIRCLE = self.ReadTarget( FLI_LIN, X, Y )
            gdfCIRCLE.to_pickle( LAS_CIRCLE )
        return gdfCIRCLE

    def ReadTarget( self, FLI_LIN, X, Y ):
        with laspy.open( FLI_LIN, 'r') as fh:
            las = fh.read()
            dfLAS = pd.DataFrame( {'x':list(las.x), 'y':list(las.y) , 'z':list(las.z),
                                  'intensity': las.intensity } )
        minx,miny,maxx,maxy=shpgeom.Point( X,Y ).\
                        buffer(self.BUFF_CIRC*self.YAML['RADIUS']).bounds
        dfLAS = dfLAS[(dfLAS.x>minx)&(dfLAS.x<maxx)&(dfLAS.y>miny)&(dfLAS.y<maxy)]
        gdfLAS = gpd.GeoDataFrame( dfLAS, crs='epsg:32647', 
                         geometry=gpd.points_from_xy( dfLAS.x,dfLAS.y) )
        return gdfLAS

    def FitRoof( self, gdfPC ):
        PC = list()  
        for side in ['L','R']:
            dfpnt = gdfPC[gdfPC.SIDE==side].copy()
            plane = pyrsc.Plane()
            best_eq,best_inliers = plane.fit( dfpnt[XYZ].to_numpy() , 
                minPoints = self.YAML['MINPOINTS'], thresh = self.YAML['THRESH'], 
                    maxIteration = self.YAML['MAXITER'])
            npnt = len(dfpnt);  nout = npnt-len(best_inliers); nperc=100*nout/npnt 
            print(f'Fit plane "{side}" outliers : {nperc:.1f}% ({nout}/{npnt})')  
            idx_gdfPC = dfpnt.iloc[ best_inliers ].index 
            gdfPC.loc[ idx_gdfPC ,'inlier'] = True
            # compare pyransac3d with skpatial, not compatible !!! 
            pnt_sk = gdfPC[(gdfPC.SIDE==side)&(gdfPC.inlier==True)].copy()
            pnt_sk.drop(['geometry'],axis=1,inplace=True )
            pln_sk = sko.Plane.best_fit( pnt_sk[XYZ].to_numpy(), tol=None )
            #print(f'Plane equation by pyransac3d {len(best_inliers)}pt : {best_eq}' ) 
            #print(f'Plane equation by skspatial {len(pnt_sk)}pt : {pln_sk.cartesian()}' ) 
            PC.append( [side,pnt_sk,npnt,nout, pln_sk] )
        dfROOF = pd.DataFrame( PC, columns=\
                       ['side','pnt_sk', 'npnt','nout','plane_sk'] )
        VectRidge = dfROOF.iloc[0].plane_sk.intersect_plane( dfROOF.iloc[1].plane_sk )
        for _,row in dfROOF.iterrows():
            def RidgeProjecting( pnt_row, vect ):
                pnt = vect.project_point( [pnt_row.x,pnt_row.y, pnt_row.z] )
                return pnt[0],pnt[1],pnt[2]
            row.pnt_sk[XYZ] = row.pnt_sk.apply( RidgeProjecting, 
                                  axis=1, result_type='expand', args=(VectRidge,)  )
        dfRIDGE = pd.concat( [dfROOF.pnt_sk.iloc[0], dfROOF.pnt_sk.iloc[1] ] )
        return gdfPC, dfRIDGE

    ########################################################################
    def PlotRoof(self, PntXYZ ,dfPnt,RIDGE=None, TITLE=None ):
        Z_ASPECT = 0.5
        cm = plt.cm.get_cmap('RdYlBu_r')  # color by height (Z)
        fig = plt.figure(figsize=(15,15))
        ax = fig.add_subplot(111, projection='3d')
        COL = { 'L':'r', 'R':'g'}
        if 'SIDE' in dfPnt.columns:
            for side in COL.keys():  #  L / R planar
                pnt = dfPnt[dfPnt.SIDE==side]
                ax.scatter( pnt.x, pnt.y, pnt.z, c=COL[side], alpha=0.7 )
            if 'inlier' in dfPnt.columns:
                pnt = dfPnt[dfPnt.inlier!=True]
                ax.scatter( pnt.x, pnt.y, pnt.z, c='k', marker='x', alpha=0.7, s=100 )
        else:
            sc = ax.scatter( dfPnt.x, dfPnt.y, dfPnt.z,c=dfPnt.z, cmap=cm, s=10, marker='o')
            cbar = plt.colorbar( sc )
        ax.scatter( *PntXYZ, c='b', s=400, alpha=0.5 )
        if RIDGE is not None:
            for side,col in COL.items():
                sko_pnt = sko.Points( RIDGE[RIDGE.SIDE==side][XYZ].to_numpy() )
                sko_pnt.plot_3d( ax,s=150, alpha=0.3, color=col )
        ax.set_box_aspect((1, 1, Z_ASPECT)) 
        ax.set_xlabel('X axis'); ax.set_ylabel('Y axis'); ax.set_zlabel('Z axis')
        plt.suptitle( TITLE )
        #plt.savefig('CACHE/Plot_Target.svg')
        plt.show()

#######################################################################
if __name__=="__main__":
    parser = argparse.ArgumentParser(description=\
            'Detect and estimate 3D coordinate of a Gable-roof Lidar Control Plane(LCP)')
    parser.add_argument( 'YAML', help="input YAML file", type=argparse.FileType('r') )
    parser.add_argument('-c','--cache', action='store_true', help='caching the circled target, FOR DEBUGGING only')
    parser.add_argument('-p','--plot', action='store_true', help='plot 3d target and point cloud')
    parser.add_argument('-l','--lcp', action='store', help='LCP name to compute,otherwise all LCPs')
    ARGS = parser.parse_args()
    gr = GableRoof( ARGS )
    lcp = list()
    for k,v in gr.YAML['FLIGHT_LINE'].items():
        #print( k,v)
        df = pd.DataFrame( v,  columns=['LCP', 'x','y','azi'] )
        df['FLIGHT_LINE'] = k
        lcp.append( df )
    dfLCP = pd.concat( lcp, axis=0, ignore_index=True )

    ##############################################################
    if ARGS.lcp is not None:
        dfLCP = dfLCP[dfLCP['LCP']==ARGS.lcp]
    for i,row in dfLCP.iterrows(): 
        print(f'========================== LCP : {row.LCP} ==============================')
        gdfPC, dfRIDGE =  gr.DoEstimateLCP( [row.x,row.y,row.azi] , row.FLIGHT_LINE )
        for side in ('L','R','LR' ):
            if side == 'LR':
                df = dfRIDGE[XYZ].copy()
            else:
                df = dfRIDGE[dfRIDGE.SIDE==side][XYZ].copy()
            df.sort_values(XYZ, axis=0, ascending=True,inplace=True) # colinear points !
            dx,dy,dz = (df.iloc[-1]-df.iloc[0])
            L = np.sqrt( dx**2 + dy**2 + dz**2 )
            az = np.degrees( divmod( np.arctan2( dx,dy ), 2*np.pi)[1] ) 
            print( f'{row.LCP} : {side:2s} ridge length = {L:.3f} m,  az = {az:.1f} deg , slope={dz:+.2f} m')
        print( f'Input {row.LCP}  L={gr.YAML["LENGTH"]} : {row.x:,.3f}, {row.y:,.3f} m  AZ:{row.azi:.1f} deg')
        x,y,z = (df.iloc[0]+df.iloc[-1])/2 # from last loop above
        print( f'Estimate {row.LCP} :      {x:,.3f}, {y:,.3f}, {z:.3f} m')
        if ARGS.plot:
            gr.PlotRoof( dfRIDGE[XYZ].mean(), gdfPC, dfRIDGE, 
                                TITLE='{row.FLIGHT_LINE} @ {row.LCP}' )
 
        #import pdb; pdb.set_trace()

