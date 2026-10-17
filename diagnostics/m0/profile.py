"""Sample a trusted cold-cache probe's RSS and elapsed time; no app job claims."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import psutil

root = Path(os.environ['LOCALAPPDATA'])/'WoodworkingPlanner'/'probes'/uuid.uuid4().hex
root.mkdir(parents=True)
for name in ('part.py', 'part.json'):
    shutil.copyfile(Path(__file__).parent/name, root/name)
environment = {key: os.environ[key] for key in ('SystemRoot','WINDIR','PATH','TEMP','TMP','USERPROFILE','LOCALAPPDATA','APPDATA','COMSPEC','PATHEXT') if key in os.environ}
environment.update(CADGEN_DAEMON='0', CADGEN_JOBS='1', CADGEN_TELEMETRY='0', CADGEN_CACHE_DIR=str(root/'cache'), CADGEN_STATE_DIR=str(root/'state'), MPLCONFIGDIR=str(root/'matplotlib'), CADGEN_NODE=shutil.which('node') or '', PYTHONUTF8='1')
started = time.monotonic()
peak = 0
with (root/'run.log').open('wb') as log:
    process = subprocess.Popen([sys.executable,'-u',str(root/'part.py')],env=environment,stdout=log,stderr=subprocess.STDOUT,shell=False)
    owner = psutil.Process(process.pid)
    while process.poll() is None:
        try:
            running = [owner, *owner.children(recursive=True)]
            sampled = 0
            for child in running:
                try:
                    sampled += child.memory_info().rss
                except psutil.NoSuchProcess:
                    pass
            peak = max(peak, sampled)
        except psutil.NoSuchProcess:
            pass
        if time.monotonic()-started > 120:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=log,stderr=log,check=False)
            raise RuntimeError('Probe exceeded 120 seconds')
        time.sleep(.1)
    if process.returncode:
        raise RuntimeError('Trusted probe failed; inspect run.log')
report = {'output_root':str(root),'elapsed_seconds':time.monotonic()-started,'peak_sampled_process_tree_rss_bytes':peak,'sample_period_seconds':.1,'scope':'native Windows single trusted panel, cold application cache; concurrent development may affect elapsed time'}
(root/'profile.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
