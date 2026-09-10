"""Review-only exports: no Gerbers, drill, assembly-position or fabrication files."""
from pathlib import Path
import subprocess
import csv
import json
from collections import defaultdict
from sexpr import read, children, value

ROOT=Path(__file__).resolve().parents[2]
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
OUT=ROOT/'build/revc'

def call(*args):subprocess.run([CLI,*map(str,args)],cwd=ROOT,check=True)

def bom():
    # These are captured schematic fields, not parallel BOM-only overrides.
    fields=['Reference','Value','MPN','Manufacturer','Footprint','LCSC','Ratings','Datasheet','DNP','QUANTITY','CoverMPN','CoverQuantity']
    call('sch','export','bom','--fields',','.join(fields),'--labels',','.join(fields),
        '--group-by','MPN,Footprint,DNP,Ratings','--sort-field','Reference','-o',ROOT/'docs/revc/BOM.csv','hub.kicad_sch')
    covers=[]
    for page in ROOT.glob('hub-*.kicad_sch'):
        for symbol in children(read(page),'symbol'):
            p={a[1]:a[2] for a in children(symbol,'property')}
            if p.get('CoverMPN'):covers.append([p['Reference'],p['CoverMPN'],p['Manufacturer'],p['CoverQuantity'],p['Datasheet'],'Removable frame cover; order separately'])
    with (ROOT/'docs/revc/BOM-covers.csv').open('w') as f:
        writer=csv.writer(f,lineterminator="\n");writer.writerow(['Parent reference','MPN','Manufacturer','Quantity','Source','Assembly note']);writer.writerows(covers)

def main():
    OUT.mkdir(exist_ok=True)
    call('sch','erc','hub.kicad_sch','-o',OUT/'erc-latest.rpt','--severity-all','--exit-code-violations')
    call('sch','export','netlist','--format','kicadxml','-o',OUT/'hub.xml','hub.kicad_sch')
    bom()

if __name__=='__main__':main()
