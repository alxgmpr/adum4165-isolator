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
 'bus_start':'Bus startup and aggregate fault reporting',
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


def main():
    from schematic_layout import make_page as layout_page
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
    root=n('kicad_sch',n('version',20250114),n('generator','eeschema'),n('uuid',ROOT_UUID),n('paper','A2'),
           n('title_block',n('title','Rev C — Isolated four-port USB 2.0 hub'),n('rev','C'),n('date','2026-09-10')),
           n('lib_symbols'))
    root.append(text('ISOLATED FOUR-PORT USB 2.0 HUB',15.24,17.78,3.81))
    root.append(text('ISOUSB211DPR | USB2514B | 2 x USB-A + 2 x USB-C | 480 Mbps',15.24,27.94,2.032))
    root.append(text('Schematic and placed PCB. UNROUTED: Alex routes all nets. Hardware validation pending.',15.24,38.1))
    placements={}
    for i,(page,title) in enumerate(TITLE.items()):
        subset=[p for p in PARTS.values() if p['page']==page]
        sheet_id,pos,powerlibs=layout_page(page,subset,i+2);placements.update(pos);syms.update(powerlibs)
        x=20.32+(i%4)*129.54;y=55.88+(i//4)*63.5
        root.append(n('sheet',n('at',x,y),n('size',111.76,40.64),n('stroke',n('width',0.254),n('type',S('default'))),
                      n('fill',n('color',0,0,0,0)),n('uuid',sheet_id),
                      n('property','Sheetname',page.replace('_',' ').upper(),n('at',x,y-2.54,0),fx(justify='left')),
                      n('property','Sheetfile',f'hub-{page}.kicad_sch',n('at',x,y+43.18,0),fx(justify='left')),
                      n('instances',n('project','hub',n('path','/'+ROOT_UUID,n('page',str(i+2)))))))
        import textwrap
        root.append(text('\n'.join(textwrap.wrap(title,37)),x+5.08,y+12.7,1.524))
    root.append(text('DATA PATH',20.32,261.62,2.032))
    root.append(text('J1 host -> ISOUSB211 -> USB2514B -> J3/J4 USB-A + J5/J6 USB-C',20.32,271.78,1.524))
    root.append(text('POWER MODES',20.32,292.10,2.032))
    root.append(text('Host must advertise at least 1.5 A: 300 mA shared downstream design budget.\nExternal J2 must advertise 3 A: 2 A total / 500 mA per port, subject to the power-report conditions.\nA default-current host requires qualified external power. Source changes cause re-enumeration.',20.32,304.80,1.524))
    root.append(text('ROUTING HANDOFF',20.32,337.82,2.032))
    root.append(text('291 physical components placed; 4-layer bench board. No tracks or vias.\nSeparate GND1 / GND2 shield frames. TI HV land gap: 8.20 mm nominal; other barrier rules: 8.30 mm.\nStart with docs/revc/README.md for power limits, routing priorities, EEPROM and pending hardware tests.',20.32,350.52,1.524))
    root.append(n('sheet_instances',n('path','/',n('page','1'))));root.append(n('embedded_fonts',S('no')))
    write(ROOT/'hub.kicad_sch',root)
    write(ROOT/'hub-lib.kicad_sym',n('kicad_symbol_lib',n('version',20250114),n('generator','kicad_symbol_editor'),*syms.values()))
    (ROOT/'build/revc/schematic-positions.json').write_text(json.dumps(placements,indent=2)+'\n')
    print(f'Captured {len(PARTS)} physical parts in {len(TITLE)} functional sheets')


if __name__=='__main__':main()
