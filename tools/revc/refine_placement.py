"""Resolve the selected passive conflicts after moving reviewed anchor groups."""
import json,math
from board import POS,COURTS,court,legal,PARTS,ROOT
path=ROOT/'tools/revc/placement-overrides.json';out=json.loads(path.read_text())
for ref in ['D21','D6']:
 old=POS[ref];del COURTS[ref]
 found=[]
 for radius in range(81):
  offsets=[(0,0)] if radius==0 else [(dx*.25,dy*.25) for dx in range(-radius,radius+1) for dy in [-radius,radius]]+[(dx*.25,dy*.25) for dx in [-radius,radius] for dy in range(-radius+1,radius)]
  for dx,dy in offsets:
   pos=[old[0]+dx,old[1]+dy,old[2]]
   if legal(ref,pos):found.append((dx*dx+dy*dy,pos))
  if found:break
 assert found,ref
 pos=min(found)[1];POS[ref]=pos;COURTS[ref]=court(ref,pos);out[ref]=pos
 print(ref,old,'->',pos)
path.write_text(json.dumps(out,indent=2)+'\n')
