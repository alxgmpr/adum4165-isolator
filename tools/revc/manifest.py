"""Hash the completed routing handoff without modifying design files."""
from pathlib import Path
import hashlib,json,platform,subprocess
from importlib.metadata import version
from sexpr import read,children
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/revc/reports/artifact-manifest.json'
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def main():
    assert git('branch','--show-current')=='codex/revc-isousb211'
    original=[p for p in git('ls-files','isolator*').splitlines() if p]
    subprocess.run(['git','diff','--exit-code','741e9b8','--',*original],cwd=ROOT,check=True)
    patterns=list((ROOT/'hub-lib.pretty').glob('*.kicad_mod'));models=set()
    for p in patterns:
        for m in children(read(p),'model'):
            model=Path(m[1].replace('${KIPRJMOD}',str(ROOT)))
            assert model.is_file(),model
            models.add(model)
    pdf_pages=len(PdfReader(ROOT/'docs/revc/renders/schematic.pdf').pages)
    assert pdf_pages==11
    drc=json.loads((ROOT/'docs/revc/reports/drc-final.json').read_text())
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks']
    assert len(drc['unconnected_items'])==499
    for filename,key in [('pcb-inventory-and-isolation.json','errors'),('electrical-invariants.json','errors')]:
        assert not json.loads((ROOT/'docs/revc/reports'/filename).read_text())[key]
    paths=set()
    for pattern in ['hub*.kicad_sch','hub*.kicad_sym','hub.kicad_pcb','hub.kicad_pro','hub.kicad_dru','sym-lib-table','fp-lib-table']:
        paths.update(ROOT.glob(pattern))
    for directory in ['docs/revc','tools/revc','hub-lib.pretty']:
        paths.update(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.update(models);paths.discard(OUT)
    manifest={
        'revision':'C','scope':'Verified schematic and placed unrouted handoff; all hardware tests pending',
        'baseline':'741e9b8','branch':git('branch','--show-current'),
        'checkpoint_before_final_handoff':git('rev-parse','HEAD'),
        'tools':{'KiCad':subprocess.check_output([CLI,'--version'],text=True).strip(),
                 'Python':platform.python_version(),**{p:version(p) for p in ['sexpdata','shapely','numpy','matplotlib','CairoSVG','Pillow','pypdf']}},
        'inventory':{'local_footprints':len(patterns),'referenced_local_models':len(models),'schematic_pdf_pages':pdf_pages},
        'original_files_unchanged_from_baseline':original,
        'hash_algorithm':'SHA-256',
        'files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)},
        'note':'Hashes exclude this manifest itself. Historical checkpoint reports remain named as such; final reports are the current handoff evidence.'}
    OUT.write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Hashed {len(paths)} artifacts; {len(patterns)} local footprints, {len(models)} model files, {pdf_pages} PDF pages; original files unchanged.')

if __name__=='__main__':main()
