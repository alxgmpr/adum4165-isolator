"""Review renders only; never exports fabrication or assembly files."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,os,argparse
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/revc/renders'
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
def run(args):
 subprocess.run([CLI,*args],cwd=ROOT,check=True)
def png(path):
 import cairosvg
 path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
 cairosvg.svg2png(url=str(path),write_to=str(path.with_suffix('.png')),output_width=3600)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('kind',choices=['schematic','pcb']);a=parser.parse_args()
 if a.kind=='schematic':
  run(['sch','export','svg','-o',str(OUT/'schematic'),'hub.kicad_sch'])
  run(['sch','export','pdf','-o',str(OUT/'schematic.pdf'),'hub.kicad_sch'])
  for path in sorted((OUT/'schematic').glob('*.svg')):png(path);print(path.name,flush=True)
 else:
  for name,layers,extra in [('placement-top','F.Cu,F.Fab,F.SilkS,Edge.Cuts,Dwgs.User',[]),('placement-bottom','B.Cu,B.Fab,B.SilkS,Edge.Cuts,Dwgs.User',['--mirror']),('placement-courtyards','F.Cu,F.CrtYd,Edge.Cuts,Dwgs.User',[])]:
   path=OUT/(name+'.svg')
   run(['pcb','export','svg','--mode-single','--layers',layers,'--fit-page-to-board','--exclude-drawing-sheet','-o',str(path),*extra,'hub.kicad_pcb']);png(path)
  commands=[]
  for name,side,rot in [('pcb-3d-top','top',None),('pcb-3d-isometric','top','-35,0,25'),('pcb-3d-bottom','bottom',None)]:
   cmd=['pcb','render','--width','2200','--height','1800','--quality','high','--background','opaque','--side',side,'--zoom','1.08','-o',str(OUT/(name+'.png'))]
   if rot:
    cmd[cmd.index('--zoom')+1]='0.80'
    cmd+=['--rotate',rot]
   commands.append(cmd+['hub.kicad_pcb'])
  with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(run,commands))
if __name__=='__main__':main()
