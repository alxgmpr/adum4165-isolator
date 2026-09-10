"""Capture the Rev C electrical source into the canonical hierarchical schematic.

This is a schematic-only generator. Physical pin tables are checked before any
file is written. Re-running overwrites generated schematic pages, not the PCB.
"""
from copy import deepcopy
from pathlib import Path
import json
import math
import uuid

from design import ROOT, PARTS
from library import build_library, fx, source_symbol, renamed, pin_table
from sexpr import S, node as n, children, child, value, write

ROOT_UUID='c86df239-2775-4bfb-906f-796343d9aaf9'
TITLE={
 'host':'Host USB-C input and current qualification',
 'isolation':'ISOUSB211 isolated 480 Mbps USB link',
 'converter':'Isolated host power and separate shield frames',
 'external':'Qualified external 5 V input and voltage regulation',
 'distribution':'Supply selection and protected port distribution',
 'hub':'USB2514B hub, 3.3 V supply, clock and configuration',
 'ports_a':'Downstream USB-A ports 1 and 2',
 'port_c3':'Downstream USB-C port 3',
 'port_c4':'Downstream USB-C port 4'
}


def uid(key): return str(uuid.uuid5(uuid.NAMESPACE_URL,'isolator-revc/'+key))


def wire(a,b):
    return n('wire',n('pts',n('xy',*a),n('xy',*b)),n('stroke',n('width',0),n('type',S('default'))),n('uuid',uid(f'wire/{a}/{b}')))


def label(net,x,y,angle=0):
    return n('global_label',net,n('shape',S('bidirectional')),n('at',x,y,angle),fx(1.27,justify='left' if angle==180 else 'right'),
             n('uuid',uid(f'label/{net}/{x}/{y}/{angle}')),
             n('property','Intersheetrefs','${INTERSHEET_REFS}',n('at',x,y,angle),fx(hide=True)))


def text(s,x,y,size=1.27):
    return n('text',s,n('at',x,y,0),fx(size,justify='left'),n('uuid',uid(f'text/{s}/{x}/{y}')))


def is_big(p):
    return (p['ref'][0] in ['U','J','T'] and not p['ref'].startswith('TP')) or p['ref'].startswith('SH')


def bounds(sym):
    points=[]
    for sub in children(sym,'symbol'):
        for shape in sub[2:]:
            if not isinstance(shape,list):continue
            for key in ['start','end','at']:
                z=child(shape,key)
                if z:points.append(z[1:3])
    return (min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points))


def component(p,x,y,path):
    sym=p['symbol'];pins=p['symbol_pins'];b=bounds(sym)
    obj=n('symbol',n('lib_id',p['local_lib']),n('at',x,y,0),n('unit',1),n('in_bom',S('no' if p.get('virtual') or p.get('exclude_bom') else 'yes')),n('on_board',S('no' if p.get('virtual') else 'yes')),
          n('dnp',S('yes' if p['dnp'] else 'no')),n('uuid',p['uuid']))
    big=is_big(p)
    if big:rx,ry=x,y-b[3]-12.7;vx,vy=x,y-b[3]-10.16
    else:rx,ry=x+3.81,y-1.27;vx,vy=x+3.81,y+1.27
    fields={'Reference':p['ref'],'Value':p['value'],'Footprint':p['footprint'],'Datasheet':p.get('datasheet',''),
            'Description':p['note'],'MPN':p['mpn'],'Manufacturer':p['manufacturer'],'LCSC':p.get('lcsc',''),'Ratings':p.get('ratings',''),
            'CoverMPN':p.get('cover_mpn',''),'CoverQuantity':p.get('cover_quantity','')}
    for key,val in fields.items():
        px,py=(rx,ry) if key=='Reference' else ((vx,vy) if key=='Value' else (x,y))
        obj.append(n('property',key,val,n('at',px,py,0),fx(1.27,hide=key not in ['Reference','Value'],justify=None if big else 'left')))
    for pin in pins:obj.append(n('pin',pin,n('uuid',uid(p['ref']+'/pin/'+pin))))
    obj.append(n('instances',n('project','hub',n('path',path,n('reference',p['ref']),n('unit',1)))))
    elems=[obj]
    buses={}
    used_wires=set()
    for number,pin in pins.items():
        net=p['pins'][number];px=x+pin['at'][0];py=y-pin['at'][1];ang=pin['at'][2]
        if net is None:
            elems.append(n('no_connect',n('at',px,py),n('uuid',uid(p['ref']+'/nc/'+number))))
            continue
        dx,dy={0:(-5.08,0),180:(5.08,0),90:(0,5.08),270:(0,-5.08)}[ang]
        end=(round(px+dx,6),round(py+dy,6))
        if ((px,py),end) not in used_wires:
            elems.append(wire((px,py),end));used_wires.add(((px,py),end))
        if big and ang in [90,270]:buses.setdefault((ang,net),[]).append(end)
        else:elems.append(label(net,*end,180 if ang==180 else 0))
    for (angle,net),ends in buses.items():
        ends=sorted(set(ends))
        for a,b in zip(ends,ends[1:]):elems.append(wire(a,b))
        for end in ends[1:-1]:elems.append(n('junction',n('at',*end),n('diameter',0),n('color',0,0,0,0),n('uuid',uid(f'junc/{p["ref"]}/{net}/{end}'))))
        elems.append(label(net,*ends[0]))
    return elems


def make_page(page,parts,number):
    page_id=uid('sheet/'+page);path='/'+ROOT_UUID+'/'+page_id
    origins={'host':['VBUS_HOST','GND1','U1_1V8_HOST'],'converter':['DCDC_RAW','GND2'],'external':['EXT_5V','EXT_SW_5V'],'hub':['ISO_3V3']}
    for j,net in enumerate(origins.get(page,[])):
        sy=renamed(source_symbol('power:PWR_FLAG'),'power_PWR_FLAG')
        parts.append(dict(ref=f'#FLG{number:02d}{j:02d}',value='PWR_FLAG',pins={'1':net},uuid=uid('flag/'+net),
                          local_lib='hub-lib:power_PWR_FLAG',symbol=sy,symbol_pins=pin_table(sy),dnp=False,virtual=True,
                          footprint='',note='Declared power origin: '+net,mpn='',manufacturer=''))
    syms={p['local_lib']:p['symbol'] for p in parts}
    libs=[]
    for name,s in syms.items():
        z=deepcopy(s);z[1]=name;libs.append(z)
    sch=n('kicad_sch',n('version',20250114),n('generator','eeschema'),n('uuid',uid('document/'+page)),n('paper','A3'),
          n('title_block',n('title',TITLE[page]),n('rev','C — design verification in progress'),n('date','2026-09-10')),
          n('lib_symbols',*libs))
    sch.append(text(TITLE[page],15.24,17.78,2.032))
    sch.append(text('Rev C | all routing reserved for Alex | electrical draft under review',15.24,24.13))
    big=[p for p in parts if is_big(p)]
    small=[p for p in parts if p not in big]
    x=10.16;y=31.75;rowh=0
    positions={}
    for p in big:
        b=bounds(p['symbol']);w=b[2]-b[0]+38.1;h=b[3]-b[1]+30.48
        if x+w>406.4:
            x=10.16;y+=rowh+7.62;rowh=0
        cx=round(x-b[0]+19.05,6);cy=round(y+b[3]+15.24,6)
        sch.extend(component(p,cx,cy,path));positions[p['ref']]=[cx,cy]
        x+=w+5.08;rowh=max(rowh,h)
    y+=rowh+17.78
    for i,p in enumerate(small):
        cx=round(35.56+(i%9)*43.18,6);cy=round(y+(i//9)*25.4,6)
        sch.extend(component(p,cx,cy,path));positions[p['ref']]=[cx,cy]
    sch.append(n('embedded_fonts',S('no')))
    write(ROOT/f'hub-{page}.kicad_sch',sch)
    return page_id,positions


def main():
    syms=build_library(PARTS)
    syms['power_PWR_FLAG']=renamed(source_symbol('power:PWR_FLAG'),'power_PWR_FLAG')
    write(ROOT/'hub-lib.kicad_sym',n('kicad_symbol_lib',n('version',20250114),n('generator','kicad_symbol_editor'),*syms.values()))
    # Preserve the original symbol/footprint tables and register the new local library.
    from sexpr import read
    for filename,kind in [('sym-lib-table','symbol'),('fp-lib-table','footprint')]:
        table=read(ROOT/filename)
        if not any(value(x,'name')=='hub-lib' for x in children(table,'lib')):
            uri='${KIPRJMOD}/hub-lib.kicad_sym' if kind=='symbol' else '${KIPRJMOD}/hub-lib.pretty'
            table.append(n('lib',n('name','hub-lib'),n('type','KiCad'),n('uri',uri),n('options',''),n('descr','Rev C project-local verified library')))
            write(ROOT/filename,table)
    root=n('kicad_sch',n('version',20250114),n('generator','eeschema'),n('uuid',ROOT_UUID),n('paper','A3'),
           n('title_block',n('title','Rev C — Isolated four-port USB 2.0 hub'),n('rev','C — verification in progress'),n('date','2026-09-10')),
           n('lib_symbols'))
    root.append(text('ISOLATED FOUR-PORT USB 2.0 HUB',15.24,17.78,3.81))
    root.append(text('ISOUSB211DPR | USB2514B | 2 x USB-A + 2 x USB-C | 480 Mbps',15.24,27.94,2.032))
    root.append(text('Design verification in progress. PCB placement and all routing are unfinished.',15.24,38.1))
    placements={}
    for i,(page,title) in enumerate(TITLE.items()):
        subset=[p for p in PARTS.values() if p['page']==page]
        sheet_id,pos=make_page(page,subset,i+2);placements.update(pos)
        x=20.32+(i%3)*129.54;y=55.88+(i//3)*63.5
        root.append(n('sheet',n('at',x,y),n('size',111.76,40.64),n('stroke',n('width',0.254),n('type',S('default'))),
                      n('fill',n('color',0,0,0,0)),n('uuid',sheet_id),
                      n('property','Sheetname',title,n('at',x,y-2.54,0),fx(justify='left')),
                      n('property','Sheetfile',f'hub-{page}.kicad_sch',n('at',x,y+43.18,0),fx(justify='left')),
                      n('instances',n('project','hub',n('path','/'+ROOT_UUID,n('page',str(i+2)))))))
    root.append(n('sheet_instances',n('path','/',n('page','1'))));root.append(n('embedded_fonts',S('no')))
    write(ROOT/'hub.kicad_sch',root)
    (ROOT/'build/revc/schematic-positions.json').write_text(json.dumps(placements,indent=2)+'\n')
    print(f'Captured {len(PARTS)} physical parts in {len(TITLE)} functional sheets')


if __name__=='__main__':main()
