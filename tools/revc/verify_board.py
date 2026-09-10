"""Read-only final board inventory, net, domain and mechanical checks."""
from pathlib import Path
from collections import Counter,defaultdict
from itertools import combinations
import json,math,csv,xml.etree.ElementTree as ET
from shapely.geometry import box,Point,Polygon
from shapely import affinity
from design import ROOT,PARTS
from sexpr import read,children,child,value
board=read(ROOT/'hub.kicad_pcb');xml=ET.parse(ROOT/'build/revc/hub.xml').getroot()
netlist={(q.attrib['ref'],q.attrib['pin']):a.attrib['name'] for a in xml.find('nets') for q in a.findall('node')}
domains=json.loads((ROOT/'docs/revc/reports/net-domains.json').read_text())
footprints={};errors=[];padrows=[];copper={'Primary':[],'Secondary':[]};bypass=[]
for f in children(board,'footprint'):
 props={p[1]:p[2] for p in children(f,'property')};ref=props['Reference']
 assert ref not in footprints,ref
 footprints[ref]=f;pos=child(f,'at')[1:];rot=pos[2] if len(pos)>2 else 0
 p=PARTS.get(ref)
 if p:
  for key,expected in [('Value',p['value']),('MPN',p['mpn']),('Manufacturer',p['manufacturer']),('Datasheet',p['datasheet']),('LCSC',p.get('lcsc','')),('Ratings',p.get('ratings',''))]:
   if props.get(key)!=expected:errors.append([ref,key,props.get(key),expected])
  if f[1]!=p['footprint']:errors.append([ref,'footprint library mismatch'])
  if not value(f,'path','').endswith('/'+p['uuid']):errors.append([ref,'schematic UUID mismatch'])
  if bool('dnp' in map(str,(child(f,'attr') or ['attr'])[1:]))!=p['dnp']:errors.append([ref,'DNP mismatch'])
  if ref.startswith('C'):bypass.append([ref,p['value'],p['note'],*pos])
 for pad in children(f,'pad'):
  num=str(pad[1]);net=child(pad,'net');name=net[-1] if net else None
  expected=netlist.get((ref,num))
  if num and name!=expected:errors.append([ref,num,'pad net',name,'expected',expected])
  at=child(pad,'at')[1:];size=child(pad,'size')[1:];a=math.radians(rot)
  x=pos[0]+at[0]*math.cos(a)+at[1]*math.sin(a);y=pos[1]-at[0]*math.sin(a)+at[1]*math.cos(a)
  if num:padrows.append([ref,num,name or 'NC',round(x,6),round(y,6),*size,rot+(at[2] if len(at)>2 else 0)])
  if name in domains and str(pad[2])!='np_thru_hole' and any('Cu' in str(l) for l in child(pad,'layers')[1:]):
   if str(pad[3])=='circle':geom=Point(0,0).buffer(size[0]/2,resolution=32)
   else:geom=box(-size[0]/2,-size[1]/2,size[0]/2,size[1]/2)
   geom=affinity.translate(affinity.rotate(geom,-(rot+(at[2] if len(at)>2 else 0)),origin=(0,0)),x,y)
   copper[domains[name]].append((ref,num,name,geom))
missing=set(PARTS)-set(footprints);extra=set(footprints)-set(PARTS)
if missing:errors.append(['missing footprints',sorted(missing)])
if extra!={'H1','H2','H3','H4'}:errors.append(['unexpected board-only inventory',sorted(extra)])
for r,p in PARTS.items():
 pads={str(a[1]) for a in children(footprints[r],'pad')}
 if not {pin for pin,net in p['pins'].items() if net}<=pads:errors.append([r,'missing connected pad'])
for tag in ['segment','via','arc']:
 if children(board,tag):errors.append(['forbidden routed items',tag])
min_gap=(1e9,None);outside=(1e9,None)
for a in copper['Primary']:
 for b in copper['Secondary']:
  dist=a[3].distance(b[3]);pair=[a[:3],b[:3]]
  if dist<min_gap[0]:min_gap=(dist,pair)
  if not(a[0]=='U1' and b[0]=='U1') and dist<outside[0]:outside=(dist,pair)
if min_gap[0]<8.2-1e-6:errors.append(['TI barrier copper gap',min_gap])
if outside[0]<8.3-1e-6:errors.append(['other barrier copper gap',outside])
zones=children(board,'zone');barriers=[z for z in zones if value(z,'name','').startswith('ISOLATION')]
if len(barriers)!=1 or set(child(barriers[0],'layers')[1:])!={'F.Cu','In1.Cu','In2.Cu','B.Cu'}:errors.append(['isolation layer keepout incomplete'])
if any(children(z,'filled_polygon') for z in zones):errors.append(['unexpected filled copper'])
stack=child(child(board,'setup'),'stackup');copper_layers=[x[1] for x in children(stack,'layer') if value(x,'type')=='copper']
if copper_layers!=['F.Cu','In1.Cu','In2.Cu','B.Cu']:errors.append(['stackup',copper_layers])
# Full source transistor/transformer/barrier mapping is verified in the electrical
# audit; this check independently compares physical lands across the domains.
result={'schematic_components':len(PARTS),'pcb_footprints':len(footprints),'board_only_mechanicals':sorted(extra),
 'pad_rows_including_duplicate_lands':len(padrows),'tracks':len(children(board,'segment')),'vias':len(children(board,'via')),
 'unfilled_rule_areas':len(zones),'copper_layers':copper_layers,'minimum_cross_domain_copper_mm':min_gap,
 'minimum_cross_domain_copper_outside_U1_mm':outside,'errors':errors,
 'limits':'Conservative pad bounding geometry, inventory and net mapping only. KiCad DRC checks detailed shapes/courtyards/edges. This is not a routed-board or certified insulation test.'}
report=ROOT/'docs/revc/reports';(report/'pcb-inventory-and-isolation.json').write_text(json.dumps(result,indent=2)+'\n')
for name,header,rows in [('pcb-pad-net-map.csv',['Reference','Pad','Net','X mm','Y mm','Width mm','Height mm','Angle deg'],padrows),('bypass-placement.csv',['Reference','Value','Owning pin / purpose','X mm','Y mm','Angle deg'],bypass)]:
 with (report/name).open('w') as f:w=csv.writer(f,lineterminator="\n");w.writerow(header);w.writerows(rows)
print(json.dumps(result,indent=2));assert not errors,errors
