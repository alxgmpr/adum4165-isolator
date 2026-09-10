"""Independent critical-path assertions against exported XML, not design.py.

Checks architecture invariants and USB polarity. Datasheet/package verification,
ERC, analog calculations and hardware timing are separate evidence.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import json
ROOT=Path(__file__).resolve().parents[2]
x=ET.parse(ROOT/'build/revc/hub.xml').getroot()
nets={(n.attrib['ref'],n.attrib['pin']):a.attrib['name'] for a in x.find('nets') for n in a.findall('node')}
components={c.attrib['ref']:c for c in x.find('components')}
checks=[]
def expect(ref,mapping):
 for pin,net in mapping.items():assert nets.get((ref,str(pin)))==net,(ref,pin,nets.get((ref,str(pin))),net)
 checks.append(ref+': critical pin/net assertions')
expect('U1',{1:'VBUS_HOST',2:'U1_3V3_HOST',3:'GND1',4:'U1_1V8_HOST',5:'U1_1V8_HOST',6:'ISO_SIDE_OK',7:'HOST_D-',8:'HOST_D+',11:'U1_1V8_HOST',12:'GND1',13:'U1_3V3_HOST',16:'ISO_3V3',17:'GND2',18:'U1_1V8_ISO',21:'HUB_UP_D+',22:'HUB_UP_D-',23:'HOST_PRESENT',24:'ISO_3V3',25:'U1_1V8_ISO',26:'GND2',27:'ISO_3V3',28:'ISO_3V3'})
expect('U11',{1:'PORT1_D-',2:'PORT1_D+',3:'PORT2_D-',4:'PORT2_D+',6:'PORT3_D-',7:'PORT3_D+',8:'PORT4_D-',9:'PORT4_D+',14:'HUB_CRFILT',22:'HUB_SDA',24:'HUB_SCL',25:'HUB_CFG1',26:'HUB_RESET_N',27:'HUB_VBUS_DET',28:'EXT_SELECTED',30:'HUB_UP_D-',31:'HUB_UP_D+',32:'HUB_XO',33:'HUB_XI',34:'HUB_PLLFILT',35:'HUB_RBIAS',37:'GND2'})
expect('U8',{1:'ISO_5V',2:'ISO_5V_PRE',3:'MUX_CP2',4:'GND2',5:'GND2',6:'MUX_PR1',7:'EXT_REG_5V',8:'ISO_5V',9:'EXT_SELECTED',12:'GND2'})
expect('U33',{1:'HUB_RESET_N',2:'GND2',3:'HOST_PRESENT',5:'ISO_3V3',6:'ISO_3V3'})
expect('Y2',{1:'HUB_XO',2:'GND2',3:'HUB_XI',4:'GND2'})
assert 'Y1' not in components and 'ADUM4165' not in (ROOT/'hub.kicad_sch').read_text().upper()
for ref,prefix,power,gnd in [('J1','HOST','VBUS_HOST','GND1'),('J5','PORT3','PORT3_VBUS','GND2'),('J6','PORT4','PORT4_VBUS','GND2')]:
 expect(ref,{'A6':prefix+'_D+','B6':prefix+'_D+','A7':prefix+'_D-','B7':prefix+'_D-','A5':prefix+'_CC1','B5':prefix+'_CC2','A4':power,'SH':gnd})
for port in range(1,5):
 prefix='PORT'+str(port);expect('U'+str(15+port),{1:prefix+'_D-',6:prefix+'_D-',3:prefix+'_D+',4:prefix+'_D+',2:'GND2',5:prefix+'_VBUS'})
 expect('U'+str(11+port),{1:'PORT_SUPPLY',2:'GND2',3:('PRTPWR'+str(port) if port<=2 else prefix+'_EN'),4:'OCS'+str(port)+'_N',6:prefix+'_VBUS'})
for port in [3,4]:
 d=port-3;p='PORT'+str(port)
 expect('U'+str(20+d),{3:'U'+str(20+d)+'_PORT',9:p+'_ID_N',10:'GND2',11:'GND2',12:'ISO_3V3'})
 expect('U'+str(35+d),{2:p+'_ID_N',4:p+'_ATTACHED'})
 expect('U'+str(37+d),{1:'PRTPWR'+str(port),2:p+'_ATTACHED',4:p+'_EN'})
 expect('U'+str(39+d),{2:p+'_EN',4:p+'_DISCHARGE'})
 expect('Q'+str(5+d),{1:p+'_DISCHARGE',2:'GND2',3:p+'_DISCHARGE_D'})
expect('U24',{2:'HOST_OUT1',4:'HOST_PWR_OK'});expect('U25',{1:'EXT_OUT1',2:'EXT_OUT2',4:'EXT_3A_OK'})
expect('U29',{1:'ISO_5V',3:'BUS_FEED_EN',4:'BUS_LIMIT_RAW_N',6:'PORT_SUPPLY'})
expect('U48',{2:'BUS_FAULT_FILTER_N',3:'GND2',4:'PORT_LIMIT_N',5:'ISO_3V3'})
expect('C116',{1:'ISO_3V3',2:'BUS_FAULT_CAP'})
expect('U30',{1:'ISO_5V',3:'EXT_BYPASS_EN',7:'EXT_PORT_FEED',8:'EXT_PORT_FEED',9:'GND2'})
expect('R116',{1:'EXT_PORT_FEED',2:'PORT_SUPPLY'});expect('R110',{1:'EXT_5V',2:'EXT_SENSED_5V'})
expect('R112',{1:'EXT_CURRENT_OK',2:'PORT_RAIL_OK'})
for ref,mapping in [('TP13',{1:'HUB_RESET_N'}),('TP14',{1:'HUB_SDA'}),('TP15',{1:'HUB_SCL'}),('TP16',{1:'GND2'}),('SH1',{1:'GND1'}),('SH2',{1:'GND2'}),('CY1',{1:'GND1',2:'GND2'})]:expect(ref,mapping)
domains=json.loads((ROOT/'docs/revc/reports/net-domains.json').read_text())
cross={}
for ref in components:
 ds={domains[net] for (r,p),net in nets.items() if r==ref}
 if len(ds)>1:cross[ref]=sorted(ds)
assert set(cross)=={'U1','T1','CY1'},cross
truth=[]
for attach,permission in [(0,0),(0,1),(1,0),(1,1)]:truth.append({'sink_attached':attach,'hub_permission':permission,'port_VBUS_enable':attach & permission,'discharge_enable':1-(attach & permission)})
report={'critical_component_checks':len(checks),'checks':checks,'only_cross_domain_components':cross,'type_c_logic_truth_table':truth,'errors':[],'limits':'Logical/netlist checks, not analog startup, fault timing, isolation certification or hardware USB testing.'}
(ROOT/'docs/revc/reports/electrical-invariants.json').write_text(json.dumps(report,indent=2)+'\n');print('Critical electrical checks:',len(checks),'passed; only U1/T1/CY1 span domains')
