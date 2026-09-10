"""Exact sourcing and footprint assignments applied to schematic source fields.

PCB test pads are manufactured features, explicitly excluded from purchase BOM.
No exported CSV is edited. Selected library geometries are copied to hub-lib.
"""
from pathlib import Path
import json
import math

ROOT=Path(__file__).resolve().parents[2]
CAPS={
 '100nF':('GRM155R71H104KE14D','0402','50V X7R 10%','C77020'),
 '10nF':('GRM155R71H103KA88D','0402','50V X7R 10%','C77019'),
 '22nF':('GRM155R71H223KA12D','0402','50V X7R 10%','C77023'),
 '220nF':('GRM155R71C224KA12D','0402','16V X7R 10%','C77011'),
 '1uF':('GRM188R61E105KA12D','0603','25V X5R 10%','C77046'),
 '4.7uF':('GRM188R61E475KE11D','0603','25V X5R 10%','C90057'),
 '10uF':('GRM21BR61E106KA73L','0805','25V X5R 10%','C84416'),
 '22uF':('GRM32ER71E226KE15L','1210','25V X7R 10%','C21397'),
 '27pF':('GCM1555C1H270JA16D','0402','50V C0G 5%','C126504'),
 '100pF':('GRM1555C1H101JA01D','0402','50V C0G 5%','C77177')
}
METRIC={'0402':'1005','0603':'1608','0805':'2012','1206':'3216','1210':'3225'}
IC_FP={
 'ISOUSB211DPR':'hub-lib:TI_DP0028A-C02_HV_SSOP28_8.2mm_Clearance',
 'TUSB320LAIRWBR':'Package_DFN_QFN:Texas_X2QFN-12_1.6x1.6mm_P0.4mm',
 'SN6505BDBVR':'Package_TO_SOT_SMD:SOT-23-6',
 'TPS630701RNMR':'isolator-lib:TPS630701RNM_VQFN-HR-15',
 'TPS2121RUXR':'hub-lib:TI_RUX0012A_VQFN-HR12_2x2.5mm',
 'TPS62162DSGR':'Package_SON:Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm',
 'USB2514B-I/M2':'hub-lib:Microchip_SQFN36_6x6mm_EP3.7mm',
 'TPS552892RYQR':'hub-lib:TI_RYQ0021A_VQFN21_3x5mm',
 'INA300AIDGSR':'Package_SO:MSOP-10_3x3mm_P0.5mm',
}
for mpn in ['TPS22975DSGR','TPS22975NDSGR']:
 IC_FP[mpn]='Package_SON:Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm'
for mpn in ['TPS2553DBVR','TPS2553DBVR-1','TPS3808G01DBVR','TPS3808G33DBVR']:
 IC_FP[mpn]='Package_TO_SOT_SMD:SOT-23-6'
for mpn in ['SN74LVC1G02DBVR','SN74LVC1G04DBVR','SN74LVC1G08DBVR','TLV75533PDBVR','TLV62568DBVR']:
 IC_FP[mpn]='Package_TO_SOT_SMD:SOT-23-5'
PRECISION={'R20','R21','R22','R64','R65','R111','R117'}
SOURCES={
 'TYPE-C-31-M-12':'https://datasheet.lcsc.com/datasheet/pdf/9e56b777c022540fcce7c7f67825f55e.pdf?productCode=C165948',
 'USBLC6-2SC6':'https://www.st.com/resource/en/datasheet/usblc6-2.pdf',
 'Q07F3Z102MA5B0S0N0':'https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2111091030_STE-Songtian-Elec-Q07F3Z102MA5B0S0N0_C2914611.pdf',
 '750313638':'https://www.we-online.com/components/products/datasheet/750313638.pdf',
 '614004134726':'https://www.we-online.com/components/products/datasheet/614004134726.pdf',
 'SS34':'https://www.lcsc.com/datasheet/C8678.pdf',
 'BAT54WS-7-F':'https://www.diodes.com/assets/Datasheets/BAT54WS.pdf',
 'BAT54C,215':'https://assets.nexperia.com/documents/data-sheet/BAT54_SER.pdf',
 '2N7002,215':'https://assets.nexperia.com/documents/data-sheet/2N7002.pdf',
 'T6V0S5A-7':'https://www.diodes.com/assets/Datasheets/T6V0S5A.pdf',
 'LTST-C190KGKT':'https://optoelectronics.liteon.com/upload/download/DS22-2000-213/LTST-C190KGKT.pdf',
 'USB2514B-I/M2':'https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/USB251xB-xBi-Data-Sheet-DS00001692.pdf',
 '24LC02B-I/SN':'https://ww1.microchip.com/downloads/en/DeviceDoc/21709c.pdf',
 'ABM8G-24.000MHZ-18-D2Y-T':'https://abracon.com/Resonators/abm8g.pdf',
 'XFL4020-152MEC':'https://www.coilcraft.com/getmedia/50632d43-da1b-4cdb-8ab4-3029cab51df3/xfl4020.pdf',
 'XFL4020-222MEC':'https://www.coilcraft.com/getmedia/50632d43-da1b-4cdb-8ab4-3029cab51df3/xfl4020.pdf',
 'XAL7070-472MEC':'https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xal/xal7070/',
}
for name in ['BMI-S-201-F','BMI-S-209-F']:
 SOURCES[name]='https://www.laird.com/products/custom-precision-metal-stamping-emi-non-emi/board-level-shields/two-piece-board-level-shields/'+name.lower()


def resistor_value(s):
    s=s.removesuffix('R')
    return float(s[:-1])*{'k':1e3,'m':1e-3}[s[-1]] if s[-1] in 'km' else float(s)


def eia(r):
    if r<100:return ('%.1f'%r).replace('.','R')
    exponent=int(math.floor(math.log10(r)))-2
    return str(round(r/10**exponent)).zfill(3)+str(exponent)


def yageo_value(r):
    if r>=1000:return ('%g'%(r/1000)).replace('.','K')+('K' if r%1000==0 else '')
    return ('%g'%r).replace('.','R')+('R' if r==int(r) else '')


def assign(parts):
    indexed={}
    for file in ['part-availability.json','passive-availability.json','supporting-availability.json','resistor-availability.json']:
        path=ROOT/'docs/revc'/file
        if not path.exists():continue
        for q in json.loads(path.read_text()).get('queries',[]):
            for row in q.get('result',{}).get('results',[]):indexed.setdefault(row['model'],[]).append(row)
    for ref,p in parts.items():
        p.setdefault('lcsc','')
        if ref.startswith('TP'):
            p.update(mpn='',manufacturer='PCB feature',exclude_bom=True,datasheet='',ratings='Exposed test pad; no purchased part')
            p['source_footprint']=p['footprint']
            p['footprint']='hub-lib:'+p['footprint'].split(':')[1]
            continue
        if ref.startswith('C') and ref!='CY1':
            if p['value']=='220uF':
                p.update(mpn='EEEFK1A221P',manufacturer='Panasonic Industry',lcsc='C401648',
                    footprint='Capacitor_SMD:CP_Elec_8x6.2',ratings='220uF 10V +/-20%; 8mm diameter, 6.5mm maximum height; polarized',
                    datasheet='https://industrial.panasonic.com/ww/products/pt/aluminum-cap-smd/models/EEEFK1A221P')
            else:
                mpn,package,rating,lcsc=CAPS[p['value']]
                if ref=='C113':mpn,package,rating,lcsc='GRM21BR61E475KA12L','0805','25V X5R 10%','C77077'
                p.update(mpn=mpn,manufacturer='Murata Manufacturing',lcsc=lcsc,ratings=rating,
                    footprint=f'Capacitor_SMD:C_{package}_{METRIC[package]}Metric',
                    datasheet='https://www.murata.com/en-global/products/productdetail?partno='+mpn[:-1]+'%23')
        elif ref.startswith('R'):
            rval=resistor_value(p['value']);package='0402'
            if rval==0:mpn='ERJ2GE0R00X';mfr='Panasonic Industry';rating='0R jumper, 0402, 1A rated current'
            elif ref in ['R110','R116']:
                mpn='WSLP1206R0200FEA' if ref=='R110' else 'WSLP1206R0100FEA';mfr='Vishay';package='1206';rating='1W, 1%, 75ppm/C; Kelvin sense'
            elif ref in PRECISION:
                mpn='RT0603BRB07'+yageo_value(rval)+'L';mfr='Yageo';package='0603';rating='0.1%, 10ppm/C thin film, 0.1W'
                if ref=='R111':mpn='RT0603BRD072K87L';rating='0.1%, 25ppm/C thin film, 0.1W'
            elif ref in ['R81','R82']:
                mpn='ERJ6ENF1000V';mfr='Panasonic Industry';package='0805';rating='100R 1%, 0.125W; 0.14mJ maximum discharge pulse'
            else:
                mpn='ERJ2RKF'+eia(rval)+'X';mfr='Panasonic Industry';rating='1%, 0.1W, 50V'
            p.update(mpn=mpn,manufacturer=mfr,ratings=rating,footprint=f'Resistor_SMD:R_{package}_{METRIC[package]}Metric')
            p['datasheet']={'Yageo':'https://www.yageo.com/upload/media/product/productsearch/datasheet/rchip/PYu-RT_51_RoHS_L.pdf',
                'Vishay':'https://www.vishay.com/docs/30122/wslp.pdf',
                'Panasonic Industry':'https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf'}[mfr]
        if p['mpn'] in IC_FP:p['footprint']=IC_FP[p['mpn']]
        if ref in ['L1','L2','L4']:p['footprint']='hub-lib:Coilcraft_XFL4020_4x4mm'
        if ref=='L3':p['footprint']='Inductor_SMD:L_Coilcraft_XAL7070-XXX'
        if ref=='Y2':p['footprint']='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm'
        if ref=='SH1':p['footprint']='RF_Shielding:Laird_Technologies_BMI-S-201-F_13.66x12.70mm'
        if ref=='SH2':p['footprint']='RF_Shielding:Laird_Technologies_BMI-S-209-F_29.36x18.50mm'
        if ref in ['SH1','SH2']:
            p['cover_mpn']=p['mpn'].removesuffix('-F')+'-C';p['cover_quantity']='1'
            p['ratings']='Separate grounded frame; removable '+p['cover_mpn']+' ordered separately; no inter-domain metal bridge'
        if p['mpn'] in SOURCES:p['datasheet']=SOURCES[p['mpn']]
        if p['mpn']=='SS34':p['lcsc']='C8678'
        if p['mpn']=='USBLC6-2SC6':p['lcsc']='C7519'
        if not p['lcsc']:
            rows=indexed.get(p['mpn'],[])
            if p['manufacturer']=='Texas Instruments':rows=[r for r in rows if r['manufacturer']=='Texas Instruments']
            if len(rows)==1:p['lcsc']=rows[0]['lcsc']
        if p['manufacturer']=='Texas Instruments':
            import re
            name=re.match(r'(ISOUSB\d+|TUSB\d+LAI|SN6505B|SN74LVC1G\d+|TPS\d+|TLV\d+|INA\d+)',p['mpn']).group(1).lower()
            if name=='tps630701':name='tps63070'
            if name=='tlv75533':name='tlv755p'
            p['datasheet']='https://www.ti.com/lit/ds/symlink/'+name+'.pdf'
        p.setdefault('ratings','See exact manufacturer datasheet')
        p.setdefault('datasheet','')
        assert p['mpn'],ref
        assert p['footprint'],ref
        p['source_footprint']=p['footprint']
        if not p['footprint'].startswith('hub-lib:'):
            lib,name=p['footprint'].split(':');p['footprint']='hub-lib:'+name
