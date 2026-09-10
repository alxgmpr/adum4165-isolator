"""Resolve local/stock symbols and build a self-contained Rev C symbol library."""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import re
from sexpr import S, node as n, child, children, value, read, write
from design import ROOT

SYS = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols')


def fx(size=1.27, hide=False, justify=None):
    return n('effects',n('font',n('size',size,size)), *([S('hide')] if hide else []),
             *([n('justify',S(justify))] if justify else []))


@lru_cache(None)
def source_library(lib):
    path=ROOT/(lib+'.kicad_sym') if lib in ['isolator-lib','hub-isolator'] else SYS/(lib+'.kicad_sym')
    return {x[1]:x for x in children(read(path),'symbol')}


def source_symbol(identifier):
    lib,name=identifier.split(':')
    if name=='24LC02B': name='24LC02'
    originals=source_library(lib)
    sym=deepcopy(originals[name])
    if child(sym,'extends'):
        parent=source_symbol(lib+':'+value(sym,'extends'))
        props={x[1]:x for x in children(parent,'property')}
        props.update({x[1]:x for x in children(sym,'property')})
        geometry=children(parent,'symbol')
        for g in geometry:g[1]=g[1].replace(parent[1]+'_',name+'_',1)
        sym=[x for x in parent if not(isinstance(x,list) and str(x[0]) in ['property','symbol'])]
        sym[1]=name;sym.extend(props.values());sym.extend(geometry)
    return sym


def pin_table(sym):
    pins=[]
    for unit in children(sym,'symbol'):
        pins.extend(children(unit,'pin'))
    return {str(value(p,'number')):dict(name=value(p,'name'),type=str(p[1]),at=child(p,'at')[1:],length=value(p,'length'),node=p) for p in pins}


CUSTOM = {
 'INA300': [('IN+','input'),('IN-','input'),('LIMIT','input'),('ENABLE','input'),('ALERT_N','open_collector'),('LATCH','input'),('DELAY','input'),('GND','power_in'),('VS','power_in'),('HYS','input')],
 'Shield_Frame': [('FRAME','passive')],
 'TUSB320LAI': [('CC1','bidirectional'),('CC2','bidirectional'),('PORT','input'),('VBUS_DET','input'),('ADDR','input'),
               ('OUT3','open_collector'),('OUT1','open_collector'),('OUT2','open_collector'),('ID','open_collector'),
               ('GND','power_in'),('EN_N','input'),('VDD','power_in')],
 # VIN/VOUT are terminals of an analog pass FET, not regulated-voltage drivers.
 # Passive terminals accurately allow mutually exclusive switches to share a rail.
 # Power flags at the qualified input/output origins retain power-input checking.
 'TPS22975': [('VIN','passive'),('VIN','passive'),('ON','input'),('VBIAS','power_in'),('GND','power_in'),('CT','passive'),
              ('VOUT','passive'),('VOUT','passive'),('EP','power_in')],
 'TPS552892': [('EN_UVLO','input'),('MODE','input'),('PG','open_collector'),('CC','open_collector'),('DITH_SYNC','input'),
               ('FSW','passive'),('VIN','power_in'),('SW1','output'),('PGND','power_in'),('SW2','output'),('VOUT','power_out'),
               ('ISP','input'),('ISN','input'),('FB','input'),('COMP','output'),('CDC','output'),('AGND','power_in'),
               ('VCC','power_out'),('BOOT2','passive'),('BOOT1','passive'),('EXTVCC','input')],
 'TPS3808': [('RESET_N','open_collector'),('GND','power_in'),('MR_N','input'),('CT','passive'),('SENSE','input'),('VDD','power_in')]
}


def boxed(name, table):
    """Rearrange an IC graphically without changing pin numbers/names/types."""
    sym=n('symbol',name,n('pin_names',n('offset',1.016)),n('in_bom',S('yes')),n('on_board',S('yes')))
    for key,val in [('Reference','U'),('Value',name),('Footprint',''),('Datasheet',''),('Description',name)]:
        sym.append(n('property',key,val,n('at',0,0,0),fx(hide=key not in ['Reference','Value'])))
    left=[];right=[];top=[];bottom=[]
    for num,p in table.items():
        pname=p['name']; typ=p['type']
        if typ=='power_in' or pname in ['EP','GND','GND1','GND2','PGND','AGND']:
            (bottom if any(t in pname for t in ['GND','VSS','EP']) else top).append(num)
        elif typ=='power_out':right.append(num)
        elif name.startswith('USB2514'):
            (right if num in ['1','2','3','4','6','7','8','9','12','13','16','17','18','19','20','21'] else left).append(num)
        elif typ in ['output','open_collector','open_emitter']:right.append(num)
        else:left.append(num)
    width=max(35.56,5.08*(max(len(top),len(bottom))+1))
    h=max(25.4,5.08*(max(len(left),len(right))+3))
    sym.append(n('symbol',name+'_0_1',n('rectangle',n('start',-width/2,h/2),n('end',width/2,-h/2),
              n('stroke',n('width',0),n('type',S('default'))),n('fill',n('type',S('background'))))))
    unit=n('symbol',name+'_1_1')
    for side,nums in [('left',left),('right',right),('top',top),('bottom',bottom)]:
        for i,num in enumerate(nums):
            pos=(i-(len(nums)-1)/2)*5.08
            x,y,angle={'left':(-width/2-5.08,-pos,0),'right':(width/2+5.08,-pos,180),
                       'top':(pos,h/2+5.08,270),'bottom':(pos,-h/2-5.08,90)}[side]
            p=table[num]
            unit.append(n('pin',S(p['type']),S('line'),n('at',x,y,angle),n('length',5.08),
                          n('name',p['name'],fx(1.016)),n('number',str(num),fx(1.016))))
    sym.append(unit)
    return sym


def get_symbol(identifier):
    lib,name=identifier.split(':')
    if lib=='hub-custom':
        return boxed(name,{str(i+1):{'name':a,'type':b} for i,(a,b) in enumerate(CUSTOM[name])})
    s=source_symbol(identifier)
    if lib not in ['Device','Transistor_FET','Diode','Connector','Mechanical','hub-isolator','power']:
        old=pin_table(s);s2=boxed(name,old)
        assert {(k,v['name'],v['type']) for k,v in old.items()}=={(k,v['name'],v['type']) for k,v in pin_table(s2).items()}
        return s2
    return s


def renamed(sym,name):
    s=deepcopy(sym);old=s[1];s[1]=name
    for sub in children(s,'symbol'):sub[1]=sub[1].replace(old+'_',name+'_',1)
    return s


def build_library(parts):
    symbols={}
    for p in parts.values():
        key=p['lib'].replace(':','_')
        if key not in symbols:
            symbols[key]=renamed(get_symbol(p['lib']),key)
        p['local_lib']='hub-lib:'+key
        p['symbol']=symbols[key]
        p['symbol_pins']=pin_table(symbols[key])
        actual=set(p['symbol_pins']);expected=set(p['pins'])
        # Some stock gate symbols omit the physically unused pin 1.
        assert actual<=expected,(p['ref'],'missing nets for pins',actual-expected)
        assert all(p['pins'][k] is None for k in expected-actual),(p['ref'],'nonexistent symbol pins',expected-actual)
    write(ROOT/'hub-lib.kicad_sym',n('kicad_symbol_lib',n('version',20250114),n('generator','kicad_symbol_editor'),*symbols.values()))
    return symbols
