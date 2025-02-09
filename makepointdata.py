#!/usr/bin/env python
import os, sys, csv, time, math
from optparse import OptionParser
import numpy
import netcdf4_functions as nffun
from netCDF4 import Dataset

parser = OptionParser()

parser.add_option("--site", dest="site", default='', \
                  help = '6-character FLUXNET code to run (required)')
parser.add_option("--sitegroup", dest="sitegroup", default="AmeriFlux", \
                  help = "site group to use (default AmeriFlux)")
parser.add_option("--lat_bounds", dest="lat_bounds", default='-999,-999', \
                  help = 'latitude range for regional run')
parser.add_option("--lon_bounds", dest="lon_bounds", default='-999,-999', \
                  help = 'longitude range for regional run')
parser.add_option("--crop", dest="crop", default=False, \
                  help = 'Crop compset specified', action="store_true")
parser.add_option("--lai", dest="lai", default=-999, \
                  help = 'Set constant LAI (SP mode only)')
parser.add_option("--model", dest="mymodel", default='', \
                 help = 'Model to use (CLM5 or ELM)')
parser.add_option("--mask", dest="mymask", default='', \
                  help = 'Mask file to use (regional only)')
parser.add_option("--pft", dest="mypft", default=-1, \
                  help = 'Replace all gridcell PFT with this value')
parser.add_option("--point_list", dest="point_list", default='', \
                  help = 'File containing list of points to run (unstructured)')
parser.add_option("--point_area_kmxkm", dest="point_area_km2", default=None, \
                  help = 'user-specific area in km2 of each point in point list (unstructured')
parser.add_option("--point_area_degxdeg", dest="point_area_deg2", default=None, \
                  help = 'user-specific area in degreeXdegree of each point in point list (unstructured')
parser.add_option("--keep_duplicates", dest="keep_duplicates", default=False, \
                  help = 'Keep duplicate points', action='store_true')
parser.add_option("--ccsm_input", dest="ccsm_input", \
                  default='../../../../ccsm_inputdata', \
                  help = "input data directory for CESM (required)")
parser.add_option("--metdir", dest="metdir", default="none", \
                  help = 'subdirectory for met data forcing')
parser.add_option("--makemetdata", dest="makemet", default=False, \
		  help = 'Generate meteorology', action="store_true")
parser.add_option("--surfdata_grid", dest="surfdata_grid", default=False, \
                  help = 'Use gridded soil data', action="store_true")
#parser.add_option("--include_nonveg", dest="include_nonveg", default=False, \
#                      help = "Include non-vegetated fractions from surface data file")
parser.add_option("--res", dest="res", default="hcru_hcru", \
                     help = 'Resolution of global files')
parser.add_option("--nopftdyn", dest="nopftdyn", default=False, \
                     action='store_true', help='Do not make transient PFT file')
parser.add_option("--mysimyr", dest="mysimyr", default=1850, \
                     help = 'Simulation year (1850 or 2000)')
parser.add_option("--humhol", dest="humhol", default=False, \
                  help = 'Use hummock/hollow microtopography', action="store_true")
parser.add_option("--marsh", dest="marsh", default=False, \
                  help = 'Use marsh hydrology/elevation', action="store_true")
parser.add_option("--usersurfnc", dest="usersurfnc", default="none", \
                  help = 'User-provided surface data nc file, with one or more variable(s) as defined')
parser.add_option("--usersurfvar", dest="usersurfvar", default="none", \
                  help = 'variable name(s) in User-provided surface data nc file, separated by ","')
(options, args) = parser.parse_args()


ccsm_input = os.path.abspath(options.ccsm_input)

#------------------- get site information ----------------------------------

#Remove existing temp files
os.system('find ./temp/ -name "*.nc*" -exec rm {} \; ')

lat_bounds = options.lat_bounds.split(',')
lon_bounds = options.lon_bounds.split(',')
lat_bounds = [float(l) for l in lat_bounds]
lon_bounds = [float(l) for l in lon_bounds]

mysimyr=int(options.mysimyr)

if ('hcru' in options.res):
    resx = 0.5
    resy = 0.5
    domainfile_orig = ccsm_input+'/share/domains/domain.clm/domain.lnd.360x720_cruncep.100429.nc'
    if (options.mymodel == 'CLM5'):
        surffile_orig = ccsm_input+'/lnd/clm2/surfdata_map/surfdata_360x720cru_16pfts_Irrig_CMIP6_simyr1850_c170824.nc'
    elif (options.crop):
        surffile_orig = ccsm_input+'/lnd/clm2/surfdata_map/surfdata_360x720cru_24pfts_simyr2000_c150227.nc'
    else:
        if (mysimyr == 2000):
            surffile_orig =  ccsm_input+'/lnd/clm2/surfdata_map/surfdata_360x720cru_simyr2000_c180216.nc'
        else:
            #CMIP6 stype (Hurtt v2)
            surffile_orig = ccsm_input+'/lnd/clm2/surfdata_map/surfdata_360x720cru_simyr1850_c180216.nc'

    pftdyn_orig = ccsm_input+'/lnd/clm2/surfdata_map/landuse.timeseries_360x720cru_hist_simyr1850-2015_c180220.nc'
    nyears_landuse=166
elif ('f19' in options.res):
    domainfile_orig = ccsm_input+'/share/domains/domain.lnd.fv1.9x2.5_gx1v6.090206.nc'
    surffile_orig =  ccsm_input+'/lnd/clm2/surfdata_map/surfdata_1.9x2.5_simyr1850_c180306.nc'
    pftdyn_orig = ccsm_input+'/lnd/clm2/surfdata_map/landuse.timeseries_1.9x2.5_rcp8.5_simyr1850-2100_c141219.nc'
    nyears_landuse=251
    resx = 2.5
    resy = 1.9
elif ('f09' in options.res):
    domainfile_orig = ccsm_input+'/share/domains/domain.lnd.fv0.9x1.25_gx1v6.090309.nc'
    surffile_orig =  ccsm_input+'/lnd/clm2/surfdata_map/surfdata_0.9x1.25_simyr1850_c180306.nc'
    pftdyn_orig = ccsm_input+'/lnd/clm2/surfdata_map/landuse.timeseries_0.9x1.25_rcp8.5_simyr1850-2100_c141219.nc'
    nyears_landuse=251
    resx = 1.25
    resy = 0.9
elif ('ne30' in options.res):
    #domainfile_orig = ccsm_input+'/share/domains/domain.lnd.ne30np4_oEC60to30.20151214.nc'
    #water cycle experiment
    domainfile_orig = ccsm_input+'/share/domains/domain.lnd.ne30np4_oEC60to30v3.161222.nc'  
    #surffile_orig   = ccsm_input+'/lnd/clm2/surfdata_map/surfdata_ne30np4_simyr1850_2015_c171018.nc'
    surffile_orig   = ccsm_input+'/lnd/clm2/surfdata_map/surfdata_ne30np4_simyr1850_c180306.nc'
    pftdyn_orig     = ccsm_input+'/lnd/clm2/surfdata_map/landuse.timeseries_ne30np4_hist_simyr1850_2015_c20171018.nc'
    nyears_landuse  = 166

n_grids=1
issite = False
isglobal = False
lat=[]
lon=[]
if (lat_bounds[0] > -90 and lon_bounds[0] > -180):
    print( '\nCreating regional datasets using '+options.res+ 'resolution')
    if (lon_bounds[0] < 0):
        lon_bounds[0] = lon_bounds[0]+360.
    if (lon_bounds[1] < 0):
        lon_bounds[1] = lon_bounds[1]+360.
elif (options.point_list != ''):
    issite=True
    input_file = open(options.point_list,'r')
    n_grids=0
    point_pfts=[]
    
    # if providing a user-defined nc file for extracting surface data other than standard inputs
    if (options.usersurfnc!='none'):
        if (options.usersurfvar=='none'):
            print('must provide variable name(s) for extracting data from : ',options.usersurfnc)
            sys.exit()
        else:
            mysurfvar = options.usersurfvar.split(',')
        mysurfnc = Dataset(options.usersurfnc,'r') # must provide the full path and file name
        mysurf_lat = numpy.asarray(mysurfnc['LATIXY'])
        mysurf_lon = numpy.asarray(mysurfnc['LONGXY'])
        ix=numpy.where(mysurf_lon<0.0)
        if(ix[0].size>0): mysurf_lon[ix]=mysurf_lon[ix]+360.0
        point_mysurf = {}
        point_ij = []
        for isurfvar in mysurfvar:
            point_mysurf[isurfvar] = []
 
    for s in input_file:
        if (n_grids == 0):
            header = s.split()
        else:
             data = s.split()
             dnum=0
             point_pfts.append(-1)
             for d in data:
                 if ('lon' in header[dnum]): 
                      mylon = float(d)
                      if (mylon < 0):
                          mylon = mylon+360
                      lon.append(mylon)
                 elif ('lat' in header[dnum]):
                      mylat = float(d)
                      lat.append(float(d))
                 elif ('pft' in header[dnum]):
                      point_pfts[n_grids-1] = int(d)
                 if (int(options.mypft) >= 0):    #overrides info in file
                     point_pfts[n_grids-1] = options.mypft
                
                 dnum=dnum+1
             #
             #overrides data from a PCT_PFT nc input file (TIP: only index here to speed-up loop)
             if(options.usersurfnc!='none' and options.usersurfvar!='none'):
                    dx=numpy.abs(mysurf_lon-mylon)
                    dy=numpy.abs(mysurf_lat-mylat)
                    dxy = numpy.sqrt(dx*dx+dy*dy)
                    ixy = numpy.unravel_index(numpy.argmin(dxy, axis=None), dxy.shape)
                    if (n_grids==1):
                        point_ij=[ixy[0],ixy[1]]
                    else:
                        point_ij=numpy.vstack((point_ij,[ixy[0],ixy[1]]))
        
        n_grids=n_grids+1
        if(divmod(n_grids, 100)[1]==0): print("grid counting: \n",n_grids)
    
    #overrides data from a PCT_PFT nc input file, after all index are assembled
    if(options.usersurfnc!='none' and options.usersurfvar!='none'):
        for isurfvar in mysurfvar:
            isurfvar_vals = numpy.asarray(mysurfnc[isurfvar])[:,point_ij[:,0],point_ij[:,1]]
            point_mysurf[isurfvar] = numpy.transpose(isurfvar_vals)

    input_file.close()
    n_grids = n_grids-1
elif (options.site != ''):
    print('\nCreating datasets for '+options.site+' using '+options.res+' resolution')
    issite = True
    AFdatareader = csv.reader(open(ccsm_input+'/lnd/clm2/PTCLM/'+options.sitegroup+'_sitedata.txt',"r"))
    for row in AFdatareader:
        if row[0] == options.site:
            mylon=float(row[3])
            if (mylon < 0):
                mylon=360.0+float(row[3])
            lon.append(mylon)
            lat.append(float(row[4]))
            if ('US-SPR' in options.site or 
                (options.marsh or options.humhol)):
                lon.append(mylon)
                lat.append(float(row[4]))
                n_grids = 2
            startyear=int(row[6])
            endyear=int(row[7])
            alignyear = int(row[8])
else:
    isglobal=True

#get corresponding 0.5x0.5 and 1.9x2.5 degree grid cells
if (options.res == 'hcru_hcru'):
     longxy = (numpy.cumsum(numpy.ones([721]))-1)*0.5
     latixy = (numpy.cumsum(numpy.ones([361]))-1)*0.5 -90.0
elif ('f19' in options.res):
    longxy = (numpy.cumsum(numpy.ones([145]))-1)*2.5-1.25
    latixy_centers = (numpy.cumsum(numpy.ones([96]))-1)*(180.0/95) - 90.0
    latixy = numpy.zeros([97], numpy.float)
    longxy[0]   = 0
    latixy[0]   =  -90
    latixy[96]  =  90
    for i in range(1,96):
        latixy[i] = (latixy_centers[i-1]+latixy_centers[i])/2.0
elif ('f09' in options.res):
    longxy = (numpy.cumsum(numpy.ones([289]))-1)*1.25-0.625
    latixy_centers = (numpy.cumsum(numpy.ones([192]))-1)*(180.0/191) - 90.0
    latixy = numpy.zeros([193], numpy.float)
    longxy[0]   = 0
    latixy[0]   =  -90
    latixy[192]  =  90
    for i in range(1,192):
        latixy[i] = (latixy_centers[i-1]+latixy_centers[i])/2.0
else:
    longxy = nffun.getvar(surffile_orig, 'LONGXY')
    latixy = nffun.getvar(surffile_orig, 'LATIXY')

xgrid_min=[]
xgrid_max=[]
ygrid_min=[]
ygrid_max=[]
for n in range(0,n_grids):
    if (issite):
        lon_bounds = [lon[n],lon[n]]
        lat_bounds = [lat[n],lat[n]]
    xgrid_min.append(-1)
    xgrid_max.append(-1)
    ygrid_min.append(-1)
    ygrid_max.append(-1)
    if ('ne' in options.res):
      if (lon_bounds[0] != lon_bounds[1] or lat_bounds[0] != lat_bounds[1]):
        print('Regional subsets not allowed for ne resolutions.  Use point lists instead')
        sys.exit()
      ygrid_min[n] = 0
      ygrid_max[n] = 0
      mindist=99999
      for i in range(0,longxy.shape[0]-1):
        thisdist = (lon_bounds[0]-longxy[i])**2 + (lat_bounds[0]-latixy[i])**2
        if (thisdist < mindist):
          xgrid_min[n] = i
          xgrid_max[n] = i
          mindist=thisdist
    else:
      
      for i in range(0,longxy.shape[0]-1):
        if (lon_bounds[0] >= longxy[i]):
            xgrid_min[n] = i
            xgrid_max[n] = i
        elif (lon_bounds[1] >= longxy[i+1]):
            xgrid_max[n] = i
      if (lon_bounds[0] == 180 and lon_bounds[1] == 180):  #global
        xgrid_min[n] = 0
        xgrid_max[n] = longxy.shape[0]-2
      for i in range(0,latixy.shape[0]-1):
        if (lat_bounds[0] >= latixy[i]):
            ygrid_min[n] = i
            ygrid_max[n] = i
        elif (lat_bounds[1] >= latixy[i+1]):
            ygrid_max[n] = i
    #print n, lat[n], lon[n], xgrid_max[n], ygrid_max[n]
if (n_grids > 1 and options.site == ''):       #remove duplicate points
  n_grids_uniq = 1
  n_dups = 0
  xgrid_min_uniq = [xgrid_min[0]]
  ygrid_min_uniq = [ygrid_min[0]]
  lon_uniq = [lon[0]]
  lat_uniq = [lat[0]]
  point_pfts_uniq = [point_pfts[0]]
  point_index = [1]
  myoutput = open('point_list_output.txt','w')
  #myoutput.write(str(lon[0])+','+str(lat[0])+','+str(point_index[0])+'\n')
  myoutput.write(str(lon[0])+','+str(lat[0])+','+str(point_index[0])+','+ \
                 str(xgrid_min_uniq[0])+','+str(ygrid_min_uniq[0])+'\n')
    
  print('Total grids', n_grids)
  for n in range (1,n_grids):
      is_unique = True
      #for m in range(0,n_grids_uniq):
      #    if (xgrid_min[n] == xgrid_min_uniq[m] and ygrid_min[n] == ygrid_min_uniq[m] \
      #        and point_pfts[n] == point_pfts_uniq[m]):
      #         n_dups = n_dups+1
      #         is_unique = False
      #         #point_index.append(m+1)
      # the above is time-costing
      if not options.keep_duplicates:
        xidx = numpy.where(numpy.asarray(xgrid_min_uniq) == xgrid_min[n])
        if len(xidx[0])>0: # more than 0 indicates duplicated 'x'
            # search 'y indx' in same positions of 'ygrid_min_uniq' 
            yidx = numpy.where(numpy.asarray(ygrid_min_uniq)[xidx] == ygrid_min[n])
            if len(yidx[0])>0: # both 'x','y' have duplicated points
                pidx = numpy.where(numpy.asarray(point_pfts_uniq)[xidx[0][yidx]] == point_pfts[n])
                if len(pidx[0])>0:
                    n_dups = n_dups + 1
                    is_unique = False
      if (is_unique):
      #if (is_unique or options.keep_duplicates):
          xgrid_min_uniq.append(xgrid_min[n])
          ygrid_min_uniq.append(ygrid_min[n])
          point_pfts_uniq.append(point_pfts[n])      
          lon_uniq.append(lon[n])
          lat_uniq.append(lat[n])
          n_grids_uniq = n_grids_uniq+1
          point_index.append(n_grids_uniq)
          myoutput.write(str(lon[n])+','+str(lat[n])+','+str(point_index[n_grids_uniq-1])+','+ \
                       str(xgrid_min_uniq[n_grids_uniq-1])+','+str(ygrid_min_uniq[n_grids_uniq-1])+'\n')
      #myoutput.write(str(lon[n])+','+str(lat[n])+','+str(point_index[n])+'\n')
  myoutput.close()
  xgrid_min = xgrid_min_uniq
  xgrid_max = xgrid_min_uniq
  ygrid_min = ygrid_min_uniq
  ygrid_max = ygrid_min_uniq
  lon = lon_uniq
  lat = lat_uniq
  point_pfts = point_pfts_uniq
  n_grids = n_grids_uniq
  if (not options.keep_duplicates):
    print(n_grids, ' Unique points')
    print(n_dups, ' duplicate points removed')
  #print(len(point_index))
  #print(point_index)
#---------------------Create domain data --------------------------------------------------

print('Creating domain data')
os.system('mkdir -p ./temp')

# 'AREA' in surfdata.nc is in KM2, which later used for scaling a point
area_orig = nffun.getvar(surffile_orig, 'AREA')

# in case NCO bin path not in $PATH
os.environ["PATH"] += ':/usr/local/nco/bin'
os.environ["PATH"] += ':/Users/f9y/ATS_ROOT/amanzi_tpls-install-master-Debug/bin'

domainfile_tmp = 'domain??????.nc' # filename pattern of 'domainfile_new'
for n in range(0,n_grids):
    nst = str(1000000+n)[1:]
    domainfile_new = './temp/domain'+nst+'.nc'
    if (not os.path.exists(domainfile_orig)):
        print('Error:  '+domainfile_orig+' does not exist.  Aborting')
        sys.exit(1)

    if (isglobal):
        os.system('cp '+domainfile_orig+' '+domainfile_new)
    else:
        os.system('ncks -h -O -d ni,'+str(xgrid_min[n])+','+str(xgrid_max[n])+' -d nj,'+str(ygrid_min[n])+ \
              ','+str(ygrid_max[n])+' '+domainfile_orig+' '+domainfile_new)

    # scaling x/y length for original grid
    if (options.point_area_km2 != None):
        area_n = area_orig[ygrid_min[n],xgrid_min[n]]
        if(float(area_n)>0.0):
            # asssuming a square of area (km2) in projected flat surface system
            # its longitude/latitude range not square anymore
            # (note: this is very coarse estimation)
            side_km = math.sqrt(float(options.point_area_km2))
            if(lat[n]==90.0): lat[n]=lat[n]-0.00001
            if(lat[n]==-90.0): lat[n]=lat[n]+0.00001
            kmratio_lon2lat = math.cos(math.radians(lat[n]))
            re_km = 6371.22
            yscalar = side_km/(math.pi*re_km/180.0*resy)
            xscalar = side_km/(math.pi*re_km/180.0*resx*kmratio_lon2lat)
    if (options.point_area_deg2 != None):
        area_n = area_orig[ygrid_min[n],xgrid_min[n]]
        if(float(area_n)>0.0):
            side_deg = math.sqrt(float(options.point_area_deg2)) # degx X degy, NOT square radians
            yscalar = side_deg/resy
            xscalar = side_deg/resx


    if (issite):
        frac = nffun.getvar(domainfile_new, 'frac')
        mask = nffun.getvar(domainfile_new, 'mask')
        xc = nffun.getvar(domainfile_new, 'xc')
        yc = nffun.getvar(domainfile_new, 'yc')
        xv = nffun.getvar(domainfile_new, 'xv')
        yv = nffun.getvar(domainfile_new, 'yv')
        area = nffun.getvar(domainfile_new, 'area')
        frac[0] = 1.0
        mask[0] = 1
        if (options.site != ''):
            xc[0] = lon[n]
            yc[0] = lat[n]
            xv[0][0][0] = lon[n]-resx/2
            xv[0][0][1] = lon[n]+resx/2
            xv[0][0][2] = lon[n]-resx/2
            xv[0][0][3] = lon[n]+resx/2
            yv[0][0][0] = lat[n]-resy/2
            yv[0][0][1] = lat[n]-resy/2
            yv[0][0][2] = lat[n]+resy/2
            yv[0][0][3] = lat[n]+resy/2
            area[0] = resx*resy*math.pi/180*math.pi/180
            ierr = nffun.putvar(domainfile_new, 'xc', xc)
            ierr = nffun.putvar(domainfile_new, 'yc', yc)
            ierr = nffun.putvar(domainfile_new, 'xv', xv)
            ierr = nffun.putvar(domainfile_new, 'yv', yv)
            ierr = nffun.putvar(domainfile_new, 'area', area)
            
        elif (options.point_area_km2 != None or options.point_area_deg2 != None):
            xc[0] = lon[n]
            yc[0] = lat[n]
            xv[0][0][0] = lon[n]-resx*xscalar
            xv[0][0][1] = lon[n]+resx*xscalar
            xv[0][0][2] = lon[n]-resx*xscalar
            xv[0][0][3] = lon[n]+resx*xscalar
            yv[0][0][0] = lat[n]-resy*yscalar
            yv[0][0][1] = lat[n]-resy*yscalar
            yv[0][0][2] = lat[n]+resy*yscalar
            yv[0][0][3] = lat[n]+resy*yscalar
            area[0] = area[0]*xscalar*yscalar
            if(options.point_area_km2 != None):
                area[0] = float(options.point_area_km2)/re_km/re_km # there is about 0.3% error with calculation above
            ierr = nffun.putvar(domainfile_new, 'xc', xc)
            ierr = nffun.putvar(domainfile_new, 'yc', yc)
            ierr = nffun.putvar(domainfile_new, 'xv', xv)
            ierr = nffun.putvar(domainfile_new, 'yv', yv)
            ierr = nffun.putvar(domainfile_new, 'area', area)
        
        ierr = nffun.putvar(domainfile_new, 'frac', frac)
        ierr = nffun.putvar(domainfile_new, 'mask', mask)
        os.system('ncks -h -O --mk_rec_dim nj '+domainfile_new+' '+domainfile_new)
    elif (options.mymask != ''):
       print('Applying mask from '+options.mymask)
       os.system('ncks -h -O -d lon,'+str(xgrid_min[n])+','+str(xgrid_max[n])+' -d lat,'+str(ygrid_min[n])+ \
              ','+str(ygrid_max[n])+' '+options.mymask+' mask_temp.nc')
       newmask = nffun.getvar('mask_temp.nc', 'PNW_mask')
       ierr = nffun.putvar(domainfile_new, 'mask', newmask)
       os.system('rm mask_temp.nc')

    domainfile_old = domainfile_new

domainfile_new = './temp/domain.nc'
if (n_grids > 1):
    #ierr = os.system('ncrcat -h '+domainfile_list+' '+domainfile_new) # OS error if '_list' too long
    ierr = os.system('find ./temp/ -name "'+domainfile_tmp+ \
                     '" | xargs ls | sort | ncrcat -O -h -o'+domainfile_new)
    if(ierr!=0): raise RuntimeError('Error: ncrcat -', ierr); #os.sys.exit()
    ierr = os.system('nccopy -6 -u '+domainfile_new+' '+domainfile_new+'.tmp') #NC-3  with large dataset support due to 64bit offset
    if(ierr!=0): raise RuntimeError('Error: nccopy -6 -u ', ierr); #os.sys.exit()
    ierr = os.system('ncpdq -h -O -a ni,nj '+domainfile_new+'.tmp '+domainfile_new)
    if(ierr!=0): raise RuntimeError('Error: ncpdq', ierr); #os.sys.exit()
    ierr = os.system('ncrename -h -O -d ni,ni_temp '+domainfile_new+' '+domainfile_new+' ')
    if(ierr!=0): raise RuntimeError('Error: ncrename', ierr); #os.sys.exit()
    ierr = os.system('ncrename -h -O -d nj,ni '+domainfile_new+' '+domainfile_new+' ')
    if(ierr!=0): raise RuntimeError('Error: ncrename', ierr); #os.sys.exit()
    ierr = os.system('ncrename -h -O -d ni_temp,nj '+domainfile_new+' '+domainfile_new+' ')
    if(ierr!=0): raise RuntimeError('Error: ncrename', ierr); #os.sys.exit()
    os.system('find ./temp/ -name '+domainfile_tmp+' -exec rm {} \;')
    os.system('rm '+domainfile_new+'.tmp*')
else:
    ierr = os.system('mv '+domainfile_old+' '+domainfile_new)
    
#
if(ierr==0): 
    # NC-4 classic better for either NC-4 or NC-3 tools, 
    # but 'ncrename' not good with NC-4
    ierr = os.system('nccopy -7 -u '+domainfile_new+' '+domainfile_new+'.tmp')
    if(ierr!=0):
        print('nccopy -7 -u '+domainfile_new+' '+domainfile_new+'.tmp')
        raise RuntimeError('Error: nccopy -7 -u ');# os.sys.exit()
    else:
        ierr = os.system('mv '+domainfile_new+'.tmp '+domainfile_new)

    print("INFO: Extracted and Compiled '"+ domainfile_new + "' FROM: '" + domainfile_orig+"'! \n")
else:
    raise RuntimeError("FAILED: Extracted and Compiled '"+ domainfile_new + "' FROM: '" + domainfile_orig+"'! \n")
    os.sys.exit(-1)


#-------------------- create surface data ----------------------------------
print('Creating surface data')

surffile_tmp = 'surfdata??????.nc' # filename pattern of 'surffile_new'
for n in range(0,n_grids):
    nst = str(1000000+n)[1:]
    surffile_new =  './temp/surfdata'+nst+'.nc'
    if (not os.path.exists(surffile_orig)):
        print('Error:  '+surffile_orig+' does not exist.  Aborting')
        sys.exit(1)
    if (isglobal):
        os.system('cp '+surffile_orig+' '+surffile_new)
    else:
        if ('ne' in options.res):
          os.system('ncks -h -O --fix_rec_dmn time -d gridcell,'+str(xgrid_min[n])+','+str(xgrid_max[n])+ \
            ' '+surffile_orig+' '+surffile_new)
        else:
          os.system('ncks -h -O --fix_rec_dmn time -d lsmlon,'+str(xgrid_min[n])+','+str(xgrid_max[n])+ \
             ' -d lsmlat,'+str(ygrid_min[n])+','+str(ygrid_max[n])+' '+surffile_orig+' '+surffile_new)

    if (issite):
        landfrac_pft = nffun.getvar(surffile_new, 'LANDFRAC_PFT')
        pftdata_mask = nffun.getvar(surffile_new, 'PFTDATA_MASK')
        longxy       = nffun.getvar(surffile_new, 'LONGXY')
        latixy       = nffun.getvar(surffile_new, 'LATIXY')
        area         = nffun.getvar(surffile_new, 'AREA')
        pct_wetland  = nffun.getvar(surffile_new, 'PCT_WETLAND')
        pct_lake     = nffun.getvar(surffile_new, 'PCT_LAKE')
        pct_glacier  = nffun.getvar(surffile_new, 'PCT_GLACIER')
        pct_urban    = nffun.getvar(surffile_new, 'PCT_URBAN')
        if (options.mymodel == 'CLM5' or options.crop):
          pct_crop = nffun.getvar(surffile_new, 'PCT_CROP')
          pct_cft  = nffun.getvar(surffile_new, 'PCT_CFT')
          #put fake P data in this datset
          vars_in = ['LABILE_P','APATITE_P','SECONDARY_P','OCCLUDED_P']
          soil_order = 1
          labilep = 1.0
          primp = 1.0
          secondp = 1.0
          occlp = 1.0
          tempdata = Dataset(surffile_new, 'a')
          for v in vars_in:
            tempvar = tempdata.createVariable(v, 'f4',('lsmlat','lsmlon',))
          tempvar = tempdata.createVariable('SOIL_ORDER', 'i4',('lsmlat','lsmlon',))
          tempdata.close()
        else:
          soil_order   = nffun.getvar(surffile_new, 'SOIL_ORDER')
          labilep      = nffun.getvar(surffile_new, 'LABILE_P')
          primp        = nffun.getvar(surffile_new, 'APATITE_P')
          secondp      = nffun.getvar(surffile_new, 'SECONDARY_P')
          occlp        = nffun.getvar(surffile_new, 'OCCLUDED_P')
        #input from site-specific information
        soil_color   = nffun.getvar(surffile_new, 'SOIL_COLOR')
        pct_sand     = nffun.getvar(surffile_new, 'PCT_SAND')
        pct_clay     = nffun.getvar(surffile_new, 'PCT_CLAY')
        organic      = nffun.getvar(surffile_new, 'ORGANIC')
        fmax         = nffun.getvar(surffile_new, 'FMAX')
        pct_nat_veg  = nffun.getvar(surffile_new, 'PCT_NATVEG')
        pct_pft      = nffun.getvar(surffile_new, 'PCT_NAT_PFT') 
        monthly_lai  = nffun.getvar(surffile_new, 'MONTHLY_LAI')
        monthly_sai  = nffun.getvar(surffile_new, 'MONTHLY_SAI')
        monthly_height_top = nffun.getvar(surffile_new, 'MONTHLY_HEIGHT_TOP')
        monthly_height_bot = nffun.getvar(surffile_new, 'MONTHLY_HEIGHT_BOT')

        npft = 17
        npft_crop = 0
        if (options.crop or options.mymodel == 'CLM5'):
            npft = 15
            npft_crop = 10

        #read file for site-specific PFT information
        mypft_frac = numpy.zeros([npft+npft_crop], numpy.float)
        mypct_sand = 0.0 
        mypct_clay = 0.0
 
        if (options.surfdata_grid == False and options.site != ''):
            #read file for site-specific PFT information
            AFdatareader = csv.reader(open(ccsm_input+'/lnd/clm2/PTCLM/'+options.sitegroup+'_pftdata.txt','r'))
            for row in AFdatareader:
                if row[0] == options.site:
                    for thispft in range(0,5):
                        mypft_frac[int(row[2+2*thispft])]=float(row[1+2*thispft])
            if (sum(mypft_frac[0:npft+npft_crop]) == 0.0):
                print('*** Warning:  PFT data NOT found.  Using gridded data ***')
            #read file for site-specific soil information
            AFdatareader = csv.reader(open(ccsm_input+'/lnd/clm2/PTCLM/'+options.sitegroup+'_soildata.txt','r'))
            for row in AFdatareader:
                if row[0] == options.site:
                    mypct_sand = row[4]
                    mypct_clay = row[5]
            if (mypct_sand == 0.0 and mypct_clay == 0.0):
                print('*** Warning:  Soil data NOT found.  Using gridded data ***')
        else:
          try:
            #mypft_frac[point_pfts[n]] = 100.0
            if(point_pfts[n]!=-1):
                # a single PFT of 100% indicated by input option
                mypft_frac[point_pfts[n]] = 100.0
            else:
                mypft_frac = pct_pft

            # multiple PFTs' pct are read-in from a nc file
            if('PCT_PFT' in mysurfvar or 'PCT_NAT_PFT' in mysurfvar):
                sum_nat=numpy.sum(pct_pft)
                if ('PCT_PFT' in point_mysurf.keys()):
                    if(numpy.sum(point_mysurf['PCT_PFT'][n])>0.0):
                        pct_pft[:,0,0] = point_mysurf['PCT_PFT'][n]
                elif('PCT_NAT_PFT' in point_mysurf.keys()):
                    if(numpy.sum(point_mysurf['PCT_NAT_PFT'][n])>0.0):
                        pct_pft[:,0,0] = point_mysurf['PCT_NAT_PFT'][n]
                else:
                    print('Error: PCT_PFT or PCT_NAT_PFT is used variable name for PFT fraction in surface data')
                    sys.exit()
                # in case PCT not summed to 100.0
                sum_nat2=numpy.sum(pct_pft[:,0,0])
                if (sum_nat2!=100.0):
                    adj=100.0/sum_nat2
                    pct_pft[:,0,0] = pct_pft[:,0,0] * adj
                if (sum_nat<100.0):
                    pct_pft[:,0,0] = pct_pft[:,0,0]*sum_nat/100.0
                if(numpy.sum(pct_pft[:,0,0])!=sum_nat):
                    # this is rare to occur, after TWO corrections above, 
                    # seems due to numerical error relevant to machine
                    # have to fix it if any (will throw error when used by ELM)
                    err=sum_nat - numpy.sum(pct_pft[:,0,0])
                    err_ix=numpy.argmax(pct_pft[:,0,0])
                    pct_pft[err_ix,0,0]=pct_pft[err_ix,0,0]+err
                    print('Error correction - ', err,numpy.sum(pct_pft[:,0,0]))

          except NameError:
            print('using PFT information from surface data')

        #landfrac_pft[0][0] = 1.0
        #pftdata_mask[0][0] = 1

        if (options.site != ''):
            longxy[0][0] = lon[n]
            latixy[0][0] = lat[n]
            area[0] = 111.2*resy*111.321*math.cos((lat[n]*resx)*math.pi/180)*resx
        elif (options.point_area_km2 != None):
            longxy[0][0] = lon[n]
            latixy[0][0] = lat[n]
            area[0] = float(options.point_area_km2)
        elif (options.point_area_deg2 != None): # degx X degy (NOT square radians of area)
            longxy[0][0] = lon[n]
            latixy[0][0] = lat[n]
            side_deg = math.sqrt(float(options.point_area_deg2)) # a square of lat/lon degrees assummed
            area[0][0] = 111.2*side_deg*111.321*math.cos((lat[n]*side_deg)*math.pi/180)*side_deg

        if (not options.surfdata_grid or sum(mypft_frac[0:npft+npft_crop]) > 0.0):
            pct_wetland[0][0] = 0.0
            pct_lake[0][0]    = 0.0
            pct_glacier[0][0] = 0.0
            if (options.crop or options.mymodel == 'CLM5'):
               if sum(mypft_frac[0:npft]) > 0.0:
                 pct_nat_veg[0][0] = 100.0
                 pct_crop[0][0] = 0.0
               else:
                 pct_nat_veg[0][0] = 0.0
                 pct_crop[0][0] = 100.0
            else:
                pct_nat_veg[0][0] = 100.0

            if ('US-SPR' in options.site and mysimyr !=2000):
                #SPRUCE P initial data
                soil_order[0][0] = 3
                labilep[0][0]    = 1.0
                primp[0][0]      = 0.1
                secondp[0][0]    = 1.0
                occlp[0][0]      = 1.0

            for k in range(0,3):
                pct_urban[k][0][0] = 0.0
            for k in range(0,10):
                if (float(mypct_sand) > 0.0 or float(mypct_clay) > 0.0):
                    if (k == 0):
                       print('Setting %sand to '+str(mypct_sand))
                       print('Setting %clay to '+str(mypct_clay))
                    pct_sand[k][0][0]   = mypct_sand
                    pct_clay[k][0][0]   = mypct_clay
                if ('US-SPR' in options.site):
                    if (k < 8):
                        organic[k][0][0] = 130.0
                    elif (k == 8):
                        organic[k][0][0] = 65.0
            # APW: this assumes that PFT labels do not change in the PFT file, consider reading from param file
            pft_names=['Bare ground','ENF Temperate','ENF Boreal','DNF Boreal','EBF Tropical', \
                       'EBF Temperate', 'DBF Tropical', 'DBF Temperate', 'DBF Boreal', 'EB Shrub' \
                       , 'DB Shrub Temperate', 'BD Shrub Boreal', 'C3 arctic grass', \
                       'C3 non-arctic grass', 'C4 grass', 'Crop','xxx','xxx']
            if options.marsh and n==1: # Set tidal channel column in marsh mode to zero PFT area
                print('Setting PFT area in tidal column to zero')
                mypft_frac = numpy.zeros([npft+npft_crop], numpy.float)
                mypft_frac[0]=100.0
            if (options.mypft >= 0 and not (options.marsh and n==1)):
              print('Setting PFT '+str(options.mypft)+'('+pft_names[int(options.mypft)]+') to 100%')
              pct_pft[:,0,0] = 0.0
              pct_pft[int(options.mypft),0,0] = 100.0
            else:
              for p in range(0,npft+npft_crop):
                #if (sum(mypft_frac[0:npft]) > 0.0):
                #if (mypft_frac[p] > 0.0):
                if (p < npft):
                  #if (mypft_frac[p] > 0.0): # too long print for long-list points
                  #  print('Setting Natural PFT '+str(p)+'('+pft_names[p]+') to '+str(mypft_frac[p])+'%')
                  pct_pft[p][0][0] = mypft_frac[p]
                else:
                  #if (mypft_frac[p] > 0.0):
                  #  print('Setting Crop PFT '+str(p)+' to '+str(mypft_frac[p])+'%')
                  pct_cft[p-npft][0][0] = mypft_frac[p]
                  pct_pft[0][0][0] = 100.0
                #maxlai = (monthly_lai).max(axis=0)
                for t in range(0,12):
                    if (float(options.lai) > 0):
                      monthly_lai[t][p][0][0] = float(options.lai)
                    #monthly_lai[t][p][j][i] = monthly_lai[t][p][0][0] 
                    #monthly_sai[t][p][j][i] = monthly_sai[t][p][0][0]
                    #monthly_height_top[t][p][j][i] = monthly_height_top[t][p][0][0]
                    #monthly_height_bot[t][p][j][i] = monthly_height_bot[t][p][0][0]



        ierr = nffun.putvar(surffile_new, 'LANDFRAC_PFT', landfrac_pft)
        ierr = nffun.putvar(surffile_new, 'PFTDATA_MASK', pftdata_mask)
        ierr = nffun.putvar(surffile_new, 'LONGXY', longxy)
        ierr = nffun.putvar(surffile_new, 'LATIXY', latixy)
        ierr = nffun.putvar(surffile_new, 'AREA', area)
        ierr = nffun.putvar(surffile_new, 'PCT_WETLAND', pct_wetland)
        ierr = nffun.putvar(surffile_new, 'PCT_LAKE', pct_lake)
        ierr = nffun.putvar(surffile_new, 'PCT_GLACIER',pct_glacier)
        ierr = nffun.putvar(surffile_new, 'PCT_URBAN', pct_urban)
        if (options.mymodel == 'CLM5' or options.crop):
            ierr = nffun.putvar(surffile_new, 'PCT_CROP', pct_crop)
            ierr = nffun.putvar(surffile_new, 'PCT_CFT', pct_cft)
       
        ierr = nffun.putvar(surffile_new, 'SOIL_ORDER', soil_order)
        ierr = nffun.putvar(surffile_new, 'LABILE_P', labilep)
        ierr = nffun.putvar(surffile_new, 'APATITE_P', primp)
        ierr = nffun.putvar(surffile_new, 'SECONDARY_P', secondp)
        ierr = nffun.putvar(surffile_new, 'OCCLUDED_P', occlp)
        ierr = nffun.putvar(surffile_new, 'SOIL_COLOR', soil_color)
        ierr = nffun.putvar(surffile_new, 'FMAX', fmax)
        ierr = nffun.putvar(surffile_new, 'ORGANIC', organic)
        ierr = nffun.putvar(surffile_new, 'PCT_SAND', pct_sand)
        ierr = nffun.putvar(surffile_new, 'PCT_CLAY', pct_clay)
        ierr = nffun.putvar(surffile_new, 'PCT_NATVEG', pct_nat_veg)
        ierr = nffun.putvar(surffile_new, 'PCT_NAT_PFT', pct_pft)
        ierr = nffun.putvar(surffile_new, 'MONTHLY_HEIGHT_TOP', monthly_height_top)
        ierr = nffun.putvar(surffile_new, 'MONTHLY_HEIGHT_BOT', monthly_height_bot)
        ierr = nffun.putvar(surffile_new, 'MONTHLY_LAI', monthly_lai)
    
    else: # not if(issite)
        if (int(options.mypft) >= 0):
          pct_pft      = nffun.getvar(surffile_new, 'PCT_NAT_PFT')
          pct_pft[:,:,:] = 0.0
          pct_pft[int(options.mypft),:,:] = 100.0
          ierr = nffun.putvar(surffile_new, 'PCT_NAT_PFT', pct_pft)

    surffile_old = surffile_new

surffile_new = './temp/surfdata.nc'

if (n_grids > 1):
  #os.system('ncecat '+surffile_list+' '+surffile_new) # not works with too long '_list'
  ierr = os.system('find ./temp/ -name "'+surffile_tmp+ \
                 '" | xargs ls | sort | ncecat -O -h -o'+surffile_new)
  if(ierr!=0): raise RuntimeError('Error: ncecat '); #os.sys.exit()
  #os.system('rm ./temp/surfdata?????.nc*') # not works with too many files
  os.system('find ./temp/ -name "'+surffile_tmp+'" -exec rm {} \;')

  #remove ni dimension
  ierr = os.system('ncwa -h -O -a lsmlat -d lsmlat,0,0 '+surffile_new+' '+surffile_new+'.tmp')
  if(ierr!=0): raise RuntimeError('Error: ncwa '); #os.sys.exit()
  ierr = os.system('nccopy -6 -u '+surffile_new+'.tmp'+' '+surffile_new+'.tmp2') #NC-3 with large dataset support (64bit offset)
  if(ierr!=0): raise RuntimeError('Error: nccopy -6 -u '); #os.sys.exit()
  ierr = os.system('ncpdq -h -a lsmlon,record '+surffile_new+'.tmp2 '+surffile_new+'.tmp3')
  if(ierr!=0): raise RuntimeError('Error: ncpdq '); #os.sys.exit()
  ierr = os.system('ncwa -h -O -a lsmlon -d lsmlon,0,0 '+surffile_new+'.tmp3 '+surffile_new+'.tmp4')
  if(ierr!=0): raise RuntimeError('Error: ncwa '); #os.sys.exit()
  ierr = os.system('ncrename -h -O -d record,gridcell '+surffile_new+'.tmp4 '+surffile_new+'.tmp5')
  if(ierr!=0): raise RuntimeError('Error: ncrename '); #os.sys.exit()

  os.system('mv '+surffile_new+'.tmp5 '+surffile_new)
  os.system('rm '+surffile_new+'.tmp*')
else:
  os.system('mv '+surffile_old+' '+surffile_new)

# NC-4 classic better for either NC-4 or NC-3 tools (though not writable as NC-4), 
# but 'ncrename' used above may not works with NC-4
ierr = os.system('nccopy -7 -u '+surffile_new+' '+surffile_new+'.tmp')
if(ierr!=0): 
    raise RuntimeError('Error: nccopy -7 -u ');# os.sys.exit()
else:
    ierr = os.system('mv '+surffile_new+'.tmp '+surffile_new)

print("INFO: Extracted and Compiled '"+ surffile_new + "' FROM: '" + surffile_orig+"'! \n")

#-------------------- create pftdyn surface data ----------------------------------

if (options.nopftdyn == False):

  print('Creating dynpft data')
  pftdyn_tmp = 'surfdata.pftdyn??????.nc' # filename pattern of 'pftdyn_new'
  for n in range(0,n_grids):
    nst = str(1000000+n)[1:]
    pftdyn_new = './temp/surfdata.pftdyn'+nst+'.nc'
    
    if (not os.path.exists(pftdyn_orig)):
        print('Error: '+pftdyn_orig+' does not exist.  Aborting')
        sys.exit(1)
    if (isglobal):
        os.system('cp '+pftdyn_orig+' '+pftdyn_new)
    else:
        if ('ne' in options.res):
          os.system('ncks -h -O --fix_rec_dmn time -d gridcell,'+str(xgrid_min[n])+','+str(xgrid_max[n])+ \
                  ' '+pftdyn_orig+' '+pftdyn_new)
        else:
          os.system('ncks -h -O --fix_rec_dmn time -d lsmlon,'+str(xgrid_min[n])+','+str(xgrid_max[n])+ \
                  ' -d lsmlat,'+str(ygrid_min[n])+','+str(ygrid_max[n])+' '+pftdyn_orig+' '+pftdyn_new)
    if (issite):
        landfrac     = nffun.getvar(pftdyn_new, 'LANDFRAC_PFT')
        pftdata_mask = nffun.getvar(pftdyn_new, 'PFTDATA_MASK')
        longxy       = nffun.getvar(pftdyn_new, 'LONGXY')
        latixy       = nffun.getvar(pftdyn_new, 'LATIXY')
        area         = nffun.getvar(pftdyn_new, 'AREA')
        pct_pft      = nffun.getvar(pftdyn_new, 'PCT_NAT_PFT')
        pct_lake_1850    = nffun.getvar(surffile_new, 'PCT_LAKE')
        pct_glacier_1850 = nffun.getvar(surffile_new, 'PCT_GLACIER')
        pct_wetland_1850 = nffun.getvar(surffile_new, 'PCT_WETLAND')
        pct_urban_1850   = nffun.getvar(surffile_new, 'PCT_URBAN')
        pct_pft_1850     = nffun.getvar(surffile_new, 'PCT_NAT_PFT')
        if (options.mymodel == 'CLM5'):
            pct_crop_1850    = nffun.getvar(surffile_new, 'PCT_CROP')
        grazing      = nffun.getvar(pftdyn_new, 'GRAZING')
        harvest_sh1  = nffun.getvar(pftdyn_new, 'HARVEST_SH1')
        harvest_sh2  = nffun.getvar(pftdyn_new, 'HARVEST_SH2')
        harvest_sh3  = nffun.getvar(pftdyn_new, 'HARVEST_SH3')
        harvest_vh1  = nffun.getvar(pftdyn_new, 'HARVEST_VH1')
        harvest_vh2  = nffun.getvar(pftdyn_new, 'HARVEST_VH2')
        
        #read file for site-specific PFT information
        dynexist = False
        mypft_frac=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        if (options.surfdata_grid == False and options.site != ''):
            AFdatareader = csv.reader(open(ccsm_input+'/lnd/clm2/PTCLM/'+options.sitegroup+'_pftdata.txt','r'))
            for row in AFdatareader:
                #print(row[0], row[1], options.site)
                if row[0] == options.site:
                    for thispft in range(0,5):
                        mypft_frac[int(row[2+2*thispft])]=float(row[1+2*thispft])

            if (os.path.exists(ccsm_input+'/lnd/clm2/PTCLM/'+options.site+'_dynpftdata.txt')):
                dynexist = True
                DYdatareader = csv.reader(open(ccsm_input+'/lnd/clm2/PTCLM/'+options.site+'_dynpftdata.txt','r'))
                dim = (19,200)
                pftdata = numpy.zeros(dim)
                for row in DYdatareader:
                    if row[0] == '1850':
                        nrows=1
                        for i in range(0,19):
                            pftdata[i][0] = float(row[i])
                    elif row[0] != 'trans_year':
                        nrows += 1
                        for i in range(0,19):
                            pftdata[i][nrows-1] = float(row[i])
            else:
                print('Warning:  Dynamic pft file for site '+options.site+' does not exist')
                print('Using constant 1850 values')

        landfrac_pft[0][0] = 1.0
        pftdata_mask[0][0] = 1
        if (options.site != ''):
            longxy[0][0] = lon[n]
            latixy[0][0] = lat[n]
            area[0][0] = 111.2*resy*111.321*math.cos((lat[n]*resx)*math.pi/180)*resx
        elif (options.point_area_km2 != None):
            longxy[0][0] = lon[n]
            latixy[0][0] = lat[n]
            area[0] = float(options.point_area_km2)
        elif (options.point_area_deg2 != None): # degx X degy (NOT square radians of area)
            longxy[0][0] = lon[n]
            latixy[0][0] = lat[n]
            side_deg = math.sqrt(float(options.point_area_deg2)) # a square of lat/lon degrees assummed
            area[0][0] = 111.2*side_deg*111.321*math.cos((lat[n]*side_deg)*math.pi/180)*side_deg

        thisrow = 0
        for t in range(0,nyears_landuse):     
            if (options.surfdata_grid == False):
                if (dynexist):
                    for p in range(0,npft):
                        pct_pft[t][p][0][0] = 0.
                    harvest_thisyear = False
                    if pftdata[0][thisrow+1] == 1850+t:
                        thisrow = thisrow+1
                        harvest_thisyear = True
                    if (t == 0 or pftdata[16][thisrow] == 1):
                        harvest_thisyear = True
                    for k in range(0,5):
                        pct_pft[t][int(pftdata[k*2+2][thisrow])][0][0] = \
                            pftdata[k*2+1][thisrow]
                        grazing[t][0][0] = pftdata[17][thisrow]
                        if (harvest_thisyear):
                            harvest_sh1[t][0][0] = pftdata[13][thisrow]
                            harvest_sh2[t][0][0] = pftdata[14][thisrow]
                            harvest_sh3[t][0][0] = pftdata[15][thisrow]
                            harvest_vh1[t][0][0] = pftdata[11][thisrow]
                            harvest_vh2[t][0][0] = pftdata[12][thisrow]
                        else:
                            harvest_sh1[t][0][0] = 0.
                            harvest_sh2[t][0][0] = 0.
                            harvest_sh3[t][0][0] = 0.
                            harvest_vh1[t][0][0] = 0.
                            harvest_vh2[t][0][0] = 0.
                else:
                    for p in range(0,npft):
                        if (sum(mypft_frac[0:16]) == 0.0):
                            #No dyn file - use 1850 values from gridded file
                            pct_pft[t][p][0][0] = pct_pft_1850[p][n]
                        else:
                            #Use specified 1850 values
                            pct_pft[t][p][0][0] = mypft_frac[p]
                    grazing[t][0][0] = 0.
                    harvest_sh1[t][0][0] = 0.
                    harvest_sh2[t][0][0] = 0.
                    harvest_sh3[t][0][0] = 0.
                    harvest_vh1[t][0][0] = 0.
                    harvest_vh2[t][0][0] = 0.
            
                #
                # multiple natural PFTs' pct are read-in from a nc file
                if(options.usersurfnc!='none' and ('PCT_PFT' in mysurfvar or 'PCT_NAT_PFT' in mysurfvar)):
                    print('Message: PCT_NAT_PFT is extracted from a non-dynamical surface data FOR surfdata.pftdyn.nc')
                    sum_nat=numpy.sum(pct_pft[t,:,0,0]) # this is the original, saved for use later
                    if ('PCT_PFT' in point_mysurf.keys()):
                        if(numpy.sum(point_mysurf['PCT_PFT'][n])>0.0):
                            pct_pft[t,:,0,0] = point_mysurf['PCT_PFT'][n]
                    elif('PCT_NAT_PFT' in point_mysurf.keys()):
                        if(numpy.sum(point_mysurf['PCT_NAT_PFT'][n])>0.0):
                            pct_pft[t,:,0,0] = point_mysurf['PCT_NAT_PFT'][n]
                    else:
                        print('Error: PCT_PFT or PCT_NAT_PFT is used variable name for PFT fraction in non-dynamical surface data')
                        sys.exit()
                    # in case new PCT not summed to 100.0
                    sum_nat2=numpy.sum(pct_pft[t,:,0,0]) # this is the updated above
                    if (sum_nat2!=100.0):
                        adj=100.0/sum_nat2
                        pct_pft[t,:,0,0] = pct_pft[t,:,0,0] * adj
                    if (sum_nat<100.0):
                        pct_pft[t,:,0,0] = pct_pft[t,:,0,0]*sum_nat/100.0
                    if(numpy.sum(pct_pft[t,:,0,0])!=sum_nat):
                        # this is rare to occur, after TWO corrections above, 
                        # seems due to numerical error relevant to machine
                        # have to fix it if any (will throw error when used by ELM)
                        err=sum_nat - numpy.sum(pct_pft[t,:,0,0])
                        err_ix=numpy.argmax(pct_pft[t,:,0,0])
                        pct_pft[t,err_ix,0,0]=pct_pft[t,err_ix,0,0]+err

            else:
                #use time-varying files from gridded file
                #print('using '+surffile_new+' for 1850 information') # too much printing if long list points
                nonpft = float(pct_lake_1850[n]+pct_glacier_1850[n]+ \
                               pct_wetland_1850[n]+sum(pct_urban_1850[0:3,n]))
                if (options.mymodel == 'CLM5'):
                    nonpft = nonpft+float(pct_crop_1850[n])
                sumpft = 0.0
                pct_pft_temp = pct_pft
                for p in range(0,npft):
                    sumpft = sumpft + pct_pft_temp[t][p][0][0]
                for p in range(0,npft):
                    if (t == 0):
                        #Force 1850 values to surface data file
                        pct_pft[t][p][0][0] = pct_pft_1850[p][n]
                    else:
                        #Scale time-varying values to non-pft fraction
                        #which might not agree with 1850 values
                        #WARNING: - large errors may result if files are inconsistent
                        pct_pft[t][p][0][0] = pct_pft[t][p][0][0]/sumpft*(100.0) #-nonpft)
            

        ierr = nffun.putvar(pftdyn_new, 'LANDFRAC_PFT', landfrac)
        ierr = nffun.putvar(pftdyn_new, 'PFTDATA_MASK', pftdata_mask)
        ierr = nffun.putvar(pftdyn_new, 'LONGXY', longxy)
        ierr = nffun.putvar(pftdyn_new, 'LATIXY', latixy)
        ierr = nffun.putvar(pftdyn_new, 'AREA', area)
        ierr = nffun.putvar(pftdyn_new, 'PCT_NAT_PFT', pct_pft)
        ierr = nffun.putvar(pftdyn_new, 'GRAZING', grazing)
        ierr = nffun.putvar(pftdyn_new, 'HARVEST_SH1', harvest_sh1)
        ierr = nffun.putvar(pftdyn_new, 'HARVEST_SH2', harvest_sh2)
        ierr = nffun.putvar(pftdyn_new, 'HARVEST_SH3', harvest_sh3)
        ierr = nffun.putvar(pftdyn_new, 'HARVEST_VH1', harvest_vh1)
        ierr = nffun.putvar(pftdyn_new, 'HARVEST_VH2', harvest_vh2)
    pftdyn_old = pftdyn_new

  pftdyn_new = './temp/surfdata.pftdyn.nc'
  if (os.path.isfile(pftdyn_new)):
      print('Warning:  Removing existing pftdyn data file')
      os.system('rm -rf '+pftdyn_new)

  if (n_grids > 1):
      #ios.system('ncecat -h '+pftdyn_list+' '+pftdyn_new) # not works with too long '_list'
      ierr = os.system('find ./temp/ -name "'+pftdyn_tmp+ \
                    '" | xargs ls | sort | ncecat -O -h -o'+pftdyn_new)
      if(ierr!=0): raise RuntimeError('Error: ncecat '); #os.sys.exit()

      #os.system('rm ./temp/surfdata.pftdyn?????.nc*') # 'rm' not works for too long file list
      os.system('find ./temp/ -name "'+pftdyn_tmp+'" -exec rm {} \;')

      #remove ni dimension
      ierr = os.system('ncwa -h -O -a lsmlat -d lsmlat,0,0 '+pftdyn_new+' '+pftdyn_new+'.tmp')
      if(ierr!=0): raise RuntimeError('Error: ncwa '); #os.sys.exit()
      ierr = os.system('nccopy -6 -u '+pftdyn_new+'.tmp'+' '+pftdyn_new+'.tmp2') # NC-3 with large dataset support due to 64bit offset
      if(ierr!=0): raise RuntimeError('Error: nccopy -6 -u '); #os.sys.exit()
      ierr = os.system('ncpdq -h -a lsmlon,record '+pftdyn_new+'.tmp2 '+pftdyn_new+'.tmp3')
      if(ierr!=0): raise RuntimeError('Error: ncpdq '); #os.sys.exit()
      ierr = os.system('ncwa -h -O -a lsmlon -d lsmlon,0,0 '+pftdyn_new+'.tmp3 '+pftdyn_new+'.tmp4')
      if(ierr!=0): raise RuntimeError('Error: ncwa '); #os.sys.exit()
      ierr = os.system('ncrename -h -O -d record,gridcell '+pftdyn_new+'.tmp4 '+pftdyn_new+'.tmp5')
      if(ierr!=0): raise RuntimeError('Error: ncrename '); #os.sys.exit()

      os.system('mv '+pftdyn_new+'.tmp5 '+pftdyn_new)
      os.system('rm '+pftdyn_new+'.tmp*')
  else:
      os.system('mv '+pftdyn_old+' '+pftdyn_new)
      
  
  # NC-4 classic better for either NC-4 or NC-3 tools, 
  # but 'ncrename' used above may not works with NC-4
  ierr = os.system('nccopy -7 -u '+pftdyn_new+' '+pftdyn_new+'.tmp')
  if(ierr!=0):    
      raise RuntimeError('Error: nccopy -7 -u '); #os.sys.exit()
  else:
      ierr = os.system('mv '+pftdyn_new+'.tmp '+pftdyn_new)

  print("INFO: Extracted and Compiled '"+ pftdyn_new + "' FROM: '" + pftdyn_orig+"'! \n")

