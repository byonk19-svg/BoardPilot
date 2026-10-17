"""Only approved runtime variables enter trusted native workers."""
import hashlib
import os
from pathlib import Path
import shutil
import sys


def worker_environment(data_root: Path):
    repository = Path(__file__).resolve().parents[5]
    lock = repository/'requirements-runtime.lock'
    namespace = 'cadgen-0.7.21-' + hashlib.sha256(lock.read_bytes()).hexdigest()[:16]
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Node runtime unavailable; run preflight')
    environment = {key:os.environ[key] for key in ('SystemRoot','SYSTEMROOT','WINDIR','TEMP','TMP','USERPROFILE','LOCALAPPDATA','APPDATA','COMSPEC','PATHEXT','PROCESSOR_ARCHITECTURE','PROCESSOR_ARCHITEW6432') if key in os.environ}
    environment.update({
        'PATH':os.pathsep.join([str(Path(sys.executable).parent),str(Path(node).parent),str(Path(environment.get('SystemRoot','C:/Windows'))/'System32')]) if os.name=='nt' else os.defpath,
        'PYTHONPATH':str(repository/'services/api/src'),'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8',
        'CADGEN_DAEMON':'0','CADGEN_JOBS':'1','CADGEN_TELEMETRY':'0','CADGEN_UPDATE_CHECK':'0','CADGEN_NODE':node,
        'CADGEN_CACHE_DIR':str(data_root/'cache'/namespace),'CADGEN_STATE_DIR':str(data_root/'cadgen-state'/namespace),'MPLCONFIGDIR':str(data_root/'matplotlib'/namespace),
    })
    for key in ('CADGEN_CACHE_DIR','CADGEN_STATE_DIR','MPLCONFIGDIR'):
        Path(environment[key]).mkdir(parents=True,exist_ok=True)
    return environment
