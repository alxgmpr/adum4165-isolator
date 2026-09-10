"""Generate ISOUSB211 symbol and exact TI HV lands using KiCad Library Tools.

Run with the repository's Rev C venv. Clone the official KiCad library tools to
build/revc/kicad-library-tools first. Nothing in the single-port library is edited.
"""
from pathlib import Path
import json
import sys
import uuid

from sexpr import node as n, S, write

ROOT = Path(__file__).resolve().parents[2]
TOOLKIT = ROOT / 'build/revc/kicad-library-tools'
sys.path[:0] = [str(TOOLKIT), str(TOOLKIT / 'src')]
from KicadModTree import Footprint, FootprintType, Pad, Property, Text, Line, Rectangle, KicadFileHandler
from KicadModTree.util import RoundRadiusHandler

spec = json.loads((ROOT / 'tools/revc/isousb211.json').read_text())
name = 'ISOUSB211DPR'
fpname = 'TI_DP0028A-C02_HV_SSOP28_8.2mm_Clearance'
footprints = ROOT / 'hub-lib.pretty'
footprints.mkdir(exist_ok=True)
fp = Footprint(fpname, FootprintType.SMD, tstamp_seed=uuid.uuid5(uuid.NAMESPACE_URL, fpname))
fp.setDescription('TI ISOUSB211 DP0028A-C02 HV/isolation option; drawing 4231707/A p40; 8.20 mm nominal pad clearance, 0.65 mm pitch')
fp.setTags(['ISOUSB211', 'isolation', 'HV', 'SSOP28'])
fp.append(Property('Reference', 'REF**', at=[0, -6.2], layer='F.SilkS'))
fp.append(Property('Value', name, at=[0, 6.2], layer='F.Fab'))
fp.append(Text('${REFERENCE}', at=[0, 0], layer='F.Fab'))
fp.append(Rectangle(layer='F.Fab', width=0.1, center=[0, 0], size=[7.5, 10.3]))
fp.append(Rectangle(layer='F.CrtYd', width=0.05, start=[-6, -5.65], end=[6, 5.65]))
for y in (-5.3, 5.3):
    fp.append(Line(start=[-3.9, y], end=[3.9, y], layer='F.SilkS', width=0.12))
fp.append(Line(start=[-3.9, -5.3], end=[-3.9, -4.8], layer='F.SilkS', width=0.12))
fp.append(Line(start=[-3.75, -4.15], end=[-2.75, -5.15], layer='F.Fab', width=0.1))
for number in range(1, 29):
    left = number <= 14
    y = ((number - 1) if left else (28 - number)) * 0.65 - 4.225
    fp.append(Pad(number=number, type=Pad.TYPE_SMT, shape=Pad.SHAPE_ROUNDRECT,
                  at=[-4.925 if left else 4.925, y], size=[1.65, 0.45],
                  layers=Pad.LAYERS_SMT, round_radius_handler=RoundRadiusHandler(radius_ratio=0.05 / 0.45, maximum_radius=0.05)))
KicadFileHandler(fp).writeFile(str(footprints / (fpname + '.kicad_mod')))

def effects(size=1.27, hide=False):
    return n('effects', n('font', n('size', size, size)), *([n('hide', S('yes'))] if hide else []))

symbol = n('symbol', name, n('pin_names', n('offset', 1.016)),
           n('exclude_from_sim', S('no')), n('in_bom', S('yes')), n('on_board', S('yes')))
for key, val, y, hide in [('Reference', 'U', 20.32, False), ('Value', name, 17.78, False),
                          ('Footprint', 'hub-lib:' + fpname, 0, True),
                          ('Datasheet', spec['source'], 0, True),
                          ('Description', '480 Mbps isolated USB transceiver, DP28; 5V/3.3V selected supply configuration', 0, True),
                          ('ki_keywords', 'USB high speed isolation TI', 0, True),
                          ('ki_fp_filters', 'TI_DP0028A-C02_HV*', 0, True)]:
    symbol.append(n('property', key, val, n('at', 0, y, 0), effects(hide=hide)))
body = n('symbol', name + '_0_1', n('rectangle', n('start', -17.78, 15.24),
         n('end', 17.78, -53.34), n('stroke', n('width', 0), n('type', S('default'))),
         n('fill', n('type', S('background')))))
body.append(n('polyline', n('pts', n('xy', 0, 15.24), n('xy', 0, -53.34)),
              n('stroke', n('width', 0.254), n('type', S('dash'))), n('fill', n('type', S('none')))))
symbol.append(body)
pins = n('symbol', name + '_1_1')
for number, pin_name, kind, net in spec['pins']:
    num = int(number); left = num <= 14
    row = num - 1 if left else 28 - num
    pins.append(n('pin', S(kind), S('line'), n('at', -22.86 if left else 22.86, 12.7 - row * 5.08, 0 if left else 180),
                  n('length', 5.08), n('name', pin_name, effects()), n('number', number, effects())))
symbol.append(pins)
write(ROOT / 'hub-isolator.kicad_sym', n('kicad_symbol_lib', n('version', 20250114), n('generator', 'kicad_symbol_editor'), symbol))
print(f'Generated {name}: 28 pins, {fpname}: 28 pads, 8.200 mm nominal clearance')
