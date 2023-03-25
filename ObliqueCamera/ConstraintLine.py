#
#
# ConstraintLine : measurement a contraint vertical or horizontal on
#                  an oblique photo
#
#
#
import numpy as np
from Pix4D_Lib import *
from pathlib import Path
from lmfit import Minimizer, Parameters, report_fit

class ConstraintLine( Pix4dBlock):
    def __init__( self , PIX4D_PATH , PHOTO  ):
        self.PHOTO = PHOTO
        super().__init__( Path( PIX4D_PATH ) )
        WID,HEI = self.CONFIG['SENSOR_SIZE']
        photo = self.dfImage[self.dfImage.ImageStem==self.PHOTO].iloc[0]
        self.ENh_ = self.Image2World( self.PHOTO, (WID/2,HEI/2) ,
                        [ photo.X,photo.Y ], 0.0 ) # approx center of photo

    def VerticalLine( self , p1, p2, DTM ):
        def fcn2min( params, data):
            E,N,h1 = params['E'],params['N'],params['h']
            ji1 = self.World2Image( self.PHOTO, np.matrix( [E,N, h1] ).T )
            if callable(DTM): h2 = DTM( E,N )
            else: h2 = DTM
            ji2 = self.World2Image( self.PHOTO, np.matrix( [E,N, h2 ] ).T )
            model = np.hstack( [ np.array(ji1), np.array(ji2) ] )
            return model-data
        params = Parameters()
        for par,val in zip( ['E','N','h'], self.ENh_ ):
            params.add( par, value=val )
        data = np.array( p1+p2 )
        minner = Minimizer( fcn2min, params, fcn_args=( data, ) )
        result = minner.minimize()
        return result

    def HorizontalLine( self , p1, p2, DTM ):
        if callable(DTM): h = DTM( E,N )
        else: h = DTM
        E_,N_,h_ = self.ENh_
        XYZ1 = self.Image2World( self.PHOTO, p1 , [ E_,N_ ], h ) 
        XYZ2 = self.Image2World( self.PHOTO, p2 , [ E_,N_ ], h ) 
        dist = np.linalg.norm( np.array(XYZ1)-np.array(XYZ2) )

        import pdb ; pdb.set_trace()
        return dist

#################################################################
#################################################################
#################################################################
if __name__ == "__main__":
    RIGNAME = 'X1074'
    photo = ConstraintLine( './CA502_MEA_SmallBlock_F2', RIGNAME )
    p1 = [ 3923.6,  244.1 ] 
    p2 = [ 3863.3, 1170.6 ]
    KNOWN_FOOT =  -8.921
    res = photo.VerticalLine( p1,p2, KNOWN_FOOT )
    report_fit( res )
    P1_ = np.array( [res.params['E'].value, res.params['N'].value, 
                    res.params['h'].value] )
    P2_ = np.array( [res.params['E'].value, res.params['N'].value, 
                     KNOWN_FOOT] )
    P1 = np.array( [665865.308, 1519031.929, 52.260] )
    P2 = np.array( [665865.413, 1519031.845, -8.921] )
    print( f'difference@P1 = {P1-P1_} m.' ) 
    print( f'difference@P2 = {P2-P2_} m.' ) 
    ##################################################
    dist = photo.HorizontalLine( p1,p2, -26 ) # just test, not real
    print( f'Horizonal distance : {dist:.3f} m.' )
    #import pdb ; pdb.set_trace()
