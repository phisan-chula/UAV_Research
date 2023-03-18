#
#
#
import pandas as pd
import geopandas as gpd
from pathlib import Path
import exifread

def getLL( tags ):
    latlng = []
    for t in ['GPS GPSLatitude', 'GPS GPSLongitude']:
        dms = list( tags[t].values )
        dms = dms[0] + dms[1]/60 + float(dms[2])/3600.
        latlng.append( dms )
    return latlng

DIR = Path( './Data/Testdata' )
LOG = list(DIR.glob('**/TransformedPOS3.csv'))[0]

jpegs = list( DIR.glob( '**/*.JPG' ) )
print( jpegs )

df = pd.DataFrame( jpegs, columns=['PathJPEG'] )
def MakePath( row ):
    STEM = row.PathJPEG.stem
    f = open( row.PathJPEG, 'rb')
    tags = exifread.process_file(f)
    model = tags['Image Model'].values
    lat,lng = getLL( tags )
    return [STEM,model,lat,lng]

df[['STEM','model', 'lat','lng' ]] = df.apply( MakePath, axis=1, result_type='expand' )
import pdb; pdb.set_trace()


