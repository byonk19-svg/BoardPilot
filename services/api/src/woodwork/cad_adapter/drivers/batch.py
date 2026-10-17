"""Run only staged maintained models, sharing one pinned CAD interpreter."""
import json
from pathlib import Path
import runpy
import shutil
import sys
import time

from woodwork.cad_adapter.windows_runtime import configure_native_platform
configure_native_platform()

HERE=Path(__file__).resolve().parent
STAGES={'panel_side':'generating_side_panels','panel_horizontal':'generating_horizontal_panels','panel_back':'generating_back_panel'}


def event(stage):
    callback=globals().get('WOODWORK_PROGRESS')
    if callback is not None:
        callback(stage)
    else:
        print(json.dumps({'woodwork_stage':stage}),file=sys.stderr,flush=True)


if __name__=='__main__':
    config=json.loads((HERE/'batch.json').read_text(encoding='utf-8'))
    if not isinstance(config,dict) or set(config)!= {'definition_ids'}:
        raise ValueError('Unsupported batch contract')
    identifiers=config['definition_ids']
    if not isinstance(identifiers,list) or len(identifiers)!=len(STAGES) or any(not isinstance(i,str) or i not in STAGES for i in identifiers) or len(set(identifiers))!=len(STAGES):
        raise ValueError('Unsupported maintained panel definitions')
    timings=[]
    for identifier in identifiers:
        event(STAGES[identifier]); started=time.monotonic()
        # The application stages these exact installed files. JSON cannot supply
        # source code, module names, executable paths or alternate driver names.
        runpy.run_path(str(HERE/identifier/'part.py'),run_name='woodwork_'+identifier)['part']()
        # The public document export uses the producer and mesh attested to these
        # exact STEP bytes. A declared @glb exports a bare tree and needlessly
        # starts a transient native producer-identification helper per panel.
        from cadgen import glb
        saved=HERE/identifier/'out/part.step'
        result=glb.build(saved,saved.with_suffix('.glb'))
        if not result.ok:raise ValueError('Saved STEP preview export failed')
        timings.append({'stage':identifier,'seconds':round(time.monotonic()-started,3)})
        for suffix in ('step','glb'):
            shutil.copyfile(HERE/identifier/'out'/('part.'+suffix),HERE.parent/'parts'/(identifier+'.'+suffix))
    event('assembling_geometry'); started=time.monotonic()
    runpy.run_path(str(HERE/'assembly/assembly.py'),run_name='woodwork_assembly')['assembly']()
    timings.append({'stage':'assembly','seconds':round(time.monotonic()-started,3)})
    shutil.copyfile(HERE/'assembly/out/assembly.step',HERE.parent/'assembly.step')
    (HERE/'timings.json').write_text(json.dumps(timings),encoding='utf-8')
