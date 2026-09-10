"""Generate the USB2514B's 256-byte development EEPROM and annotated map.

This is configuration data, not firmware. Address map: DS00001692E section 5.
The Microchip default VID/PID are for this development prototype only.
"""
from pathlib import Path
import csv,hashlib,json
ROOT=Path(__file__).resolve().parents[2]
settings={
0x00:(0x24,'VID low: Microchip default development identity'),
0x01:(0x04,'VID high: 0x0424; obtain authorized identity before distribution'),
0x02:(0x14,'PID low: USB2514B default'),0x03:(0x25,'PID high: 0x2514'),
0x04:(0x00,'Device release low'),0x05:(0x03,'Device release high: 0x0300 Rev C'),
0x06:(0x1B,'HS enabled, multi-TT, EOP disabled, individual OC sensing and switching; bit7 ignored with dynamic power'),
0x07:(0x80,'Dynamic LOCAL_PWR switching enabled, 0.1ms additional hub OC debounce'),
0x08:(0x00,'Standard port map; string descriptors disabled'),
0x09:(0x00,'All ports removable'),0x0A:(0x00,'All four ports enabled with external power'),
0x0B:(0x00,'All four ports enabled with qualified bus power; shared load budget applies'),
0x0C:(0x32,'Self-powered upstream maximum 100mA including host-side isolator'),
0x0D:(0xFA,'Bus-powered controller/circuit maximum 500mA; Type-C current qualification required'),
0x0E:(0x32,'Self-powered hub-controller maximum 100mA'),
0x0F:(0xFA,'Bus-powered hub-controller maximum 500mA; not a promise of legacy bus-powered interoperability'),
0x10:(0xFA,'500ms port power-on interval in 2ms units'),
0xD0:(0x00,'Battery charging disabled on every port'),
0xFA:(0x00,'No upstream or downstream differential polarity swaps'),
0xFB:(0x00,'Port remapping disabled'),0xFC:(0x00,'Port remapping disabled'),
0xFF:(0x00,'SMBus-only status/attach register not used in EEPROM mode')}
b=bytearray(256)
for addr,(data,_) in settings.items():b[addr]=data
out=ROOT/'docs/revc/eeprom';out.mkdir(exist_ok=True)
(out/'hub-revc-development.bin').write_bytes(b)
with (out/'hub-revc-development.csv').open('w') as f:
 w=csv.writer(f,lineterminator="\n");w.writerow(['Address hex','Data hex','Meaning'])
 for a,v in enumerate(b):w.writerow([f'{a:02X}',f'{v:02X}',settings.get(a,(0,'Reserved/unused: zero'))[1]])
(out/'manifest.json').write_text(json.dumps({'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'source':'https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/USB251xB-xBi-Data-Sheet-DS00001692.pdf','status':'Development configuration; program/read back before first enumeration. Validate descriptors and host policy on hardware.'},indent=2)+'\n')
print('EEPROM: 256 bytes, SHA256',hashlib.sha256(b).hexdigest())
