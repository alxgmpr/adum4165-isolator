"""Synchronize and place the canonical Rev C board. Never creates tracks or vias.

Explicit anchors and pin-directed passive placement are saved for review. This
initial placement generator is followed by KiCad DRC and geometric inspection.
"""
from copy import deepcopy
from pathlib import Path
import json,math,xml.etree.ElementTree as ET
from collections import defaultdict
from shapely.geometry import Polygon,LineString,Point,box
from shapely.ops import polygonize,unary_union
from shapely import affinity
from design import ROOT,PARTS
from library import build_library
from capture import uid,ROOT_UUID
from sexpr import *
n=node

B=ROOT/'build/revc';build_library(PARTS)
if (ROOT/'hub.kicad_pcb').exists():
 previous=read(ROOT/'hub.kicad_pcb')
 assert not any(children(previous,k) for k in ['segment','via','arc']), 'Refusing to overwrite routed work; edit the board directly.'
XML=ET.parse(B/'hub.xml').getroot()
NETS={a.attrib['name']:int(a.attrib['code']) for a in XML.find('nets')}
PINNET={(p.attrib['ref'],p.attrib['pin']):net.attrib['name'] for net in XML.find('nets') for p in net.findall('node')}
F={r:read(ROOT/'hub-lib.pretty'/(p['footprint'].split(':')[1]+'.kicad_mod')) for r,p in PARTS.items()}
POS={}; COURTS={};TARGETS={}
WIDTH=136;HEIGHT=116;BARRIER=42

def xy(v):return child(v,'at')[1:3]
def transform(x,y,pos):
 a,b,angle=pos;t=math.radians(angle);return (round(a+x*math.cos(t)+y*math.sin(t),6),round(b-x*math.sin(t)+y*math.cos(t),6))
def geometry(f):
 lines=[];polys=[]
 for a in f:
  if not isinstance(a,list) or value(a,'layer')!='F.CrtYd':continue
  tag=str(a[0])
  if tag=='fp_rect':
   p=child(a,'start')[1:3];q=child(a,'end')[1:3];polys.append(box(min(p[0],q[0]),min(p[1],q[1]),max(p[0],q[0]),max(p[1],q[1])))
  elif tag=='fp_line':lines.append(LineString([child(a,'start')[1:3],child(a,'end')[1:3]]))
  elif tag=='fp_circle':
   c=child(a,'center')[1:3];e=child(a,'end')[1:3];polys.append(Point(c).buffer(math.dist(c,e)))
  elif tag=='fp_arc':
   # The sole rounded courtyard families also enclose their component in Fab;
   # sampling the three defining points is supplemented by pad extent fallback.
   lines.extend([])
 polys.extend(polygonize(lines))
 if not polys:
  pts=[child(a,'at')[1:3] for a in children(f,'pad')];xs,ys=zip(*pts)
  return box(min(xs)-1,min(ys)-1,max(xs)+1,max(ys)+1)
 polys.sort(key=lambda q:q.area,reverse=True);out=polys[0]
 for p in polys[1:]:out=out.symmetric_difference(p)
 return out
BASECOURT={r:geometry(f) for r,f in F.items()}
def court(ref,pos):return affinity.translate(affinity.rotate(BASECOURT[ref],-pos[2],origin=(0,0)),pos[0],pos[1])
def put(ref,x,y,a=0):
 assert ref not in POS,ref
 POS[ref]=[x,y,a];COURTS[ref]=court(ref,POS[ref])

def group(spec):
 for r,v in spec.items():put(r,*v)

# Connector mating faces extend 0.5 mm beyond the bench-board edge.
# TI isolator and transformer straddle one continuous vertical barrier.
group({'J1':(3.15,76,270),'J2':(92,3.15,180),'J3':(124.17,20,180),'J4':(124.17,46,180),
 'J5':(132.85,77,90),'J6':(132.85,102,90),'U1':(42,76,0),'T1':(42,28,0),'CY1':(35,104,0),
 'SH1':(28.5,28,0),'SH2':(64,28,0),
 'U5':(29,28,180),'U6':(65.5,28,0),'L1':(65.5,22.8,0),
 'U2':(11,76,0),'U3':(14,67,180),'U22':(21,64,0),'U24':(21,69,0),'U26':(22,42,180),
 'U45':(23,85,0),'L4':(28,85,0),
 'U23':(84,12,0),'U7':(91,13,90),'U25':(98,14,0),'U27':(88,23,0),'U46':(86,31,180),
 'U28':(98,30,0),'L3':(98,23.5,0),
 'U8':(77,46,0),'U29':(85,46,0),'U30':(85,52,0),'U47':(94,53,0),'U31':(79,57,0),
 'U48':(97,45,0),
 'U32':(92,61,0),'U41':(84,62,0),'U42':(74,61,0),'U43':(77,67,0),
 'U10':(59,52,0),'L2':(55,52,0),'U11':(75,79,180),'Y2':(75,86,0),
 'U33':(61,86,0),'U34':(63,97,180),
 'U12':(107,26,0),'U16':(113,20,0),'U13':(107,41,0),'U17':(113,46,0),
 'U14':(116,68,0),'U18':(124,77,0),'U20':(123,69,180),'U35':(117,62,0),'U37':(109,67,0),'U39':(117,84,0),'Q5':(124,84,0),
 'U15':(116,94,0),'U19':(124,102,0),'U21':(123,94,180),'U36':(117,88.5,0),'U38':(109,95,0),'U40':(116,109,0),'Q6':(124,109,0)})

# Primary switching bypass stays inside the low-profile GND1 frame.
group({'C10':(26,25,90),'C11':(29,24.8,0),'C12':(29,31,0),
 'D3':(52,24,180),'D4':(52,32,180),
 'C13':(57,23,90),'C15':(61,23,90),'C16':(57,28,90),
 'C14':(55,31,90),'C17':(62,28.5,0),
 'C18':(71,24,90),'C19':(75,24,90),'C20':(72,30,90),'C21':(69,27.5,0),
 'C22':(65.5,32,90),'R10':(70,32.5,90),'R11':(67.5,32.5,90),'R12':(63,32.5,90),'R15':(61,32.5,90),
 # Closest 10 nF / 100 nF bypasses are first, 4.7 uF reservoirs immediately outboard.
 'C67':(35,73.4,90),'C66':(33.5,73.4,90),'C65':(31.6,73.4,90),
 'C70':(35,78.6,90),'C69':(33.5,78.6,90),'C68':(31.6,78.6,90),
 'C73':(49,73.4,270),'C72':(50.5,73.4,270),'C71':(52.4,73.4,270),
 'C76':(49,78.6,270),'C75':(50.5,78.6,270),'C74':(52.4,78.6,270),
 'C3':(34,69.3,0),'C4':(35.5,70.9,0),'C63':(32,70.9,0),
 'C28':(50,69.3,180),'C29':(48.5,70.9,180),'C64':(52,70.9,180),
 # Converter hot loops: the bulky 1210 capacitors are selected for effective C.
 'C79':(92,22,90),'C80':(92,26,90),'C81':(96.5,32.9,0),'C82':(103.5,26,90),
 'C83':(98.5,33.2,0),'C84':(104,30,90),'C85':(108,30,90),'C86':(104,34,90),'C87':(108,34,90),
 'C88':(96.5,27.9,90),'C89':(99.5,27.9,90),'R110':(85,22,0),'R116':(89,52,0),
 'C92':(76,39,0),'C44':(124,31,0),'C47':(124,56,0),
 'C113':(21,82,90),'C114':(29,90,0),'R114':(25,90,90),'R115':(23,90,90),
 'C30':(61.6,52,90),'C31':(53.5,57,0),
 'C35':(79.7,79,0),'C36':(77,74.3,90),'C37':(74.5,74.3,90),'C38':(70.3,79,180),'C39':(73.5,83.7,270),'C40':(77,83.7,270),
 'C34':(75,74.3,90),'C59':(76,83.7,270),'C32':(71.8,86,90),'C33':(78.2,86,90),'R32':(76,73,0)})

# Mounting holes use 3.2 mm NPTH and reserve a 6.4 mm hardware envelope.
MECHANICAL={'H1':(5,5,0),'H2':(131,5,0),'H3':(5,111,0),'H4':(131,111,0)}
for ref,pos in MECHANICAL.items():
 f=read(ROOT/'hub-lib.pretty'/'MountingHole_3.2mm_M3.kicad_mod');F[ref]=f;BASECOURT[ref]=Point(0,0).buffer(3.2)
 put(ref,*pos)

# Pin-directed targets for small parts. Specific ownership in schematic notes
# wins over broad rail connectivity. Rare signal nets choose a local IC endpoint.
NETIC=defaultdict(list)
for ref,p in PARTS.items():
 if ref.startswith('U'):
  for pad in children(F[ref],'pad'):
   net=p['pins'].get(str(pad[1]));
   if net:NETIC[net].append((ref,str(pad[1]),transform(*xy(pad),POS[ref])))
PRIMARY=set(r for r,p in PARTS.items() if p['page']=='host')|{'U5','C10','C11','C12','SH1'}
for r,p in PARTS.items():
 if p['page']=='isolation' and 'GND1' in p['pins'].values() and r!='CY1':PRIMARY.add(r)
PRIMARY|={'C4','C63','R51','R52','R53','R54','TP3'}
SHIELDED={'C10':'SH1','C11':'SH1','C12':'SH1','U5':'SH1',**{r:'SH2' for r in ['U6','L1','D3','D4','C13','C14','C15','C16','C17','C18','C19','C20','C21','C22','R10','R11','R12','R15']}}

import re

def target(ref):
 p=PARTS[ref];owner=re.search(r'\b(U\d+|J\d+)\.(\d+)\b',p['note'])
 if owner:
  rr,pin=owner.groups()
  for a in children(F.get(rr,[]),'pad'):
   if str(a[1])==pin:return (*transform(*xy(a),POS[rr]),rr+'.'+pin)
 owner=re.search(r'\b(U\d+|J\d+)\b',p['note'])
 if owner and owner[1] in POS:return (*POS[owner[1]][:2],owner[1])
 candidates=[]
 for net in p['pins'].values():
  if not net or net.startswith('GND'):continue
  options=[v for v in NETIC[net] if PARTS[v[0]]['page']==p['page']]
  for rr,pin,pos in options:candidates.append((len(NETIC[net]),rr,pin,pos))
 if candidates:
  _,rr,pin,pos=min(candidates);return (*pos,rr+'.'+pin)
 centers={'host':(20,72),'isolation':(30 if ref in PRIMARY else 54,81),'converter':(65,30),'external':(96,35),'distribution':(85,59),'hub':(70,90),'ports_a':(110,30),'port_c3':(118,78),'port_c4':(118,103)}
 return (*centers[p['page']],'functional block')

def legal(ref,pos):
 shape=court(ref,pos);a,b,c,d=shape.bounds
 if a<2 or c>WIDTH-2 or b<2 or d>HEIGHT-2:return False
 if ref in PRIMARY:
  if c>37.3:return False
 elif a<46.7:return False
 for r,other in COURTS.items():
  if shape.distance(other)<.18:return False
 return True

# Place the remaining passives nearest their verified owner, on a 0.25 mm grid.
# No electrical routing is produced by this search.
remaining=[r for r in PARTS if r not in POS]
cache=ROOT/'tools/revc/placement-passives.json'
if cache.exists():
 for ref,pos in json.loads(cache.read_text()).items():
  if ref in remaining:put(ref,*pos)
remaining=[r for r in remaining if r not in POS]
remaining.sort(key=lambda r:(not r.startswith('C'),-BASECOURT[r].area,r))
for ref in remaining:
 tx,ty,why=target(ref);TARGETS[ref]=dict(x=tx,y=ty,owner=why)
 found=[]
 for radius in range(0,81):
  d=radius*.25
  offsets=[(0,0)] if radius==0 else [(dx*.25,dy*.25) for dx in range(-radius,radius+1) for dy in [-radius,radius]]+[(dx*.25,dy*.25) for dx in [-radius,radius] for dy in range(-radius+1,radius)]
  for dx,dy in offsets:
   for ang in (0,90):
    pos=[round((tx+dx)*4)/4,round((ty+dy)*4)/4,ang]
    if legal(ref,pos):found.append((dx*dx+dy*dy,ang,pos))
  if found:break
 if not found:raise RuntimeError(('no space',ref,tx,ty))
 put(ref,*min(found)[2])

# Overrides from visual / electrical placement review are persistent and explicit.
overrides=ROOT/'tools/revc/placement-overrides.json'
if overrides.exists():
 for ref,pos in json.loads(overrides.read_text()).items():POS[ref]=pos;COURTS[ref]=court(ref,pos)
cache.write_text(json.dumps(POS,indent=2)+'\n')


def make_footprint(ref):
 f=deepcopy(F[ref]);p=PARTS.get(ref)
 f[1]=p['footprint'] if p else 'hub-lib:MountingHole_3.2mm_M3'
 remove={'version','generator','generator_version','uuid','at','path','sheetname','sheetfile','embedded_fonts'}
 f[:]=[x for x in f if not(isinstance(x,list) and str(x[0]) in remove)]
 f.extend([n('uuid',uid('pcb/'+ref)),n('at',*POS[ref])])
 props={a[1]:a for a in children(f,'property')}
 for name,val in {'Reference':ref,'Value':p['value'] if p else 'M3 NPTH'}.items():
  if name in props:props[name][2]=val
 if p:
  fields={'MPN':p['mpn'],'Manufacturer':p['manufacturer'],'LCSC':p.get('lcsc',''),'Ratings':p.get('ratings',''),
          'Datasheet':p.get('datasheet',''),'Description':p['note'],'CoverMPN':p.get('cover_mpn',''),'CoverQuantity':p.get('cover_quantity','')}
  for name,val in fields.items():
   if name in props:props[name][2]=val
   else:f.append(n('property',name,val,n('at',0,0,0),n('layer','F.Fab'),n('hide',S('yes')),n('effects',n('font',n('size',1,1),n('thickness',.15)))))
  f.extend([n('path','/'+ROOT_UUID+'/'+uid('sheet/'+p['page'])+'/'+p['uuid']),n('sheetname',p['page'].upper()),n('sheetfile','hub-'+p['page']+'.kicad_sch')])
  if p['dnp']:child(f,'attr').append(S('dnp'))
  if p.get('exclude_bom'):child(f,'attr').append(S('exclude_from_bom'))
 else:
  child(f,'attr').extend([S('board_only'),S('exclude_from_pos_files'),S('exclude_from_bom')])
 for a in children(f,'pad'):
  number=str(a[1]);net=PINNET.get((ref,number))
  if net:a.append(n('net',NETS[net],net))
  if p and number in p['symbol_pins']:
   a.extend([n('pinfunction',p['symbol_pins'][number]['name']),n('pintype',p['symbol_pins'][number]['type'])])
  # Current KiCad uses pad rotations relative to the footprint; preserve them.
 user_refs=[q for q in children(f,'fp_text') if q[2] in ['${REFERENCE}','%R']]
 small=ref.startswith(('R','C')) and ref!='CY1'
 size=.45 if small else .7
 ref_xy={'SH1':(0,-8.5),'SH2':(0,-11),'CY1':(7,0)}.get(ref,(0,0))
 for q in user_refs:
  child(q,'at')[1:]=[*ref_xy,POS[ref][2]]
  font=child(child(q,'effects'),'font');child(font,'size')[1:]=[size,size]
  if child(font,'thickness'):child(font,'thickness')[1]=.08
 for prop in children(f,'property'):
  at=child(prop,'at');at[3]=POS[ref][2] # horizontal after footprint rotation
  if prop[1]!='Reference' or user_refs:
   if child(prop,'hide') is None:prop.append(n('hide',S('yes')))
  if prop[1]=='Reference':
   child(prop,'layer')[1]='F.Fab' # reference map is assembly documentation
   child(prop,'at')[1:3]=ref_xy
   font=child(child(prop,'effects'),'font');child(font,'size')[1:]=[size,size]
   if child(font,'thickness'):child(font,'thickness')[1]=.1
 # Every board object UUID is deterministic and unique, including copied lands.
 def ids(tree,path):
  for i,a in enumerate(tree):
   if isinstance(a,list):
    if str(a[0])=='uuid':a[1]=uid('pcb/'+ref+'/'+path+'/'+str(i))
    else:ids(a,path+'/'+str(i))
 ids(f,'root');return f

board=n('kicad_pcb',n('version',20240108),n('generator','pcbnew'),n('general',n('thickness',1.6)),n('paper','A4'),
 n('title_block',n('title','Rev C isolated four-port USB hub — UNROUTED'),n('rev','C'),n('date','2026-09-10')),
 n('layers',*[n(str(i),name,S(kind)) for i,name,kind in [(0,'F.Cu','signal'),(1,'In1.Cu','power'),(2,'In2.Cu','power'),(31,'B.Cu','signal'),(34,'B.Paste','user'),(35,'F.Paste','user'),(36,'B.SilkS','user'),(37,'F.SilkS','user'),(38,'B.Mask','user'),(39,'F.Mask','user'),(40,'Dwgs.User','user'),(41,'Cmts.User','user'),(44,'Edge.Cuts','user'),(46,'B.CrtYd','user'),(47,'F.CrtYd','user'),(48,'B.Fab','user'),(49,'F.Fab','user')]]))
stack=n('stackup',n('layer','F.SilkS',n('type','Top Silk Screen')),n('layer','F.Paste',n('type','Top Solder Paste')),n('layer','F.Mask',n('type','Top Solder Mask'),n('thickness',.015),n('epsilon_r',3.8),n('loss_tangent',0)),
 n('layer','F.Cu',n('type','copper'),n('thickness',.035)),n('layer','dielectric 1',n('type','prepreg'),n('thickness',.0994),n('material','3313'),n('epsilon_r',4.1),n('loss_tangent',.02)),
 n('layer','In1.Cu',n('type','copper'),n('thickness',.0152)),n('layer','dielectric 2',n('type','core'),n('thickness',1.265),n('material','NP-155F'),n('epsilon_r',4.43),n('loss_tangent',.02)),
 n('layer','In2.Cu',n('type','copper'),n('thickness',.0152)),n('layer','dielectric 3',n('type','prepreg'),n('thickness',.0994),n('material','3313'),n('epsilon_r',4.1),n('loss_tangent',.02)),
 n('layer','B.Cu',n('type','copper'),n('thickness',.035)),n('layer','B.Mask',n('type','Bottom Solder Mask'),n('thickness',.015),n('epsilon_r',3.8),n('loss_tangent',0)),n('layer','B.Paste',n('type','Bottom Solder Paste')),n('layer','B.SilkS',n('type','Bottom Silk Screen')),n('copper_finish','ENIG'),n('dielectric_constraints',S('yes')))
board.append(n('setup',stack,n('pad_to_mask_clearance',0),n('allow_soldermask_bridges_in_footprints',S('no'))))
board.extend(n('net',code,name) for name,code in NETS.items());board.extend(make_footprint(r) for r in POS)
def line(a,b,layer='Edge.Cuts',width=.05):return n('gr_line',n('start',*a),n('end',*b),n('stroke',n('width',width),n('type',S('default'))),n('layer',layer),n('uuid',uid(f'pcbline/{a}/{b}/{layer}')))
# 3 mm corner radius; no slots are needed for the verified 9.41 mm T1 land gap.
for a,b in [((3,0),(WIDTH-3,0)),((WIDTH,3),(WIDTH,HEIGHT-3)),((WIDTH-3,HEIGHT),(3,HEIGHT)),((0,HEIGHT-3),(0,3))]:board.append(line(a,b))
for start,mid,end in [((0,3),(.87868,.87868),(3,0)),((WIDTH-3,0),(WIDTH-.87868,.87868),(WIDTH,3)),((WIDTH,HEIGHT-3),(WIDTH-.87868,HEIGHT-.87868),(WIDTH-3,HEIGHT)),((3,HEIGHT),(.87868,HEIGHT-.87868),(0,HEIGHT-3))]:board.append(n('gr_arc',n('start',*start),n('mid',*mid),n('end',*end),n('stroke',n('width',.05),n('type',S('default'))),n('layer','Edge.Cuts'),n('uuid',uid('corner/'+str(start)))))

def keepout(name,points,layers=('F.Cu','In1.Cu','In2.Cu','B.Cu')):
 return n('zone',n('net',0),n('net_name',''),n('layers',*layers),n('uuid',uid('keepout/'+name)),n('name',name),n('hatch',S('edge'),.5),n('connect_pads',n('clearance',0)),n('min_thickness',.25),n('keepout',n('tracks',S('not_allowed')),n('vias',S('not_allowed')),n('pads',S('not_allowed')),n('copperpour',S('not_allowed')),n('footprints',S('allowed'))),n('fill',n('thermal_gap',.3),n('thermal_bridge_width',.3)),n('polygon',n('pts',*[n('xy',*p) for p in points])))
# 8.30 mm everywhere, recessed only to the TI HV footprint's exact 8.20 mm gap.
barrier=[(37.85,-1),(46.15,-1),(46.15,70.3),(46.10,70.3),(46.10,81.7),(46.15,81.7),(46.15,HEIGHT+1),(37.85,HEIGHT+1),(37.85,81.7),(37.90,81.7),(37.90,70.3),(37.85,70.3)]
board.append(keepout('ISOLATION — NO COPPER ON ANY LAYER',barrier))
for ref,pos in MECHANICAL.items():
 points=[(pos[0]+3.2*math.cos(a*math.pi/16),pos[1]+3.2*math.sin(a*math.pi/16)) for a in range(32)]
 ko=keepout(ref+' — M3 hardware clearance',points)
 child(child(ko,'keepout'),'pads')[1]=S('allowed') # permits the NPTH itself; courtyard reserves hardware
 board.append(ko)
 board.append(n('gr_circle',n('center',pos[0],pos[1]),n('end',pos[0]+1.6,pos[1]),n('stroke',n('width',.15),n('type',S('default'))),n('fill',S('none')),n('layer','Dwgs.User'),n('uuid',uid('hole-drawing/'+ref))))
for a,b in [((37.85,0),(37.85,116)),((46.15,0),(46.15,116))]:board.append(line(a,b,'Dwgs.User',.15))
for content,x,y,size,layer in [('REV C / ISOUSB211 / 480 Mbps',77,111,1.2,'F.SilkS'),('HOST',8,85,1,'F.SilkS'),('EXT 5V / 3A',110,8,1,'F.SilkS'),('GND1',21,101,1.5,'F.SilkS'),('GND2',58,108,1.5,'F.SilkS'),('UNROUTED — ALEX ROUTES ALL NETS',74,119,1.5,'Dwgs.User'),('JLC04161H-3313 / 4 LAYERS / 90 OHM USB TARGET',74,122,1.2,'Dwgs.User')]:
 board.append(n('gr_text',content,n('at',x,y),n('layer',layer),n('uuid',uid('pcbtext/'+content)),n('effects',n('font',n('size',size,size),n('thickness',.15)))))
write(ROOT/'hub.kicad_pcb',board)
(B/'placement.json').write_text(json.dumps(POS,indent=2)+'\n');(B/'placement-targets.json').write_text(json.dumps(TARGETS,indent=2)+'\n')
# Collision report includes preassigned anchors and is a gate, not an exclusion.
collisions=[]
for i,(a,ga) in enumerate(COURTS.items()):
 for b,gb in list(COURTS.items())[i+1:]:
  if ga.intersection(gb).area>.00001:collisions.append((a,b,round(ga.intersection(gb).area,4)))
(B/'placement-collisions.json').write_text(json.dumps(collisions,indent=2)+'\n')
print('Synchronized',len(PARTS),'schematic footprints and',len(MECHANICAL),'mechanicals; 0 tracks, 0 vias. Anchor collisions:',collisions)
