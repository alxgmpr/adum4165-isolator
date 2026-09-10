"""Rev C electrical source. All part data is written into the schematic by capture.py.

The immutable baseline inventory is retained for connectivity change reports.
This module does not write any board, track, or via.
"""
from pathlib import Path
import json
import uuid

ROOT = Path(__file__).resolve().parents[2]
BASE = json.loads((ROOT / 'docs/revc/baseline-connectivity.json').read_text())
PARTS = {}


def add(ref, value, lib, pins, page, mpn='', manufacturer='', footprint='', note='', dnp=False):
    if ref in PARTS:
        raise ValueError(f'duplicate reference {ref}')
    PARTS[ref] = dict(ref=ref, value=value, lib=lib, pins={str(k): v for k, v in pins.items()},
                      page=page, mpn=mpn, manufacturer=manufacturer, footprint=footprint,
                      note=note, dnp=dnp, uuid=BASE.get(ref, {}).get('uuid', str(uuid.uuid5(uuid.NAMESPACE_URL, 'isolator-revc/' + ref))))
    return PARTS[ref]


def r(ref, val, a, b, page, note='', dnp=False):
    return add(ref, val, 'Device:R_Small_US', {1: a, 2: b}, page, note=note, dnp=dnp)


def c(ref, val, rail, ground, page, note=''):
    return add(ref, val, 'Device:C_Polarized' if val=='220uF' else 'Device:C', {1: rail, 2: ground}, page, note=note)


def ic(ref, mpn, lib, pins, page, note=''):
    return add(ref, mpn, lib, pins, page, mpn, 'Texas Instruments', note=note)


def tp(ref, net, page):
    return add(ref, net, 'Connector:TestPoint', {1: net}, page, footprint='TestPoint:TestPoint_Pad_D1.0mm', note='PCB test pad; no purchased part')


def mos(ref, gate, source, drain, page, note=''):
    return add(ref, '2N7002', 'Transistor_FET:2N7002', {1: gate, 2: source, 3: drain}, page,
               '2N7002,215', 'Nexperia', 'Package_TO_SOT_SMD:SOT-23', note)


def inv(ref, inp, out, supply, ground, page):
    return ic(ref, 'SN74LVC1G04DBVR', '74xGxx:74LVC1G04', {1: None, 2: inp, 3: ground, 4: out, 5: supply}, page)


def and_gate(ref, a, b, out, page):
    return ic(ref, 'SN74LVC1G08DBVR', '74xGxx:74LVC1G08', {1: a, 2: b, 3: 'GND2', 4: out, 5: 'ISO_3V3'}, page)


def tusb(ref, cc1, cc2, supply, ground, page, role, out1=None, out2=None, ident=None, vdet=None):
    return ic(ref, 'TUSB320LAIRWBR', 'hub-custom:TUSB320LAI',
              {1: cc1, 2: cc2, 3: ground if role == 'sink' else ref+'_PORT', 4: vdet,
               5: None, 6: None, 7: out1, 8: out2, 9: ident, 10: ground, 11: ground, 12: supply}, page,
              'GPIO; '+role+' only; internal Rd/Rp. LAI current-tracking variant required.')


def usb_c(ref, prefix, power, ground, page, data=True):
    pins = {p: ground for p in ['A1','A12','B1','B12','SH']}
    pins.update({p: power for p in ['A4','A9','B4','B9']})
    pins.update({'A5': prefix+'_CC1', 'B5': prefix+'_CC2', 'A8': None, 'B8': None,
                 'A6': prefix+'_D+' if data else None, 'B6': prefix+'_D+' if data else None,
                 'A7': prefix+'_D-' if data else None, 'B7': prefix+'_D-' if data else None})
    return add(ref, 'USB-C USB2.0' if data else 'USB-C 5V POWER', 'Connector:USB_C_Receptacle_USB2.0_16P', pins, page,
               'TYPE-C-31-M-12', 'HRO', 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12')


def esd(ref, prefix, power, ground, page):
    return add(ref, 'USBLC6-2SC6', 'Power_Protection:USBLC6-2SC6',
               {1: prefix+'_D-', 6: prefix+'_D-', 3: prefix+'_D+', 4: prefix+'_D+', 2: ground, 5: power},
               page, 'USBLC6-2SC6', 'STMicroelectronics', 'Package_TO_SOT_SMD:SOT-23-6',
               'Flow-through: 1/6 D-, 3/4 D+. Place at connector; no data stubs.')


# Upstream input and current qualification. Main converter capacitance is behind U26.
usb_c('J1', 'HOST', 'VBUS_HOST', 'GND1', 'host')
esd('U2', 'HOST', 'VBUS_HOST', 'GND1', 'host')
c('C1','100nF','VBUS_HOST','GND1','host','J1 local bypass')
c('C2','1uF','VBUS_HOST','GND1','host','U22 input')
ic('U22','TLV75533PDBVR','Regulator_Linear:TLV75533PDBV', {1:'VBUS_HOST',2:'GND1',3:'VBUS_HOST',4:None,5:'HOST_3V3'},'host')
c('C61','1uF','HOST_3V3','GND1','host','U22 output; Ceff >= 0.47uF')
tusb('U3','HOST_CC1','HOST_CC2','HOST_3V3','GND1','host','sink','HOST_OUT1','HOST_OUT2',vdet='HOST_VDET')
r('R1','909kR','VBUS_HOST','HOST_VDET','host')
r('R2','10kR','HOST_3V3','HOST_OUT1','host')
r('R3','10kR','HOST_3V3','HOST_OUT2','host')
c('C7','100nF','HOST_3V3','GND1','host','U3.12')
inv('U24','HOST_OUT1','HOST_PWR_OK','HOST_3V3','GND1','host')
c('C8','100nF','HOST_3V3','GND1','host','U24.5')
r('R4','100kR','HOST_PWR_OK','GND1','host','Default-off converter permission')
ic('U26','TPS2553DBVR','isolator-lib:TPS2553DBV',
   {1:'VBUS_HOST',2:'GND1',3:'HOST_PWR_OK',4:'HOST_LIMIT_N',5:'HOST_ILIM',6:'HOST_CONVERTER_5V'},'host',
   'Input current limit and controlled converter startup; no high-current load on default source')
r('R5','28.7kR','HOST_ILIM','GND1','host','825 to 990mA steady current limit across 1% resistor; transformer driver protection')
r('R6','10kR','HOST_3V3','HOST_LIMIT_N','host')
c('C62','100nF','VBUS_HOST','GND1','host','U26.1')
tp('TP1','HOST_PWR_OK','host');tp('TP2','HOST_LIMIT_N','host')

# Host-side 1.8 V buck fixes the >100mA upstream draw of the all-linear default.
# VBUS1 stays on 5 V; only the core regulator is bypassed per TI section 8.2.4.
ic('U45','TLV62568DBVR','Regulator_Switching:TLV62568DBV',
   {1:'VBUS_HOST',2:'GND1',3:'HOST18_SW',4:'VBUS_HOST',5:'HOST18_FB'},'host')
add('L4','2.2uH','Device:L',{1:'HOST18_SW',2:'U1_1V8_HOST'},'host','XFL4020-222MEC','Coilcraft')
c('C113','4.7uF','VBUS_HOST','GND1','host','U45.4 input; part of direct attach capacitance')
c('C114','22uF','U1_1V8_HOST','GND1','host','U45 output in addition to the local U1 bypass groups')
r('R114','200kR','U1_1V8_HOST','HOST18_FB','host')
r('R115','100kR','HOST18_FB','GND1','host')

# ISOUSB211, without an isolator crystal. Four independently placed bypass groups.
iso = json.loads((ROOT/'tools/revc/isousb211.json').read_text())
ic('U1',iso['mpn'],'hub-isolator:ISOUSB211DPR',{p[0]:p[3] for p in iso['pins']},'isolation')
PARTS['U1']['footprint']='hub-lib:TI_DP0028A-C02_HV_SSOP28_8.2mm_Clearance'
for ref, val, rail, gnd, note in [
 ('C3','1uF','VBUS_HOST','GND1','U1.1 to U1.3'),
 ('C4','100nF','U1_3V3_HOST','GND1','U1.2 to U1.3'),
 ('C28','1uF','ISO_3V3','GND2','U1.28 to U1.26'),
 ('C29','100nF','ISO_3V3','GND2','U1.27 to U1.26'),
 ('C63','100nF','U1_1V8_HOST','GND1','U1.5 to U1.3'),
 ('C64','1uF','ISO_3V3','GND2','U1.24 to U1.26')]: c(ref,val,rail,gnd,'isolation',note)
for k,(supply,ground,pin,gpin) in enumerate([
 ('U1_1V8_HOST','GND1',4,3),('U1_1V8_HOST','GND1',11,12),
 ('U1_1V8_ISO','GND2',25,26),('U1_1V8_ISO','GND2',18,17)]):
    for j,val in enumerate(['4.7uF','100nF','10nF']):
        c('C'+str(65+3*k+j),val,supply,ground,'isolation',f'U1.{pin} to U1.{gpin}; top-layer loop; smallest capacitor closest')
for k,net in enumerate(['EQ10','EQ11','EQ20','EQ21']):
    ground='GND1' if k<2 else 'GND2'; supply='U1_3V3_HOST' if k<2 else 'ISO_3V3'
    r('R'+str(51+2*k),'0R',net,ground,'isolation','Fitted: zero equalization')
    r('R'+str(52+2*k),'0R',net,supply,'isolation','DNP: EQ rework; never fit both straps',True)
tp('TP3','ISO_SIDE_OK','isolation');tp('TP4','HOST_PRESENT','isolation')
add('CY1','1nF Y1','Device:C',{1:'GND1',2:'GND2'},'isolation',
    'Q07F3Z102MA5B0S0N0','STE Songtian','isolator-lib:C_Disc_D7.0mm_W5.5mm_P14.00mm',
    note='1nF 400VAC Y1, 14mm lead spacing; sole intentional inter-ground capacitance')

# Retained isolated power chain, with the previously bypassed configuration links repaired.
ic('U5','SN6505BDBVR','Power_Management:SN6505BDBV',
   {1:'PRI_B',2:'HOST_CONVERTER_5V',3:'PRI_A',4:'GND1',5:'HOST_CONVERTER_5V',6:'GND1'},'converter')
add('T1','750313638','isolator-lib:750313638', {1:'PRI_A',2:'HOST_CONVERTER_5V',3:'PRI_B',4:'SEC_B',5:'GND2',6:'SEC_A'},
    'converter','750313638','Wurth Elektronik','isolator-lib:WE_750313638')
for ref,val in [('C10','100nF'),('C11','4.7uF'),('C12','100nF')]:c(ref,val,'HOST_CONVERTER_5V','GND1','converter','U5 primary current loop')
for ref,anode in [('D3','SEC_A'),('D4','SEC_B')]:
    add(ref,'SS34','Device:D_Schottky',{1:'DCDC_RAW',2:anode},'converter','SS34','MDD Microdiode Electronics','Diode_SMD:D_SMA')
for ref,val in [('C13','22uF'),('C14','100nF'),('C15','22uF'),('C16','22uF'),('C17','100nF')]:c(ref,val,'DCDC_RAW','GND2','converter','Rectifier/U6 input; voltage up to 7.2V')
ic('U6','TPS630701RNMR','isolator-lib:TPS630701RNM',
   {1:'BB_PS',2:'BB_PG',3:'BB_VAUX',4:'GND2',5:'BB_FB',6:None,7:'ISO_5V_PRE',8:'ISO_5V_PRE',
    9:'BB_L2',10:'GND2',11:'BB_L1',12:'DCDC_RAW',13:'DCDC_RAW',14:'DCDC_RAW',15:'GND2'},'converter')
add('L1','1.5uH','Device:L',{1:'BB_L1',2:'BB_L2'},'converter','XFL4020-152MEC','Coilcraft')
for ref,val in [('C18','22uF'),('C19','22uF'),('C20','22uF'),('C21','100nF')]:c(ref,val,'ISO_5V_PRE','GND2','converter','U6 output bank')
c('C22','100nF','BB_VAUX','GND2','converter','U6.3; no external load')
r('R10','0R','ISO_5V_PRE','BB_FB','converter','Fixed-output feedback link')
r('R11','100kR','ISO_5V_PRE','BB_PS','converter','Power-save mode')
r('R12','100kR','ISO_5V_PRE','BB_PG','converter')
r('R15','0R','BB_PS','GND2','converter','DNP: forced PWM rework; remove R11 first',True)
tp('TP5','DCDC_RAW','converter');tp('TP6','ISO_5V_PRE','converter')
for ref,mpn,gnd in [('SH1','BMI-S-201-F','GND1'),('SH2','BMI-S-209-F','GND2')]:
    add(ref,mpn,'hub-custom:Shield_Frame',{1:gnd},'converter',mpn,'Laird Performance Materials',note='Separate removable cover ordered separately; never bridge domains')

# Qualified and regulated external power. The converter is physically disconnected
# by a slew-controlled input switch until the source advertises 3 A.
usb_c('J2','EXT','EXT_5V','GND2','external',data=False)
ic('U23','TLV75533PDBVR','Regulator_Linear:TLV75533PDBV',{1:'EXT_5V',2:'GND2',3:'EXT_5V',4:None,5:'EXT_3V3'},'external')
c('C23','100nF','EXT_5V','GND2','external','J2 bypass')
c('C24','1uF','EXT_5V','GND2','external','U23 input')
c('C77','1uF','EXT_3V3','GND2','external','U23 output')
tusb('U7','EXT_CC1','EXT_CC2','EXT_3V3','GND2','external','sink','EXT_OUT1','EXT_OUT2',vdet='EXT_VDET')
r('R16','909kR','EXT_5V','EXT_VDET','external')
r('R17','10kR','EXT_3V3','EXT_OUT1','external');r('R18','10kR','EXT_3V3','EXT_OUT2','external')
ic('U25','SN74LVC1G02DBVR','74xGxx:74LVC1G02',{1:'EXT_OUT1',2:'EXT_OUT2',3:'GND2',4:'EXT_3A_OK',5:'EXT_3V3'},'external')
c('C25','100nF','EXT_3V3','GND2','external','U7.12');c('C26','100nF','EXT_3V3','GND2','external','U25.5')
r('R19','100kR','EXT_3A_OK','GND2','external')
ic('U27','TPS22975DSGR','hub-custom:TPS22975',{1:'EXT_SENSED_5V',2:'EXT_SENSED_5V',3:'EXT_3A_OK',4:'EXT_5V',5:'GND2',6:'EXT_SLEW',7:'EXT_SW_5V',8:'EXT_SW_5V',9:'GND2'},'external')
# Input current monitor sheds port load without interrupting the hub supply.
# The 3A qualification switch remains on; board-internal faults use U28/source protection.
r('R110','20mR','EXT_5V','EXT_SENSED_5V','external','1% 0.5W current shunt; Kelvin sense U46 inputs')
ic('U46','INA300AIDGSR','hub-custom:INA300',
   {1:'EXT_5V',2:'EXT_SENSED_5V',3:'EXT_TRIP',4:'ISO_3V3',5:'EXT_CURRENT_OK',
    6:'PORT_ANY_ON',7:'ISO_3V3',8:'GND2',9:'ISO_3V3',10:None},'external',
   '100us input-overload detection sheds ports while keeping core supply alive; clears when hub removes every port permission')
r('R111','2.87kR','EXT_TRIP','GND2','external','0.1%; 20uA * 2.87k / 20m = 2.87A nominal')
r('R112','0R','EXT_CURRENT_OK','PORT_RAIL_OK','external','Wired-OR port-shedding fault link; open only for diagnostic isolation')
c('C110','100nF','ISO_3V3','GND2','external','U46.9')
tp('TP17','EXT_CURRENT_OK','external')
c('C78','10nF','EXT_SLEW','GND2','external','U27 controlled input inrush')
for ref,val in [('C79','22uF'),('C80','22uF'),('C81','100nF')]:c(ref,val,'EXT_SW_5V','GND2','external','U28 input')
ic('U28','TPS552892RYQR','hub-custom:TPS552892',
   {1:'EXT_3A_OK',2:'GND2',3:'EXT_REG_PG',4:None,5:'GND2',6:'EXT_FSW',7:'EXT_SW_5V',8:'EXT_SW1',9:'GND2',
    10:'EXT_SW2',11:'EXT_REG_5V',12:'EXT_REG_5V',13:'EXT_REG_5V',14:'EXT_FB',15:'EXT_COMP',16:None,17:'GND2',
    18:'EXT_REG_VCC',19:'EXT_BOOT2',20:'EXT_BOOT1',21:None},'external','Regulates external VBUS for switch-drop allowance')
add('L3','4.7uH','Device:L',{1:'EXT_SW1',2:'EXT_SW2'},'external','XAL7070-472MEC','Coilcraft')
c('C82','100nF','EXT_BOOT1','EXT_SW1','external','U28.20 boot');c('C83','100nF','EXT_BOOT2','EXT_SW2','external','U28.19 boot')
c('C84','10uF','EXT_REG_VCC','GND2','external','U28.18; effective capacitance >4.7uF')
for ref in ['C85','C86','C87','C88']:c(ref,'22uF','EXT_REG_5V','GND2','external','U28 output bank')
c('C89','100nF','EXT_REG_5V','GND2','external','U28.11')
r('R20','10kR','EXT_REG_5V','EXT_FB','external','0.1% feedback upper')
r('R21','3kR','EXT_FB','EXT_FB_LOW','external','0.1% feedback lower series part')
r('R22','15R','EXT_FB_LOW','GND2','external','0.1%: Vout = 1.2*(1+10000/3015) = 5.1801V')
r('R59','49.9kR','EXT_FSW','GND2','external','400kHz; L > 3uH')
r('R60','2.7kR','EXT_COMP','EXT_COMP_ZERO','external','Loop compensation; see power calculation')
c('C90','220nF','EXT_COMP_ZERO','GND2','external');c('C91','100pF','EXT_COMP','GND2','external')
r('R61','10kR','EXT_3V3','EXT_REG_PG','external');tp('TP7','EXT_3A_OK','external');tp('TP8','EXT_REG_5V','external')

# Power distribution: logic is upstream of the limited port bus. The low-current
# path remains active when the external bypass is turned off by mux status.
ic('U8','TPS2121RUXR','isolator-lib:TPS2121',
   {1:'ISO_5V',2:'ISO_5V_PRE',3:'MUX_CP2',4:'GND2',5:'GND2',6:'MUX_PR1',7:'EXT_REG_5V',
    8:'ISO_5V',9:'EXT_SELECTED',10:'MUX_ILIM',11:'MUX_SS',12:'GND2'},'distribution')
r('R23','17.8kR','EXT_REG_5V','MUX_PR1','distribution');r('R24','10kR','MUX_PR1','GND2','distribution')
r('R25','23.7kR','ISO_5V_PRE','MUX_CP2','distribution');r('R26','10.2kR','MUX_CP2','GND2','distribution')
r('R27','29.8kR','MUX_ILIM','GND2','distribution','3 to 4 A datasheet range; secondary protection, precise limits are upstream and on port bus')
r('R28','10kR','ISO_3V3','EXT_SELECTED','distribution','ST high means IN1 or Hi-Z; logic powered by OUT')
c('C27','100nF','MUX_SS','GND2','distribution')
c('C92','220uF','ISO_5V','GND2','distribution','Logic hold-up during source switch and load shedding')
c('C93','100nF','ISO_5V','GND2','distribution','U8 OUT bypass')
ic('U29','TPS2553DBVR-1','isolator-lib:TPS2553DBV',
   {1:'ISO_5V',2:'GND2',3:'BUS_FEED_EN',4:'PORT_LIMIT_N',5:'PORT_ILIM',6:'PORT_SUPPLY'},'distribution',
   'Latch-off aggregate bus-mode limiter; 300mA intended shared load')
r('R62','75kR','PORT_ILIM','GND2','distribution')
r('R63','10kR','ISO_3V3','PORT_LIMIT_N','distribution')
and_gate('U32','EXT_SELECTED','PORT_FEED_EN','EXT_BYPASS_EN','distribution')
ic('U30','TPS22975NDSGR','hub-custom:TPS22975',
   {1:'ISO_5V',2:'ISO_5V',3:'EXT_BYPASS_EN',4:'ISO_5V',5:'GND2',6:'EXT_PORT_SLEW',7:'EXT_PORT_FEED',8:'EXT_PORT_FEED',9:'GND2'},
   'distribution','No-QOD N variant: external-mode path; no discharge of live shared rail')
c('C115','22nF','EXT_PORT_SLEW','GND2','distribution','U30 controlled ramp avoids simultaneous USB-A reservoir inrush')
r('R116','10mR','EXT_PORT_FEED','PORT_SUPPLY','distribution','1% 0.5W shunt; Kelvin sense U47; maximum routing drop in power report')
ic('U47','INA300AIDGSR','hub-custom:INA300',
   {1:'EXT_PORT_FEED',2:'PORT_SUPPLY',3:'EXT_PORT_TRIP',4:'ISO_3V3',5:'PORT_RAIL_OK',
    6:'PORT_ANY_ON',7:None,8:'GND2',9:'ISO_3V3',10:None},'distribution',
   '10us port overload cutoff, before 100us input cutoff; latches until hub removes all port permissions')
r('R117','1.1kR','EXT_PORT_TRIP','GND2','distribution','0.1%; (20uA*1.1k - 500uV) / 10m = 2.15A nominal')
c('C112','100nF','ISO_3V3','GND2','distribution','U47.9')
ic('U31','TPS3808G01DBVR','hub-custom:TPS3808',
   {1:'PORT_RAIL_OK',2:'GND2',3:'ISO_3V3',4:None,5:'PORT_SENSE',6:'ISO_3V3'},'distribution',
   'Port-only undervoltage shedding before hub buck loses regulation; 20ms retry delay')
r('R64','100kR','ISO_5V','PORT_SENSE','distribution');r('R65','10kR','PORT_SENSE','GND2','distribution')
r('R66','10kR','ISO_3V3','PORT_RAIL_OK','distribution')
for ref,rail,note in [('C94','ISO_3V3','U31.6'),('C95','ISO_3V3','U32.5'),('C96','ISO_5V','U29.1/U30.1'),('C97','PORT_SUPPLY','Port distribution')]:c(ref,'100nF',rail,'GND2','distribution',note)
tp('TP9','ISO_5V','distribution');tp('TP10','PORT_SUPPLY','distribution');tp('TP11','PORT_RAIL_OK','distribution')
and_gate('U41','PORT_ANY_ON','PORT_RAIL_OK','PORT_FEED_EN','distribution')
inv('U42','EXT_SELECTED','BUS_SELECTED','ISO_3V3','GND2','distribution')
and_gate('U43','PORT_FEED_EN','BUS_SELECTED','BUS_FEED_EN','distribution')
r('R83','10kR','PORT_ANY_ON','GND2','distribution')
c('C107','100nF','ISO_3V3','GND2','distribution','U41.5')
c('C108','100nF','ISO_3V3','GND2','distribution','U42.5')
c('C109','100nF','ISO_3V3','GND2','distribution','U43.5')
for port in range(1,5):
    add('D'+str(13+port),'BAT54WS','Device:D_Schottky',{1:'PORT_ANY_ON',2:'PRTPWR'+str(port)},'distribution',
        'BAT54WS-7-F','Diodes Incorporated','Diode_SMD:D_SOD-323','Diode OR; any hub permission enables aggregate path')
for idx,(fault,pa,pb) in enumerate([('PORT_LIMIT_N',1,2),('PORT_LIMIT_N',3,4),('PORT_RAIL_OK',1,2),('PORT_RAIL_OK',3,4)]):
    add('D'+str(20+idx),'BAT54C','Diode:BAT54C',{1:f'OCS{pa}_N',2:f'OCS{pb}_N',3:fault},'distribution',
        'BAT54C,215','Nexperia','Package_TO_SOT_SMD:SOT-23','Common-cathode fault fanout; preserves independent port faults')

# Shared 3.3 V supply and hub, including reset and source-aware EEPROM configuration.
ic('U10','TPS62162DSGR','Regulator_Switching:TPS62162DSG',
   {1:'GND2',2:'ISO_5V',3:'ISO_5V',4:'GND2',5:'GND2',6:'ISO_3V3',7:'BUCK33_SW',8:'BUCK33_PG',9:'GND2'},'hub')
add('L2','2.2uH','Device:L',{1:'BUCK33_SW',2:'ISO_3V3'},'hub','XFL4020-222MEC','Coilcraft')
c('C30','10uF','ISO_5V','GND2','hub','U10.2');c('C31','22uF','ISO_3V3','GND2','hub','U10.6 output bank')
r('R67','10kR','ISO_3V3','BUCK33_PG','hub')
hubpins={1:'PORT1_D-',2:'PORT1_D+',3:'PORT2_D-',4:'PORT2_D+',5:'ISO_3V3',6:'PORT3_D-',7:'PORT3_D+',8:'PORT4_D-',9:'PORT4_D+',
 10:'ISO_3V3',11:'GND2',12:'PRTPWR1',13:'OCS1_N',14:'HUB_CRFILT',15:'ISO_3V3',16:'PRTPWR2',17:'OCS2_N',18:'PRTPWR3',
 19:'OCS3_N',20:'PRTPWR4',21:'OCS4_N',22:'HUB_SDA',23:'ISO_3V3',24:'HUB_SCL',25:'HUB_CFG1',26:'HUB_RESET_N',
 27:'HUB_VBUS_DET',28:'EXT_SELECTED',29:'ISO_3V3',30:'HUB_UP_D-',31:'HUB_UP_D+',32:'HUB_XO',33:'HUB_XI',34:'HUB_PLLFILT',35:'HUB_RBIAS',36:'ISO_3V3',37:'GND2'}
add('U11','USB2514B-I/M2','Interface_USB:USB2514B_Bi',hubpins,'hub','USB2514B-I/M2','Microchip Technology')
add('Y2','24MHz','Device:Crystal_GND24_Small',{1:'HUB_XO',2:'GND2',3:'HUB_XI',4:'GND2'},'hub','ABM8G-24.000MHZ-18-D2Y-T','Abracon')
c('C32','27pF','HUB_XO','GND2','hub','CL18pF: 27pF external + 6pF IC + 3pF PCB per pin, divided by two; verify frequency')
c('C33','27pF','HUB_XI','GND2','hub','Matched to C32; adjust after measuring stray capacitance/frequency')
c('C34','100nF','HUB_CRFILT','GND2','hub','U11.14; datasheet allows 0.1uF nominal maximum')
c('C59','100nF','HUB_PLLFILT','GND2','hub','U11.34; no added parallel 10nF')
for ref,pin in zip(['C35','C36','C37','C38','C39','C40'],[5,10,15,23,29,36]):c(ref,'100nF','ISO_3V3','GND2','hub',f'U11.{pin} to EP37')
c('C41','4.7uF','ISO_3V3','GND2','hub','Shared hub bulk')
r('R32','12kR','HUB_RBIAS','GND2','hub','1% RBIAS; place at U11.35')
ic('U33','TPS3808G33DBVR','hub-custom:TPS3808',
   {1:'HUB_RESET_N',2:'GND2',3:'HOST_PRESENT',4:None,5:'ISO_3V3',6:'ISO_3V3'},'hub',
   '20ms reset delay, 3.07V nominal threshold; MR holds hub reset while host absent')
r('R33','10kR','ISO_3V3','HUB_RESET_N','hub')
r('R34','4.7kR','ISO_3V3','HUB_SCL','hub');r('R35','10kR','ISO_3V3','HUB_CFG1','hub')
r('R36','4.7kR','ISO_3V3','HUB_SDA','hub')
r('R37','1kR','HOST_PRESENT','HUB_VBUS_DET','hub');r('R31','100kR','HUB_VBUS_DET','GND2','hub')
c('C42','100nF','ISO_3V3','GND2','hub','U33.6')
add('U34','24LC02B-I/SN','Memory_EEPROM:24LC02B',{1:'GND2',2:'GND2',3:'GND2',4:'GND2',5:'HUB_SDA',6:'HUB_SCL',7:'GND2',8:'ISO_3V3'},
    'hub','24LC02B-I/SN','Microchip Technology','Package_SO:SOIC-8_3.9x4.9mm_P1.27mm','Must program supplied EEPROM image before bring-up')
c('C98','100nF','ISO_3V3','GND2','hub','U34.8')
for ref,net in [('TP12','ISO_3V3'),('TP13','HUB_RESET_N'),('TP14','HUB_SDA'),('TP15','HUB_SCL'),('TP16','GND2')]:tp(ref,net,'hub')

# Four independent protected ports. USB-C uses standalone attach detection;
# no VCONN is implemented (USB2-only). TPS2553 enables require both hub
# permission and valid attachment, and an external discharge FET empties VBUS.
for port in range(1,5):
    page='ports_a' if port<=2 else 'port_c'+str(port); prefix='PORT'+str(port)
    permission='PRTPWR'+str(port) if port<=2 else prefix+'_EN'
    if port<=2:
        add('J'+str(port+2),'USB-A','Connector:USB_A',{1:prefix+'_VBUS',2:prefix+'_D-',3:prefix+'_D+',4:'GND2','SH':'GND2'},
            page,'614004134726','Wurth Elektronik','Connector_USB:USB_A_Wuerth_614004134726_Horizontal')
    else: usb_c('J'+str(port+2),prefix,prefix+'_VBUS','GND2',page)
    ic('U'+str(11+port),'TPS2553DBVR','isolator-lib:TPS2553DBV',
       {1:'PORT_SUPPLY',2:'GND2',3:permission,4:'OCS'+str(port)+'_N',5:prefix+'_ILIM',6:prefix+'_VBUS'},page)
    r({1:'R38',2:'R39',3:'R40',4:'R44'}[port],'46.4kR',prefix+'_ILIM','GND2',page,'Guarantee >=500mA; see tolerance report')
    r('R'+str(46+port),'100kR','ISO_3V3','OCS'+str(port)+'_N',page)
    esd('U'+str(15+port),prefix,prefix+'_VBUS','GND2',page)
    for ref,val,rail in zip({1:['C43','C44','C45'],2:['C46','C47','C48'],3:['C49','C50','C51'],4:['C55','C56','C57']}[port],
                            ['100nF','220uF' if port<=2 else '10uF','100nF'],['PORT_SUPPLY',prefix+'_VBUS',prefix+'_VBUS']):
        c(ref,val,rail,'GND2',page,'Port '+str(port)+' VBUS bypass')
    r('R'+str(100+port),'100kR',permission,'GND2',page,'Switch default off during reset')
    if port>=3:
        ctref='U'+str(17+port)
        tusb(ctref,prefix+'_CC1',prefix+'_CC2','ISO_3V3','GND2',page,'source',ident=prefix+'_ID_N',vdet=prefix+'_VDET')
        r('R'+str(72+3*(port-3)),'4.7kR','ISO_3V3',ctref+'_PORT',page)
        r('R'+str(73+3*(port-3)),'10kR','ISO_3V3',prefix+'_ID_N',page)
        r('R'+str(74+3*(port-3)),'909kR',prefix+'_VBUS',prefix+'_VDET',page)
        inv('U'+str(32+port),prefix+'_ID_N',prefix+'_ATTACHED','ISO_3V3','GND2',page)
        and_gate('U'+str(34+port),'PRTPWR'+str(port),prefix+'_ATTACHED',prefix+'_EN',page)
        inv('U'+str(36+port),prefix+'_EN',prefix+'_DISCHARGE','ISO_3V3','GND2',page)
        mos('Q'+str(port+2),prefix+'_DISCHARGE','GND2',prefix+'_DISCHARGE_D',page)
        r('R'+str(116+port),'10kR',prefix+'_VBUS','GND2',page,'Passive VBUS discharge also works after complete board power loss')
        r('R'+str(78+port),'100R',prefix+'_VBUS',prefix+'_DISCHARGE_D',page,'VBUS discharge; pulse energy and decay verified in power report')
        for j in range(4):c('C'+str(99+4*(port-3)+j),'100nF','ISO_3V3','GND2',page,ctref+' and port logic bypass '+str(j+1))

# VBUS transient clamps. These suppress ESD, not sustained input overvoltage.
for ref,rail,gnd,page in [('D1','VBUS_HOST','GND1','host'),('D5','EXT_5V','GND2','external'),
                         ('D8','PORT1_VBUS','GND2','ports_a'),('D9','PORT2_VBUS','GND2','ports_a'),
                         ('D10','PORT3_VBUS','GND2','port_c3'),('D13','PORT4_VBUS','GND2','port_c4')]:
    add(ref,'T6V0S5A-7','Device:D_Zener',{1:rail,2:gnd},page,'T6V0S5A-7','Diodes Incorporated','Diode_SMD:D_SOD-523',
        'Unidirectional TVS: physical cathode/band pad 1 to VBUS, anode pad 2 to ground')

# Source/local status indicators; all meanings are explicit, no ADI PGOOD remains.
for ref,rref,qref,control,rail,gnd,page in [
 ('D2','R9','Q2','HOST_PWR_OK','HOST_3V3','GND1','host'),
 ('D6','R29','Q3','EXT_SELECTED','ISO_3V3','GND2','distribution'),
 ('D7','R30','Q4','HOST_PRESENT','ISO_3V3','GND2','hub')]:
    r(rref,'3.3kR',rail,ref+'_A',page)
    add(ref,'GREEN','Device:LED',{1:ref+'_K',2:ref+'_A'},page,'LTST-C190KGKT','Lite-On','LED_SMD:LED_0603_1608Metric')
    mos(qref,control,gnd,ref+'_K',page)


from sourcing import assign
assign(PARTS)


if __name__ == '__main__':
    target=ROOT/'build/revc/design.json'; target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(PARTS,indent=2)+'\n')
    print(len(PARTS),'physical parts')
    for page in dict.fromkeys(p['page'] for p in PARTS.values()):
        print(page,sum(p['page']==page for p in PARTS.values()))
