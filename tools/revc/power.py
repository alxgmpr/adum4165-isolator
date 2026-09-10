"""Rev C reproducible DC/tolerance budget and averaged-loop screening.

Efficiency and ceramic DC-bias retention are explicit design assumptions, not
manufacturer guarantees. Hardware acceptance checks are in the bring-up guide.
"""
import json,csv,math,hashlib
from itertools import product
from pathlib import Path
import numpy as np
from design import ROOT,PARTS
OUT=ROOT/'docs/revc';REPORT=OUT/'reports'
loads=[('USB2514B',155,'Microchip maximum: 80 + 3 x 25 mA'),('ISOUSB211 side 2',109.5,'TI zero-EQ HS maxima: 13.5 + 96 mA'),
 ('Type-C controllers, gates, monitors, reset, EEPROM, pullups and indicators',25.5,'Conservative combined allowance; not a measured load')]
i33=sum(row[1] for row in loads)/1000
eta33=.85;core5=3.3*i33/(4.75*eta33)+.010
# Comparator trip bounds: current-source full-temperature limits, precision
# resistor tolerance/drift, shunt tolerance/TCR and offset/PSRR allowances.
def current_trip(r,shunt,tc,fast=False):
 tol=.001+tc*60e-6;stol=.01+75*60e-6
 offset=.00065 if fast else .00050
 psrr=.00015*.6;naf=.0005 if fast else 0
 lo=(19.85e-6*r*(1-tol)-naf-offset-psrr)/(shunt*(1+stol))
 hi=(20.15e-6*r*(1+tol)-naf+offset+psrr)/(shunt*(1-stol))
 return {'nominal_A':(20e-6*r-naf)/shunt,'minimum_A':lo,'maximum_A':hi}
trip_in=current_trip(2870,.02,25);trip_ports=current_trip(1100,.01,10,True)
# Reference +/-1% and resistor 0.1% + 10ppm/C over a 60C excursion.
def setpoint(sign):
 t=.001+10e-6*60;top=10000*(1+sign*t);bottom=3000*(1-sign*t)+(.05 if sign<0 else 0)
 # FB leakage +/-100nA plus CDC sink 0..300nA; use Rtop, not Rparallel.
 return 1.2*(1+sign*.01)*(1+top/bottom)+(-.001 if sign<0 else .00401)
vout_nom=1.2*(1+10000/3000);vout_lo=setpoint(-1);vout_hi=setpoint(1)
# Efficiencies below include converter stages but not the connector-to-converter
# series path. Use the minimum guaranteed current trip, and include switch,
# shunt and 10mOhm routed input resistance before multiplying by efficiency.
input_r=.031+.02029+.010
host_input_r=.135+.010
rows=[]
for vin in [4.25,4.5,4.75,5.0,5.25]:
 for eff in [.70,.75,.80]:
  available=max(0,(vin*.825-.825**2*host_input_r)*eff-(3.3*i33/eta33+.05))/5
  rows.append(['Host',vin,eff,min(.3,available),available])
 for eff in [.85,.90,.93]:
  available=max(0,(vin*trip_in['minimum_A']-trip_in['minimum_A']**2*input_r)*eff/vout_hi-core5)
  rows.append(['External',vin,eff,min(2.0,trip_ports['minimum_A'],available),available])
with (OUT/'power-operating-envelope.csv').open('w') as f:
 w=csv.writer(f,lineterminator="\n");w.writerow(['Source','Connector voltage V','Assumed conversion efficiency','Permitted design load A','Power-limited load before cap A']);w.writerows(rows)
# Thermal voltage-drop calculation includes 85C TPS2121 max Ron, full-temp
# TPS22975/2553 maxima, shunt and 15mV complete routed path allowance.
port_vmin=vout_lo-(2+core5)*.085-2*.031-2*.010145-.5*.135-.015-.020
port_max=vout_hi+.020 # design ripple budget; must be measured
# A conservative full-load input threshold uses high regulator setpoint and
# low-voltage core current simultaneously, although these corners do not align.
ext_required_vin=vout_hi*(2+core5)/(.90*trip_in['minimum_A'])+trip_in['minimum_A']*input_r
# Capacitor retention includes tolerance, temperature, ageing and assumed DC bias.
# Manufacturer product pages give nominal/tolerance/rating; DC bias is a bench gate.
cap_min=22e-6*.90*.85*.95*.80
cap_max=22e-6*1.10*1.15
rmin=69000*(1-.01-.006);rmax=69000*(1+.01+.006)
# Use Schmitt thresholds spanning TI's 3V and 4.5V rows to cover 3.0..3.6V.
# Signed input leakage and FAULT VOL push both limits conservatively.
final_fast=-5e-6*68000*(1+.016)
final_slow=.18+5e-6*68000*(1+.016)
delay_min=cap_min*rmin*math.log((3.0-final_fast)/(1.97-final_fast))
delay_max=cap_max*rmax*math.log((3.6-final_slow)/(.89-final_slow))
startup={'C116_effective_min_uF':cap_min*1e6,'bus_fault_delay_min_s':delay_min,'bus_fault_delay_max_s':delay_max,
 'bus_reservoir_charge_s_at_600uF_5_5V_300mA_load':600e-6*5.5/(.312-.3),
 'host_direct_cap_nominal_uF':6.9,'host_direct_cap_positive_tolerance_uF':6.9*1.1,
 'type_c_discharge_active_s_13uF_101ohm_5_5_to_0_8':13e-6*101*math.log(5.5/.8),
 'type_c_discharge_passive_s_13uF_10k1_5_5_to_0_8':13e-6*10100*math.log(5.5/.8),
 'U27_typical_rise_s_at_5V':(0.43*10000+26)*5e-6,
 'U30_typical_rise_s_at_5_2V':(0.43*22000+26)*5.2e-6}
assert delay_min>startup['bus_reservoir_charge_s_at_600uF_5_5V_300mA_load']+.003
host={'HS_A_at_4V_and_75pct_core_eff':.0135+1.8*.096/(4*.75)+.003,
 'L2_A_at_4V_60pct_core_eff_and_0_50mA_controls':.00155+1.8*.00055/(4*.60)+.00050,
 'qualified_max_A':.990+.0135+1.8*.096/(4*.75)+.003,
 'controls_note':'3mA active and 0.50mA L2 are conservative allowances; buck light-load efficiency and complete suspend current require measurement.'}
# Worst loss estimate (actual temperature rise depends on the routed PCB).
losses={'U8_W':(2+core5)**2*.085,'U30_W':2**2*.031,'R116_W':2**2*.010145,'each_port_switch_W':.5**2*.135,
 'R110_W':3**2*.02029,'U28_at_90pct_W':(vout_nom*2+3.3*i33/eta33)*(1/.90-1),'U10_at_85pct_W':3.3*i33*(1/.85-1)}
# TI equations 19-26: ideal averaged boost plant and physical compensation
# impedance. Finite error-amplifier Ro is swept, since no guaranteed Ro is
# published. ESR, Ceff and load bounds include reflected downstream reservoirs.
f=np.logspace(0,6,10000);s=2j*np.pi*f;out=[]
for vin,load,cap,esr,ro in product([4.0,4.25,4.75,5.25],[.25,1.0,2.3],[38e-6,88e-6,300e-6,900e-6],[.003,.03,.30],[1e5,1e6,1e7]):
 v=vout_nom;one_d=min(1,vin/v);rl=v/load;rs=.055;L=4.7e-6;rc=2700;cc=220e-9;cp=100e-12
 fp=2/(2*np.pi*rl*cap);fz=1/(2*np.pi*esr*cap);frhp=rl*one_d**2/(2*np.pi*L)
 gps=rl*one_d/(2*rs)*(1+s/(2*np.pi*fz))*(1-s/(2*np.pi*frhp))/(1+s/(2*np.pi*fp))
 zc=1/(1/ro+s*cp+1/(rc+1/(s*cc)));loop=gps*.000190*zc*1.2/v
 gain=20*np.log10(abs(loop));phase=np.unwrap(np.angle(loop))*180/np.pi
 crosses=np.flatnonzero((gain[:-1]>=0)&(gain[1:]<0));idx=crosses[0] if len(crosses) else 0
 phase_cross=np.flatnonzero((phase[:-1]>-180)&(phase[1:]<=-180));gm=float(-gain[phase_cross[0]]) if len(phase_cross) else None
 out.append(dict(vin=vin,load_A=load,Ceff_uF=cap*1e6,ESR_ohm=esr,Ro_ohm=ro,fc_Hz=float(f[idx]),phase_margin_deg=float(180+phase[idx]),gain_margin_dB=gm,fc_limit_Hz=min(40000,frhp/5)))
summary={'core_3V3_mA':i33*1000,'core_5V_A_at_4_75V':core5,'U46_input_trip':trip_in,'U47_port_trip':trip_ports,
 'ext_setpoint_V':{'nominal':vout_nom,'minimum':vout_lo,'maximum':vout_hi},'port_minimum_V_at_2A_and_mux_Tj_85C_with_20mV_ripple':port_vmin,'port_maximum_V_with_20mV_ripple':port_max,
 'losses':losses,'startup_and_inrush':startup,'host_budget':host,'external_min_connector_V_for_2A_at_90pct':ext_required_vin,'input_path_resistance_ohm':input_r,'loop_screen':{'corners':len(out),'minimum_phase_margin_deg':min(x['phase_margin_deg'] for x in out),'minimum_gain_margin_dB':min(x['gain_margin_dB'] for x in out if x['gain_margin_dB'] is not None),
 'maximum_fc_Hz':max(x['fc_Hz'] for x in out),'corners_above_TI_fc_limit':sum(x['fc_Hz']>x['fc_limit_Hz'] for x in out)},
 'limits':'DC calculation and ideal averaged-loop screening only. Efficiency, distributed capacitance, noise, transient response, thermal rise and physical USB compliance require hardware tests.'}
(REPORT/'power-calculations.json').write_text(json.dumps(summary,indent=2)+'\n');(REPORT/'loop-corners.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(summary,indent=2))
