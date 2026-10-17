"""Compare the current worker with a single-process trusted-driver pilot.

Only maintained drivers and the supplied baseline are executed. Each run uses
a fresh disposable directory/cache; no project store is opened or changed.
The historical pre-change result in evidence/m2/regeneration-profile.json used
the old four-launch worker; rerunning this script measures the current worker.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time

from woodwork.cad_adapter.windows_runtime import configure_native_platform
configure_native_platform()
from woodwork.cad_adapter.runtime import DRIVERS, _cad_environment, _run_driver
from woodwork.cad_adapter.verifier import measure_geometry
from woodwork.domain import compile_project
from woodwork.exports.core import write_json
from woodwork.jobs.environment import worker_environment
from woodwork.jobs.process import ProcessSupervisor
from woodwork.templates import default_project_spec


PILOT = '''import json, runpy, shutil, time
from pathlib import Path
from woodwork.cad_adapter.windows_runtime import configure_native_platform
configure_native_platform()
HERE=Path(__file__).resolve().parent
timings=[]
for identifier in ('panel_side','panel_horizontal','panel_back'):
    print(json.dumps({'stage':'generating_geometry','definition_id':identifier}),flush=True)
    started=time.monotonic()
    runpy.run_path(str(HERE/identifier/'part.py'),run_name='woodwork_'+identifier)['part']()
    from cadgen import glb
    glb.build(HERE/identifier/'out/part.step',HERE/identifier/'out/part.glb')
    timings.append({'stage':identifier,'seconds':time.monotonic()-started})
    for suffix in ('step','glb'):
        shutil.copyfile(HERE/identifier/'out'/('part.'+suffix),HERE.parent/'parts'/(identifier+'.'+suffix))
print(json.dumps({'stage':'assembling_geometry'}),flush=True)
started=time.monotonic()
runpy.run_path(str(HERE/'assembly/assembly.py'),run_name='woodwork_assembly')['assembly']()
timings.append({'stage':'assembly','seconds':time.monotonic()-started})
shutil.copyfile(HERE/'assembly/out/assembly.step',HERE.parent/'assembly.step')
(HERE.parent/'pilot-timings.json').write_text(json.dumps(timings))
'''


def pilot(root):
    spec=default_project_spec(); resolved=compile_project(spec)
    out=root/'out'; work=out/'.work'; work.mkdir(parents=True)
    (out/'parts').mkdir()
    for definition in resolved['part_definitions']:
        target=work/definition['definition_id']; target.mkdir()
        shutil.copyfile(DRIVERS/'part.py',target/'part.py')
        write_json(target/'part.json',definition['finished_mm'])
    target=work/'assembly'; target.mkdir()
    shutil.copyfile(DRIVERS/'assembly.py',target/'assembly.py')
    write_json(target/'assembly.json',{'part_definitions':resolved['part_definitions'],'part_instances':resolved['part_instances']})
    (work/'pilot.py').write_text(PILOT,encoding='utf-8')
    started=time.monotonic()
    _run_driver(work/'pilot.py',_cad_environment(work))
    generation=time.monotonic()-started
    report,_=measure_geometry(out,resolved)
    write_json(root/'pilot-result.json',{'generation_seconds':generation,'total_seconds':time.monotonic()-started,'timings':json.loads((out/'pilot-timings.json').read_text()),'geometry':report['geometry'],'assembly':report['assembly']})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--pilot-worker',action='store_true')
    args=parser.parse_args(); root=args.root.resolve()
    if args.pilot_worker:
        pilot(root); return
    root.mkdir(parents=True,exist_ok=False)
    observations=[]
    with ProcessSupervisor() as supervisor:
        for mode in ('pilot','baseline'):
            target=root/mode; target.mkdir()
            if mode=='pilot': command=[sys.executable,'-u',str(Path(__file__).resolve()),'--root',str(target),'--pilot-worker']
            else:
                spec=default_project_spec()
                write_json(target/'input.json',{'kind':'generate','spec':spec,'resolved':compile_project(spec),'metadata':{'project_id':'profile','revision_id':'baseline','revision_number':1}})
                command=[sys.executable,'-u','-m','woodwork.jobs.worker',str(target)]
            result=supervisor.run(command,cwd=Path(__file__).resolve().parents[1],env=worker_environment(target),log_path=target/'worker.log',timeout_seconds=300,on_event=lambda event: print(json.dumps(event),flush=True))
            observation={'mode':mode,'returncode':result.returncode,'timed_out':result.timed_out,'elapsed_seconds':result.elapsed_seconds,'peak_rss_bytes':result.peak_rss_bytes}
            detail=target/('pilot-result.json' if mode=='pilot' else 'out/geometry-validation.json')
            if detail.exists(): observation['detail']=json.loads(detail.read_text())
            observations.append(observation)
            write_json(root/'profile.json',observations)
            print(json.dumps({key:value for key,value in observation.items() if key!='detail'}),flush=True)
            if result.returncode: raise RuntimeError(f'{mode} failed; inspect {target}')


if __name__=='__main__': main()
