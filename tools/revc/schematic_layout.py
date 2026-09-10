"""Functional-panel schematic layout, with directly wired capacitor banks.

Coordinates are on the 50 mil grid. This changes presentation only; the exported
pin/net inventory is compared to design.py after every capture.
"""
from copy import deepcopy
import math
from collections import defaultdict
from sexpr import S,node as n,children,child,value,write
from library import source_symbol,renamed,pin_table,fx

PANELS={
 'host':[
  ('Host connector and ESD','J1 U2 C1 D1'),
  ('CC current qualification: 1.5 A or 3 A required','U22 U3 U24 C2 C61 C7 C8 R1 R2 R3 R4 TP1'),
  ('Isolated-converter input protection','U26 R5 R6 C62 TP2'),
  ('Efficient host-core supply: 1.8 V','U45 L4 C113 C114 R114 R115'),
  ('Qualified-host indicator','R9 D2 Q2')],
 'isolation':[
  ('Isolated USB link: no external clock','U1 TP3 TP4'),
  ('Host-side supply bypass: GND1 only','C3 C4 C63 C65 C66 C67 C68 C69 C70'),
  ('Isolated-side supply bypass: GND2 only','C28 C29 C64 C71 C72 C73 C74 C75 C76'),
  ('Equalization rework: fit only one strap per input','R51 R52 R53 R54 R55 R56 R57 R58'),
  ('Only intentional inter-ground capacitance','CY1')],
 'converter':[
  ('Primary push-pull driver and transformer','U5 T1 C10 C11 C12'),
  ('Secondary rectifier and reservoir','D3 D4 C13 C14 C15 C16 C17 TP5'),
  ('Isolated 5 V regulation','U6 L1 C18 C19 C20 C21 C22 R10 R11 R12 R15 TP6'),
  ('Two separate shield frames','SH1 SH2')],
 'external':[
  ('Power-only USB-C connector and 3.3 V bias','J2 U23 C23 C24 C77 D5'),
  ('External source must advertise 3 A','U7 U25 R16 R17 R18 C25 C26 R19 TP7'),
  ('Input inrush and port-shedding current monitor','U27 U46 R110 R111 R112 C110 C78 TP17'),
  ('Buck-boost power stage','U28 L3 C79 C80 C81 C82 C83 C84 C85 C86 C87 C88 C89 TP8'),
  ('Output setpoint and voltage-loop compensation','R20 R21 R22 R59 R60 C90 C91 R61')],
 'distribution':[
  ('External-priority power mux and core hold-up','U8 R23 R24 R25 R26 R27 R28 C27 C92 C93 TP9'),
  ('Bus / external downstream supply paths','U29 U30 U47 R62 R63 C115 R116 R117 C112 C96 C97 TP10'),
  ('Core undervoltage sheds downstream loads','U31 R64 R65 R66 C94 TP11'),
  ('Mutually exclusive supply enables','U32 U41 U42 U43 R83 C95 C107 C108 C109 D14 D15 D16 D17'),
 ],
 'bus_start':[
  ('Delayed bus fault report; immediate current limit','U48 R121 R122 C116 C117'),
  ('Aggregate fault fanout and external-source indicator','D20 D21 D22 D23 R29 D6 Q3')],
 'hub':[
  ('Shared 1 A rated 3.3 V buck','U10 L2 C30 C31 R67 TP12'),
  ('USB2514B core and per-port control','U11'),
  ('Hub clock, bias and internal-regulator filters','Y2 C32 C33 C34 C59 R32'),
  ('Hub local bypass: each 100 nF owns one supply pin','C35 C36 C37 C38 C39 C40 C41'),
  ('Host-present reset and VBUS sensing','U33 R33 R37 R31 C42 TP13 R30 D7 Q4'),
  ('EEPROM configuration and programming pads','U34 R34 R35 R36 C98 TP14 TP15 TP16')],
 'ports_a':[
  ('Port 1: USB-A, 500 mA with qualified external power','J3 U12 U16 R38 R47 R101 C43 C44 C45 D8'),
  ('Port 2: USB-A, 500 mA with qualified external power','J4 U13 U17 R39 R48 R102 C46 C47 C48 D9')],
}
for port in [3,4]:
    d=port-3
    PANELS['port_c'+str(port)]=[
      (f'Port {port}: USB-C, USB 2.0 and ESD',f'J{5+d} U{18+d} D{10 if d==0 else 13}'),
      ('Attach detection: DFP, default Rp, no VCONN',f'U{20+d} R{72+3*d} R{73+3*d} R{74+3*d} C{99+4*d}'),
      ('Attachment AND hub permission controls VBUS',f'U{35+d} U{37+d} U{14+d} R{40 if d==0 else 44} R{49+d} R{103+d} C{49 if d==0 else 55} C{50 if d==0 else 56} C{51 if d==0 else 57} C{100+4*d} C{101+4*d}'),
      ('Detach discharge, including total board power loss',f'U{39+d} Q{5+d} R{81+d} R{119+d} C{102+4*d}')]

POWER_NETS={'VBUS_HOST','HOST_3V3','HOST_CONVERTER_5V','U1_3V3_HOST','U1_1V8_HOST',
    'U1_1V8_ISO','ISO_3V3','ISO_5V','ISO_5V_PRE','DCDC_RAW','EXT_5V','EXT_3V3',
    'EXT_SENSED_5V','EXT_SW_5V','EXT_REG_5V','EXT_REG_VCC','PORT_SUPPLY','EXT_PORT_FEED',
    *['PORT'+str(i)+'_VBUS' for i in range(1,5)]}
CHAINS=[['R114','R115'],['R20','R21','R22'],['R23','R24'],['R25','R26'],['R64','R65']]

def snap(x):return round(round(x/1.27)*1.27,6)

class Layout:
    def __init__(self,parts,path,page):
        from capture import uid,wire,label,text,bounds,component,is_big
        self.uid=uid;self.wire=wire;self.label=label;self.text=text;self.bounds=bounds
        self.old_component=component;self.is_big=is_big;self.parts={p['ref']:p for p in parts}
        self.path=path;self.page=page;self.elems=[];self.powerlibs={};self.positions={};self.placed=set()
        self.power_count=0

    def power(self,net,x,y):
        key='power_'+net
        if key not in self.powerlibs:
            sy=renamed(source_symbol('power:GND1' if net.startswith('GND') else 'power:VCC'),key)
            for p in children(sy,'property'):
                if p[1]=='Value':p[2]=net
                if p[1]=='Description':p[2]='Global supply '+net
            self.powerlibs[key]=sy
        ident=self.uid(f'pwr/{self.page}/{net}/{x}/{y}')
        self.power_count+=1
        ref='#PWR'+str((list(PANELS).index(self.page)+2)*1000+self.power_count)
        dy=3.81 if net.startswith('GND') else -3.81
        self.elems.append(n('symbol',n('lib_id','hub-lib:'+key),n('at',x,y,0),n('unit',1),
            n('in_bom',S('no')),n('on_board',S('no')),n('dnp',S('no')),n('uuid',ident),
            n('property','Reference',ref,n('at',x,y,0),fx(hide=True)),
            n('property','Value',net,n('at',x,y+dy,0),fx(1.016)),
            n('pin','1',n('uuid',self.uid(ident+'/1'))),
            n('instances',n('project','hub',n('path',self.path,n('reference',ref),n('unit',1))))))

    def terminal(self,net,x,y,angle):
        if (angle==270 and net in POWER_NETS) or (angle in [90,270] and net.startswith('GND')):
            self.power(net,x,y)
        else:self.elems.append(self.label(net,x,y,180 if angle==180 else 0))

    def part(self,ref,x,y,connect=True):
        assert ref not in self.placed,ref
        self.placed.add(ref);p=self.parts[ref];self.positions[ref]=[x,y]
        obj=self.old_component(p,x,y,self.path)[0]
        rotation=90 if ref.startswith('L') or ref=='CY1' else 0
        child(obj,'at')[3]=rotation
        for f in children(obj,'property'):
            if f[1] not in ['Reference','Value']:continue
            if rotation:child(f,'at')[3]=rotation
            if ref.startswith('Q'):child(f,'at')[1]=x+10.16
            if ref.startswith(('D','L')) or ref=='CY1':
                child(f,'at')[1:3]=[x-2.54,y-(8.89 if f[1]=='Reference' else 6.35)]
            if ref.startswith('Y'):
                child(f,'at')[1:3]=[x-2.54,y-(8.89 if f[1]=='Reference' else 6.35)]
            if ref.startswith('TP') and f[1]=='Value' or ref.startswith('#FLG'):
                child(f,'effects').append(S('hide'))
        b=self.bounds(p['symbol'])
        if self.is_big(p):
            for f in children(obj,'property'):
                if f[1] in ['Reference','Value']:
                    child(f,'at')[1:3]=[x+b[0]-2.54,y-b[3]-(5.08 if f[1]=='Reference' else 2.54)]
                    top_nets={p['pins'][num] for num,pin in p['symbol_pins'].items() if pin['at'][2]==270 and p['pins'][num]}
                    if len(top_nets)>1:child(f,'at')[1]=x-25.4
                    eff=child(f,'effects');eff[:]=[a for a in eff if not(isinstance(a,list) and str(a[0])=='justify')]
                    eff.append(n('justify',S('right')))
        self.elems.append(obj)
        if not connect:return
        ends=defaultdict(set);seen=set()
        for num,pin in p['symbol_pins'].items():
            ax,ay,ang=pin['at'];theta=math.radians(rotation)
            px=snap(x+math.cos(theta)*ax-math.sin(theta)*ay)
            py=snap(y-math.sin(theta)*ax-math.cos(theta)*ay)
            ang=(ang+rotation)%360;net=p['pins'][num]
            if net is None:
                self.elems.append(n('no_connect',n('at',px,py),n('uuid',self.uid(ref+'/nc/'+num))));continue
            dx,dy={0:(-3.81,0),180:(3.81,0),90:(0,3.81),270:(0,-3.81)}[ang]
            end=(snap(px+dx),snap(py+dy));key=((px,py),end)
            if key not in seen:self.elems.append(self.wire((px,py),end));seen.add(key)
            if ang in [90,270] and self.is_big(p):ends[(net,ang)].add(end)
            else:self.terminal(net,*end,ang)
        top_groups=sum(ang==270 for net,ang in ends)
        top_index=0
        for (net,ang),pts in sorted(ends.items(),key=lambda item:(item[0][1],min(item[1])[0])):
            pts=sorted(pts)
            for a,b in zip(pts,pts[1:]):self.elems.append(self.wire(a,b))
            for pt in pts[1:-1]:self.junction(pt)
            endpoint=pts[0]
            if ang==270 and top_groups>1:
                spread=snap(x+(top_index-(top_groups-1)/2)*30.48)
                endpoint=(spread,pts[0][1]-3.81)
                self.elems.extend([self.wire(pts[0],(spread,pts[0][1])),self.wire((spread,pts[0][1]),endpoint)])
                top_index+=1
            self.terminal(net,*endpoint,ang)

    def junction(self,pt):self.elems.append(n('junction',n('at',*pt),n('diameter',0),n('color',0,0,0,0),n('uuid',self.uid(f'j/{self.page}/{pt}'))))

    def bank(self,refs,x,y):
        p=self.parts[refs[0]];top=p['pins']['1'];bottom=p['pins']['2']
        xs=[snap(x+i*12.7) for i in range(len(refs))]
        for ref,cx in zip(refs,xs):
            q=self.parts[ref];assert q['pins']==p['pins']
            self.part(ref,cx,y,False)
            for pin,by in [('1',y-7.62),('2',y+7.62)]:
                pos=q['symbol_pins'][pin]['at'];self.elems.append(self.wire((cx+pos[0],y-pos[1]),(cx,snap(by))))
        for yy,net,ang in [(snap(y-7.62),top,270),(snap(y+7.62),bottom,90)]:
            for a,b in zip(xs,xs[1:]):self.elems.append(self.wire((a,yy),(b,yy)))
            for xx in xs[1:-1]:self.junction((xx,yy))
            self.terminal(net,xs[0],yy,ang)

    def chain(self,refs,x,y):
        for i,ref in enumerate(refs):
            p=self.parts[ref];cy=snap(y+i*12.7);self.part(ref,x,cy,False)
            top=snap(cy-p['symbol_pins']['1']['at'][1]);bottom=snap(cy-p['symbol_pins']['2']['at'][1])
            if i==0:
                self.elems.append(self.wire((x,top),(x,top-3.81)));self.terminal(p['pins']['1'],x,top-3.81,270)
            if i==len(refs)-1:
                self.elems.append(self.wire((x,bottom),(x,bottom+3.81)));self.terminal(p['pins']['2'],x,bottom+3.81,90)
            else:
                q=self.parts[refs[i+1]];assert p['pins']['2']==q['pins']['1']
                nexttop=snap(cy+12.7-q['symbol_pins']['1']['at'][1]);mid=snap((bottom+nexttop)/2)
                self.elems.extend([self.wire((x,bottom),(x,mid)),self.wire((x,mid),(x,nexttop)),self.wire((x,mid),(x-5.08,mid)),self.label(p['pins']['2'],x-5.08,mid)])
                self.junction((x,mid))

    def panel(self,title,refs,x,y,width):
        refs=refs.split();parts=[self.parts[r] for r in refs]
        self.elems.append(self.text(title,x,y,1.778))
        big=[p for p in parts if self.is_big(p)]
        cy=y+17.78;cx=x;rowh=0
        for p in big:
            b=self.bounds(p['symbol']);left=max(22.86,max([len(v) for v in p['pins'].values() if v] or [0])*.75)
            w=snap(b[2]-b[0]+left+20.32);h=snap(b[3]-b[1]+20.32)
            if cx>x and cx+w>x+width:cx=x;cy+=rowh+7.62;rowh=0
            px=snap(cx-b[0]+left);py=snap(cy+b[3])
            self.part(p['ref'],px,py);cx+=w+5.08;rowh=max(rowh,h)
        cy+=rowh+5.08 if big else 2.54
        small=[p for p in parts if p not in big];groups=[];grouped=set()
        for refs_chain in CHAINS:
            if set(refs_chain)<=set(refs):groups.append(('chain',refs_chain));grouped.update(refs_chain)
        # Preserve independently owned isolator bypass groups, even on the same rail.
        caps=defaultdict(list)
        for p in small:
            if p['ref'].startswith('C') and p['ref']!='CY1' and p['ref'] not in grouped:
                owner=p['note'].split(';')[0] if p['page']=='isolation' else ''
                caps[(tuple(p['pins'].items()),owner)].append(p['ref']);grouped.add(p['ref'])
        for rr in caps.values():
            for k in range(0,len(rr),5):groups.append(('bank',rr[k:k+5]))
        groups.extend(('part',[p['ref']]) for p in small if p['ref'] not in grouped)
        cx=x;rowh=0
        for kind,rr in groups:
            p=self.parts[rr[0]]
            longest=max([len(v) for v in p['pins'].values() if v] or [0])
            left=snap(max(12.7,longest*.75));w=snap(left+15.24+(12.7*(len(rr)-1) if kind=='bank' else 0))
            if kind=='part' and p['ref'].startswith('D'):
                left=snap(max(20.32,longest*.9+6.35));w=snap(2*left+25.4)
            if kind=='part' and p['ref'].startswith('Q'):
                left=snap(max(25.4,longest*.8+10.16));w=snap(left+30.48)
            if kind=='part' and p['ref'].startswith(('Q','L')):w+=25.4
            h=snap(25.4+(12.7*(len(rr)-1) if kind=='chain' else 0))
            if p['ref'].startswith('Q'):h=35.56
            if cx>x and cx+w>x+width:cx=x;cy+=rowh+3.81;rowh=0
            px=snap(cx+left);py=snap(cy+10.16)
            getattr(self,kind)(rr if kind!='part' else rr[0],px,py)
            cx+=w+5.08;rowh=max(rowh,h)
        return snap(cy+rowh+5.08)

def make_page(page,parts,number):
    from capture import uid,ROOT_UUID,TITLE,ROOT,text
    page_id=uid('sheet/'+page);path='/'+ROOT_UUID+'/'+page_id
    lay=Layout(parts,path,page)
    # Functional panels use two columns on A2. Simpler downstream port pages use A3.
    paper='A3' if page in ['ports_a','bus_start'] else 'A2'
    width=185.42 if paper=='A3' else 269.24
    x1=20.32;x2=snap(x1+width+20.32);ys=[43.18,43.18]
    for i,(title,refs) in enumerate(PANELS[page]):
        col=0 if i==0 else min(range(2),key=lambda j:ys[j])
        ys[col]=lay.panel(title,refs,x1 if col==0 else x2,ys[col],width)+7.62
    expected=set(lay.parts);assert lay.placed==expected,(page,'unplaced',expected-lay.placed,'extra',lay.placed-expected)
    origins={'host':['VBUS_HOST','GND1','U1_1V8_HOST'],'converter':['DCDC_RAW','GND2'],
        'external':['EXT_5V','EXT_SW_5V','EXT_SENSED_5V'],'distribution':['EXT_PORT_FEED'],'hub':['ISO_3V3']}
    flags=[]
    if origins.get(page):
        col=min(range(2),key=lambda j:ys[j]);fy=ys[col]+10.16;fx0=x1 if col==0 else x2
        lay.elems.append(text('Declared power origins',fx0,ys[col],1.27))
        for i,net in enumerate(origins[page]):
            sy=renamed(source_symbol('power:PWR_FLAG'),'power_PWR_FLAG');ref=f'#FLG{number:02d}{i:02d}'
            p=dict(ref=ref,value='PWR_FLAG',pins={'1':net},uuid=uid('flag/'+net),local_lib='hub-lib:power_PWR_FLAG',symbol=sy,symbol_pins=pin_table(sy),dnp=False,virtual=True,footprint='',note='Declared power origin: '+net,mpn='',manufacturer='')
            lay.parts[ref]=p;lay.part(ref,snap(fx0+20.32+i*55.88),snap(fy));flags.append(p)
        ys[col]=fy+22.86
    syms={p['local_lib']:p['symbol'] for p in [*parts,*flags]}
    syms.update({'hub-lib:'+k:v for k,v in lay.powerlibs.items()})
    libs=[]
    for name,s in syms.items():z=deepcopy(s);z[1]=name;libs.append(z)
    sch=n('kicad_sch',n('version',20250114),n('generator','eeschema'),n('uuid',uid('document/'+page)),n('paper',paper),
        n('title_block',n('title',TITLE[page]),n('rev','C'),n('date','2026-09-10')),n('lib_symbols',*libs))
    sch.extend([text(TITLE[page],20.32,17.78,2.54),text('USB 2.0 / 480 Mbps  |  Rev C electrical design  |  Placed PCB; all routing by Alex; hardware tests pending',20.32,27.94)])
    sch.extend(lay.elems);sch.append(n('embedded_fonts',S('no')))
    limit=paper=='A3' and 260 or 389
    assert max(ys)<limit,(page,'off-frame panel bottom',ys,limit)
    write(ROOT/f'hub-{page}.kicad_sch',sch)
    print(page,paper,'content bottom',max(ys))
    return page_id,lay.positions,lay.powerlibs
