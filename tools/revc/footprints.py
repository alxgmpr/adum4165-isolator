"""Build the Rev C project-local land library. Never modifies the original library.

Custom packages use manufacturer land drawings and the official KiCad tools.
Thermal vias are deliberately omitted: all vias and routing belong to Alex.
"""
from pathlib import Path
import sys
import uuid
import json
import hashlib
import shutil
from design import ROOT, PARTS
from sexpr import read, write, child, children, value, node as n, S

TOOLKIT=ROOT/'build/revc/kicad-library-tools'
sys.path[:0]=[str(TOOLKIT),str(TOOLKIT/'src')]
from KicadModTree import Footprint, FootprintType, Pad, Property, Text, Line, Rectangle, KicadFileHandler
from KicadModTree.util import RoundRadiusHandler

OUT=ROOT/'hub-lib.pretty'
SYS=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
PROVENANCE={}
MODELS=ROOT/'hub-lib.3dshapes'

def local_models():
    MODELS.mkdir(exist_ok=True)
    model_root=SYS.parent/'3dmodels'
    # Dimensioned envelopes for packages without a manufacturer STEP model.
    # These are explicitly not detailed lead/assembly models.
    envelopes={
      'TI_DP0028A-C02_HV_SSOP28_8.2mm_Clearance':(7.5,10.3,2.65),
      'Microchip_SQFN36_6x6mm_EP3.7mm':(6.1,6.1,1),
      'TI_RUX0012A_VQFN-HR12_2x2.5mm':(2,2.5,1),
      'TI_RYQ0021A_VQFN21_3x5mm':(5.1,3.1,1),
      'Coilcraft_XFL4020_4x4mm':(4.3,4.3,2.1),
      'TPS630701RNM_VQFN-HR-15':(3,2.5,1),
      'C_1210_3225Metric':(3.5,2.7,2.7),
      'Texas_X2QFN-12_1.6x1.6mm_P0.4mm':(1.7,1.7,.4),
      'USB_A_Wuerth_614004134726_Horizontal':(19.6,7.3,14.8),
    }
    frames={'Laird_Technologies_BMI-S-201-F_13.66x12.70mm':(12.8,13.76,2.67),
            'Laird_Technologies_BMI-S-209-F_29.36x18.50mm':(29.46,18.60,7.13)}
    aliases={
      'Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm':model_root/'Package_SON.3dshapes/WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm.step',
      'USB_C_Receptacle_HRO_TYPE-C-31-M-12':MODELS/'HRO.step',
    }
    for file in OUT.glob('*.kicad_mod'):
        f=read(file)
        for m in children(f,'model'):
            if file.stem in envelopes or file.stem in frames:continue
            src=Path(m[1].replace('${KICAD10_3DMODEL_DIR}',str(model_root)).replace('${KIPRJMOD}',str(ROOT)))
            if file.stem in aliases:src=aliases[file.stem]
            if not src.exists() and m[1].startswith('${KICAD10_3DMODEL_DIR}'):
                src=MODELS/src.name
            assert src.exists(),src
            dst=MODELS/src.name
            if src!=dst:shutil.copyfile(src,dst)
            m[1]='${KIPRJMOD}/hub-lib.3dshapes/'+dst.name
            if file.stem=='WE_750313638':
                child(child(m,'rotate'),'xyz')[1:]=[-90,0,0]
                child(child(m,'offset'),'xyz')[1:]=[-6.120114543,8.591146647,-3.475710646]
            if file.stem=='USB_C_Receptacle_HRO_TYPE-C-31-M-12':
                child(child(m,'rotate'),'xyz')[1:]=[-90,0,0]
                child(child(m,'offset'),'xyz')[1:]=[-4.47,-3.65,0]
            if file.stem=='C_Disc_D7.0mm_W5.5mm_P14.00mm':
                # Model body is centered on Z=0; raise it clear of the board.
                # Long as-supplied leads remain visible and must be trimmed.
                child(child(m,'offset'),'xyz')[1:]=[7,0,4]
        if file.stem in envelopes:
            f[:]=[x for x in f if not(isinstance(x,list) and str(x[0])=='model')]
            x,y,z=envelopes[file.stem];cx=-2.68 if file.stem.startswith('USB_A_') else 0
            # KiCad VRML model units are 0.1 inches.
            wrl='#VRML V2.0 utf8\n# Dimensioned body envelope; not a detailed assembly model.\n'
            wrl+=f'Transform {{ translation {cx/2.54:.8f} 0 {z/5.08:.8f} children [ Shape {{ appearance Appearance {{ material Material {{ diffuseColor 0.20 0.21 0.24 }} }} geometry Box {{ size {x/2.54:.8f} {y/2.54:.8f} {z/2.54:.8f} }} }} ] }}\n'
            dst=MODELS/(file.stem+'.wrl');dst.write_text(wrl)
            f.append(n('model','${KIPRJMOD}/hub-lib.3dshapes/'+dst.name,n('offset',n('xyz',0,0,0)),n('scale',n('xyz',1,1,1)),n('rotate',n('xyz',0,0,0))))
        if file.stem in frames:
            f[:]=[x for x in f if not(isinstance(x,list) and str(x[0])=='model')]
            x,y,z=frames[file.stem];wrl='#VRML V2.0 utf8\n# Open-frame dimensional envelope; cover shown separately in assembly review.\n'
            for dx,dy,w,h in [(-x/2+.1,0,.2,y),(x/2-.1,0,.2,y),(0,-y/2+.1,x,.2),(0,y/2-.1,x,.2)]:
                wrl+=f'Transform {{ translation {dx/2.54:.8f} {dy/2.54:.8f} {z/5.08:.8f} children [ Shape {{ appearance Appearance {{ material Material {{ diffuseColor 0.7 0.7 0.7 }} }} geometry Box {{ size {w/2.54:.8f} {h/2.54:.8f} {z/2.54:.8f} }} }} ] }}\n'
            dst=MODELS/(file.stem+'.wrl');dst.write_text(wrl)
            f.append(n('model','${KIPRJMOD}/hub-lib.3dshapes/'+dst.name,n('offset',n('xyz',0,0,0)),n('scale',n('xyz',1,1,1)),n('rotate',n('xyz',0,0,0))))
        write(file,f)
    (ROOT/'docs/revc/body-envelopes.json').write_text(json.dumps({'bodies':envelopes,'frames':frames,'notes':'Dimensioned review envelopes; connector datum and covered-frame volumes are independently checked in placement review. Not manufacturer assembly STEP models.'},indent=2)+'\n')

def base(name,body,court,source):
    f=Footprint(name,FootprintType.SMD,tstamp_seed=uuid.uuid5(uuid.NAMESPACE_URL,name))
    f.setDescription(source+'; no thermal vias; see docs/revc/footprint-verification.md')
    f.append(Property('Reference','REF**',at=[0,-court[1]/2-.8],layer='F.SilkS'))
    f.append(Property('Value',name,at=[0,court[1]/2+.8],layer='F.Fab'))
    f.append(Text('${REFERENCE}',at=[0,0],layer='F.Fab',size=[.7,.7],thickness=.1))
    f.append(Rectangle(layer='F.Fab',width=.1,center=[0,0],size=body))
    f.append(Rectangle(layer='F.CrtYd',width=.05,center=[0,0],size=court))
    # Two corner marks outside copper, with the longer mark at pin 1.
    f.append(Line(start=[-court[0]/2,-court[1]/2],end=[-court[0]/2+.5,-court[1]/2],layer='F.SilkS',width=.12))
    f.append(Line(start=[-court[0]/2,-court[1]/2],end=[-court[0]/2,-court[1]/2+.5],layer='F.SilkS',width=.12))
    PROVENANCE[name]={'source':source,'body_mm':body,'courtyard_mm':court,'origin':'manufacturer drawing, KicadModTree'}
    return f

def pad(f,num,x,y,w,h,layers=None):
    f.append(Pad(number=str(num),type=Pad.TYPE_SMT,shape=Pad.SHAPE_ROUNDRECT,at=[x,y],size=[w,h],
        layers=layers or Pad.LAYERS_SMT,round_radius_handler=RoundRadiusHandler(radius_ratio=min(.25,.05/min(w,h)),maximum_radius=.05)))

def save(f): KicadFileHandler(f).writeFile(str(OUT/(f.name+'.kicad_mod')))

def placement_silk():
    # Retain exact copper/Fab geometry. Connector bodies intentionally overhang
    # the board by 0.5 mm; keep their ink inside that defined board edge.
    for name,axis,limit,lower in [('USB_C_Receptacle_HRO_TYPE-C-31-M-12',1,2.9,False),
            ('USB_A_Wuerth_614004134726_Horizontal',0,-11.58,True)]:
        path=OUT/(name+'.kicad_mod');f=read(path);remove=[]
        for a in children(f,'fp_line'):
            if value(a,'layer')!='F.SilkS':continue
            start=child(a,'start');end=child(a,'end');i=axis+1
            outside=lambda p:p[i]<limit if lower else p[i]>limit
            if outside(start) and outside(end):remove.append(a)
            elif outside(start) or outside(end):
                p,q=(start,end) if outside(start) else (end,start)
                t=(limit-q[i])/(p[i]-q[i]);j=2 if i==1 else 1
                p[j]=round(q[j]+t*(p[j]-q[j]),6);p[i]=limit
        for a in remove:f.remove(a)
        write(path,f);PROVENANCE[name]['silkscreen_adjustment']='Clipped mating end to provisional board edge; copper/Fab unchanged'
    name='TPS630701RNM_VQFN-HR-15';path=OUT/(name+'.kicad_mod');f=read(path)
    f[:]=[a for a in f if not(isinstance(a,list) and str(a[0])=='fp_rect' and value(a,'layer')=='F.SilkS')]
    f.append(n('fp_circle',n('center',-2.2,1.95),n('end',-2.1,1.95),n('stroke',n('width',.12),n('type',S('default'))),n('fill',S('yes')),n('layer','F.SilkS')))
    write(path,f);PROVENANCE[name]['silkscreen_adjustment']='Replaced pad-crossing body rectangle with pin-1 dot; copper/Fab unchanged'

def custom():
    f=base('Microchip_SQFN36_6x6mm_EP3.7mm',[6.1,6.1],[7,7],
        'Microchip DS00001692E p48 M2 SQFN36: 0.5 pitch; 0.28x0.90 lands, 4.65 inner gap, 3.70 EP')
    for i in range(9):
        v=(i-4)*.5
        pad(f,1+i,-2.775,v,.9,.28)
        pad(f,10+i,v,2.775,.28,.9)
        pad(f,19+i,2.775,-v,.9,.28)
        pad(f,28+i,-v,-2.775,.28,.9)
    pad(f,37,0,0,3.7,3.7,['F.Cu','F.Mask'])
    # Nine separated apertures: 69% paste coverage; thermal vias are a routing task.
    for x in [-1.15,0,1.15]:
        for y in [-1.15,0,1.15]:pad(f,'',x,y,1.025,1.025,['F.Paste'])
    save(f)
    f=base('TI_RUX0012A_VQFN-HR12_2x2.5mm',[2,2.5],[2.9,3.4],
        'TI TPS2121 SLVSEA3F p39 RUX0012A 4224010/A: 1.05x0.4 power lands and 0.2x0.6 signal lands')
    for num,x,y in [(1,-.675,-.35),(2,-.675,.35),(7,.675,.35),(8,.675,-.35)]:pad(f,num,x,y,1.05,.4)
    for i,x in enumerate([-.75,-.25,.25,.75]):
        pad(f,3+i,x,1.15,.2,.6);pad(f,12-i,x,-1.15,.2,.6)
    save(f)
    f=base('TI_RYQ0021A_VQFN21_3x5mm',[5.1,3.1],[5.9,3.9],
        'TI TPS552892 SLVSH28A p33-34 RYQ0021A 4226658/A; five full-height power lands, stepped PGND; segmented paste')
    for i,y in enumerate([-.75,-.25,.25,.75]):
        pad(f,1+i,-2.4,y,.6,.25);pad(f,17-i,2.4,y,.6,.25)
    for num,x,y,h in [(5,-2.04,1.375,.65),(6,-1.54,1.4,.6),(12,1.54,1.4,.6),(13,2.04,1.375,.65),
                       (21,-2.04,-1.375,.65),(20,-1.54,-1.4,.6),(19,1.54,-1.4,.6),(18,2.04,-1.375,.65)]:pad(f,num,x,y,.25,h)
    for num,x in [(7,-1.04),(8,-.54),(9,0),(10,.54),(11,1.04)]:
        pad(f,num,x,0,.25,3.4,['F.Cu','F.Mask'])
        if num==9:pad(f,num,x,0,.33,2.35,['F.Cu','F.Mask'])
        for y in [-1.2,0,1.2]:pad(f,'',x,y,.25,1,['F.Paste'])
    save(f)
    f=base('Coilcraft_XFL4020_4x4mm',[4.3,4.3],[4.9,4.8],
        'Coilcraft XFL4020 document 745-3 2026-03-10: 0.98x2.37 lands on 3.40 centers; maximum body 4.3x4.3x2.1')
    pad(f,1,-1.7,0,.98,2.37);pad(f,2,1.7,0,.98,2.37);save(f)

def main():
    OUT.mkdir(exist_ok=True)
    custom()
    for p in PARTS.values():
        lib,name=p['source_footprint'].split(':')
        dst=OUT/(name+'.kicad_mod')
        if lib=='hub-lib':
            assert dst.exists(),(p['ref'],name)
            continue
        src=(ROOT/(lib+'.pretty') if lib=='isolator-lib' else SYS/(lib+'.pretty'))/(name+'.kicad_mod')
        assert src.exists(),src
        dst.write_bytes(src.read_bytes())
        PROVENANCE[name]={'source':str(src.relative_to(ROOT)) if lib=='isolator-lib' else f'KiCad 10.99 stock {lib}:{name}',
            'origin':'unchanged copy','sha256':hashlib.sha256(src.read_bytes()).hexdigest()}
    # Bare PCB mechanical features; no purchased component is implied.
    for lib,name in [('MountingHole','MountingHole_3.2mm_M3'),('Fiducial','Fiducial_1mm_Mask2mm')]:
        src=SYS/(lib+'.pretty')/(name+'.kicad_mod');(OUT/src.name).write_bytes(src.read_bytes())
        PROVENANCE[name]={'source':f'KiCad 10.99 stock {lib}:{name}','origin':'unchanged copy','sha256':hashlib.sha256(src.read_bytes()).hexdigest()}
    for p in PARTS.values():
        f=read(OUT/(p['footprint'].split(':')[1]+'.kicad_mod'))
        pads={str(q[1]) for q in children(f,'pad') if q[1]!=''}
        # USB connector shields use S1 in the stock land but SH on stock USB_A.
        missing={k for k,v in p['pins'].items() if v is not None}-pads
        assert not missing,(p['ref'],'symbol pins not present in land',missing,pads)
        assert not children(f,'via'),p['ref']
    local_models()
    placement_silk()
    (ROOT/'docs/revc/footprint-provenance.json').write_text(json.dumps(PROVENANCE,indent=2)+'\n')
    print(f'Assigned {len(PARTS)} components; {len(list(OUT.glob("*.kicad_mod")))} project-local footprints')

if __name__=='__main__':main()
