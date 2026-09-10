"""Conservative frame/lid and connector placement measurements, no PCB edits."""
import json,math
from pathlib import Path
from sexpr import read,child,children,value
from design import ROOT,PARTS
b=read(ROOT/'hub.kicad_pcb');fps={}
for f in children(b,'footprint'):
 p={q[1]:q[2] for q in children(f,'property')};fps[p['Reference']]=f
# Maximum package-height allowances from local source drawing review.
def height(r):
 p=PARTS[r];fp=p['footprint'].split(':')[1]
 if r.startswith('TP'):return 0
 if 'C_1210' in fp:return 2.7
 if 'Coilcraft_XFL' in fp:return 2.1
 if 'SMA' in fp:return 2.62
 if 'SOT-23' in fp:return 1.45
 if 'C_0603' in fp:return .95
 if 'C_0805' in fp:return 1.45
 if 'C_0402' in fp or 'R_0402' in fp or 'R_0603' in fp:return .65
 if r=='U6':return 1.0
 raise ValueError(('unreviewed enclosed part height',r,fp))
frames=[]
for r,w,d,lid in [('SH1',12.8,13.76,2.44),('SH2',29.46,18.6,6.80)]:
 x,y=child(fps[r],'at')[1:3];inside=[]
 for q,f in fps.items():
  if q.startswith('SH') or q not in PARTS:continue
  u,v=child(f,'at')[1:3]
  if abs(u-x)<w/2-.3 and abs(v-y)<d/2-.3:inside.append({'reference':q,'maximum_height_mm':height(q)})
 tallest=max(inside,key=lambda z:z['maximum_height_mm'])
 assert tallest['maximum_height_mm']<lid
 frames.append({'frame':r,'center_mm':[x,y],'outer_envelope_mm':[w,d],'assumed_conservative_lid_underside_mm':lid,'enclosed_parts':inside,'tallest':tallest,'minimum_lid_margin_mm':lid-tallest['maximum_height_mm']})
result={'outline_mm':[136,116],'corner_radius_mm':3,'nominal_thickness_mm':1.6,
 'holes':{r:{'center_mm':child(fps[r],'at')[1:3],'NPTH_diameter_mm':3.2,'reserved_hardware_radius_mm':3.2} for r in ['H1','H2','H3','H4']},
 'frames':frames,'shield_to_shield_edge_gap_mm':(65-29.46/2)-(27.5+12.8/2),
 'connector_centers':{r:child(fps[r],'at')[1:] for r in ['J1','J2','J3','J4','J5','J6']},
 'top_clearance_allowance_mm':15,'bottom_clearance_allowance_mm':5,
 'limits':['Frame inner contours and all footprint courtyards are checked by KiCad DRC. Heights use conservative drawing envelopes; lid tolerances and formed tabs must be checked on received parts.','No commercial enclosure is selected. Reserve plastic enclosure, nylon hardware and connector plug insertion space.','3D models mix manufacturer/third-party STEP and labeled body envelopes. This is not a full solid-contact solver or enclosure-fit certification.']}
(ROOT/'docs/revc/reports/mechanical.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
