 EstimLCP : estimate position of an LCP by optiminzing planes of a <br/>
              Gabel roof. EstimLCP make use of RANSAC to reject point- <br/>
              cloud anomally and uncertain low-quality point-cloud from <br/>
              the ULS. <br/>
Example result : <br/>         
========================== LCP : LCP-1 ============================== <br/>
Reading point cloud by flight-line : "CU_CHC_AU20/AU20_80mHeight/20220819114421000.las"...  <br/>
Reading cached "CACHE/gdfCIRCLE.pkl" ... <br/>
Point cloud on target circle : 4,259  <br/>
Target circle size (meter) : 3.3 x 3.3  <br/>
Plotting CACHE/Plot_Target.svg... <br/>
Fit plane "L" outliers : 5.8% (32/553) <br/>
Fit plane "R" outliers : 10.5% (30/285) <br/>
LCP-1 : L  ridge length = 1.113 m,  az = 97.5 deg , slope=+0.02 m <br/>
LCP-1 : R  ridge length = 1.110 m,  az = 97.5 deg , slope=+0.02 m <br/>
LCP-1 : LR ridge length = 1.116 m,  az = 97.5 deg , slope=+0.02 m <br/>
Input LCP-1  L=1.22 : 665,572.180, 1,519,337.160 m  AZ:96.0 deg <br/>
Estimate LCP-1 :      665,572.160, 1,519,337.179, 1.328 m <br/>
Plotting CACHE/Plot_Target.svg... <br/>
========================== LCP : LCP-1 ============================== <br/>
Reading point cloud by flight-line : "CU_CHC_AU20/AU20_80mHeight/20220819114527002.las"...  <br/>
Reading cached "CACHE/gdfCIRCLE.pkl" ... <br/>
Point cloud on target circle : 4,259  <br/>
Target circle size (meter) : 3.3 x 3.3  <br/>
Plotting CACHE/Plot_Target.svg... <br/>
Fit plane "L" outliers : 5.8% (32/556) <br/>
Fit plane "R" outliers : 10.5% (30/287) <br/>
LCP-1 : L  ridge length = 1.110 m,  az = 97.2 deg , slope=+0.02 m <br/>
LCP-1 : R  ridge length = 1.110 m,  az = 97.2 deg , slope=+0.02 m <br/>
LCP-1 : LR ridge length = 1.117 m,  az = 97.2 deg , slope=+0.02 m <br/>
Input LCP-1  L=1.22 : 665,572.200, 1,519,337.160 m  AZ:96.0 deg <br/>
Estimate LCP-1 :      665,572.159, 1,519,337.181, 1.328 m <br/>
Plotting CACHE/Plot_Target.svg... <br/>
 <br/>

![LCP Color by Height](https://github.com/phisan-chula/UAV_Research/blob/main/LidarTarget_LCP/Plot_Target_Hgt.svg)

![LCP fitted by two planes](https://github.com/phisan-chula/UAV_Research/blob/main/LidarTarget_LCP/Plot_Target_Fit.svg)
