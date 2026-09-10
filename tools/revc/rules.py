"""Set stackup-based routing defaults and explicit two-domain isolation rules."""
import json,xml.etree.ElementTree as ET
from copy import deepcopy
from design import ROOT,PARTS
root=ET.parse(ROOT/'build/revc/hub.xml').getroot()
primary_refs={r for r,p in PARTS.items() if p['page']=='host'}|{'U5','C10','C11','C12','SH1'}
def domain(ref,pin):
 if ref=='U1':return 'Primary' if int(pin)<=14 else 'Secondary'
 if ref=='T1':return 'Primary' if int(pin)<=3 else 'Secondary'
 if ref=='CY1':return 'Primary' if pin=='1' else 'Secondary'
 p=PARTS[ref]
 if p['page']=='isolation':
  if 'GND1' in p['pins'].values() or any(v and v in ['U1_3V3_HOST','U1_1V8_HOST','ISO_SIDE_OK'] for v in p['pins'].values()):return 'Primary'
 return 'Primary' if ref in primary_refs else 'Secondary'
domains={};errors=[]
for net in root.find('nets'):
 ds={domain(n.attrib['ref'],n.attrib['pin']) for n in net.findall('node')}
 if len(ds)!=1:errors.append((net.attrib['name'],sorted(ds)))
 else:domains[net.attrib['name']]=ds.pop()
assert not errors,errors
path=ROOT/'hub.kicad_pro';j=json.loads(path.read_text());base=deepcopy(j['net_settings']['classes'][0]);base.update(clearance=.15,track_width=.2,diff_pair_width=.136,diff_pair_gap=.15,diff_pair_via_gap=.25,via_diameter=.6,via_drill=.3)
classes=[base]
for priority,name,width in [(0,'USB90',.136),(1,'Power',1.0),(2,'Primary',.2),(3,'Secondary',.2)]:
 c=deepcopy(base);c.update(name=name,priority=priority,track_width=width);classes.append(c)
power={'VBUS_HOST','HOST_CONVERTER_5V','EXT_5V','EXT_SENSED_5V','EXT_SW_5V','EXT_REG_5V','DCDC_RAW','ISO_5V_PRE','ISO_5V','EXT_PORT_FEED','PORT_SUPPLY','ISO_3V3','U1_1V8_HOST',*[f'PORT{i}_VBUS' for i in range(1,5)]}
patterns=[]
for net,domain in sorted(domains.items()):
 patterns.append(dict(netclass=domain,pattern=net))
 if net.endswith(('_D+','_D-')):patterns.append(dict(netclass='USB90',pattern=net))
 if net in power:patterns.append(dict(netclass='Power',pattern=net))
j['net_settings'].update(classes=classes,netclass_patterns=patterns,netclass_assignments={})
rules=j['board']['design_settings']['rules'];rules.update(min_clearance=.15,min_track_width=.125,min_copper_edge_clearance=.5,min_silk_clearance=.1)
for check in ['missing_courtyard','footprint_filters_mismatch','footprint_type_mismatch','track_not_centered_on_via','tuning_profile_track_geometries']:
 j['board']['design_settings']['rule_severities'][check]='warning'
path.write_text(json.dumps(j,indent=2)+'\n')
(ROOT/'docs/revc/reports/net-domains.json').write_text(json.dumps(domains,indent=2)+'\n')
(ROOT/'hub.kicad_dru').write_text('''(version 1)
# Nominal JLC04161H-3313, 90 ohm differential target. See routing guide.
(rule "USB pair geometry"
  (condition "A.hasNetclass('USB90')")
  (constraint track_width (opt 0.136mm))
  (constraint diff_pair_gap (opt 0.15mm))
  (constraint diff_pair_uncoupled (max 5mm))
  (constraint skew (max 0.25mm) (within_diff_pairs))
  (constraint length (max 80mm)))
(rule "Isolation barrier: independent ground domains"
  (condition "(A.hasNetclass('Primary') && B.hasNetclass('Secondary')) || (A.hasNetclass('Secondary') && B.hasNetclass('Primary'))")
  (constraint clearance (min 8.30mm))
  (constraint creepage (min 8.30mm)))
# Exact TI DP0028A-C02 HV land pattern: 8.20 mm nominal copper gap.
# This is a local manufacturer geometry, not a blanket board safety rating.
(rule "ISOUSB211 manufacturer HV lands"
  (condition "A.memberOfFootprint('U1') && B.memberOfFootprint('U1') && ((A.hasNetclass('Primary') && B.hasNetclass('Secondary')) || (A.hasNetclass('Secondary') && B.hasNetclass('Primary')))")
  (constraint clearance (min 8.20mm))
  (constraint creepage (min 8.20mm)))
''')
print('Assigned',len(domains),'nets to independent isolation domains; six USB pairs configured.')
