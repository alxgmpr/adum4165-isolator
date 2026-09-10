"""Reproducible symbol/pad inventory and a dimensional land review drawing."""
import csv
import json
from collections import defaultdict
import xml.etree.ElementTree as ET
from pathlib import Path
from design import ROOT, PARTS
from library import build_library
from sexpr import read, children, child, value

def main():
    build_library(PARTS)
    netlist=ET.parse(ROOT/'build/revc/hub.xml').getroot()
    actual={}
    for net in netlist.find('nets'):
        for q in net.findall('node'):actual[(q.attrib['ref'],q.attrib['pin'])]=net.attrib['name']
    rows=[];errors=[];no_purchase=[]
    for ref,p in PARTS.items():
        f=read(ROOT/'hub-lib.pretty'/(p['footprint'].split(':')[1]+'.kicad_mod'))
        pads=defaultdict(list)
        for a in children(f,'pad'):
            if a[1]!='':pads[str(a[1])].append(a)
        for pin,net in p['pins'].items():
            if net is not None and actual.get((ref,pin))!=net:errors.append([ref,pin,'net mismatch',net,actual.get((ref,pin))])
            if net is not None and pin not in pads:errors.append([ref,pin,'missing land'])
            for a in pads.get(pin,[]):
                rows.append([ref,p['mpn'],p['footprint'],pin,p['symbol_pins'].get(pin,{}).get('name','NC'),net or 'NC',
                    *child(a,'at')[1:3],*child(a,'size')[1:3],p.get('datasheet','')])
        if not p.get('exclude_bom') and not all(p.get(x) for x in ['mpn','manufacturer','footprint','datasheet']):errors.append([ref,'incomplete purchase fields'])
        if p.get('exclude_bom'):no_purchase.append(ref)
    out=ROOT/'docs/revc'
    with (out/'symbol-pad-net-audit.csv').open('w') as f:
        w=csv.writer(f,lineterminator="\n");w.writerow(['Reference','MPN','Footprint','Pin','Function','Expected net','Pad X mm','Pad Y mm','Pad width mm','Pad height mm','Manufacturer source']);w.writerows(rows)
    result={'physical_symbols':len(PARTS),'exported_components':len(netlist.findall('components/comp')),
        'pad_rows_including_duplicate_lands':len(rows),'connected_pin_net_differences':errors,
        'purchase_bom_exceptions':{'PCB test pads':no_purchase},
        'limits':'Inventory and exact exported pin/net check; manufacturer function/package review and PCB geometry checks are separate.'}
    (out/'symbol-pad-net-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    assert not errors,errors
    print(json.dumps(result,indent=2))
    render()

def render():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Ellipse
    selected=[('U1','TI DP28 HV lands'),('U11','Microchip M2 SQFN36'),('U8','TI RUX12'),('U28','TI RYQ21'),('L1','Coilcraft XFL4020'),('T1','Wurth transformer'),('CY1','Songtian Y1 capacitor'),('U3','TI RWB12'),('U6','TI RNM15')]
    fig,axes=plt.subplots(3,3,figsize=(15,14))
    for ax,(ref,title) in zip(axes.flat,selected):
        p=PARTS[ref];f=read(ROOT/'hub-lib.pretty'/(p['footprint'].split(':')[1]+'.kicad_mod'))
        extents=[]
        for a in f:
            if not isinstance(a,list):continue
            tag=str(a[0]);layer=value(a,'layer')
            if tag in ['fp_line','fp_rect'] and layer in ['F.Fab','F.CrtYd']:
                start=child(a,'start')[1:3];end=child(a,'end')[1:3];extents.extend([start,end])
                color='#596777' if layer=='F.Fab' else '#ab61ce'
                if tag=='fp_rect':ax.add_patch(Rectangle(start,end[0]-start[0],end[1]-start[1],fill=False,edgecolor=color,linewidth=.8))
                else:ax.plot([start[0],end[0]],[start[1],end[1]],color=color,lw=.8)
            if tag=='pad':
                layers=child(a,'layers')[1:]
                if not any('Cu' in l for l in layers):continue
                x,y=child(a,'at')[1:3];w,h=child(a,'size')[1:3];shape=str(a[3])
                extents.extend([(x-w/2,y-h/2),(x+w/2,y+h/2)])
                if shape=='circle':patch=Ellipse((x,y),w,h,facecolor='#db7860',edgecolor='#9c3424',lw=.5)
                else:patch=Rectangle((x-w/2,y-h/2),w,h,facecolor='#db7860',edgecolor='#9c3424',lw=.5)
                ax.add_patch(patch)
                if child(a,'drill'):
                    d=child(a,'drill');diam=float(d[1] if isinstance(d[1],(int,float)) else d[2]);ax.add_patch(Ellipse((x,y),diam,diam,facecolor='white',edgecolor='#333',lw=.5))
                ax.text(x,y,str(a[1]),fontsize=6,ha='center',va='center')
        xs,ys=zip(*extents);ax.set_xlim(min(xs)-1,max(xs)+1);ax.set_ylim(max(ys)+1,min(ys)-1);ax.set_aspect('equal');ax.set_title(ref+' · '+title,fontsize=11)
        ax.set_xlabel('mm');ax.set_ylabel('mm');ax.grid(alpha=.12)
    fig.suptitle('Rev C land-pattern review · copper and pin numbers · no tracks or vias',fontsize=16)
    fig.tight_layout(rect=[0,0,1,.97]);out=ROOT/'docs/revc/renders';out.mkdir(exist_ok=True)
    fig.savefig(out/'land-pattern-review.png',dpi=180);fig.savefig(out/'land-pattern-review.svg');plt.close(fig)
    svg=out/'land-pattern-review.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')

if __name__=='__main__':main()
