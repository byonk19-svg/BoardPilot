"""Cheap runtime metadata and safe setup diagnostics; native probes run separately."""
import importlib.metadata
import platform as platform_module
import shutil
import subprocess
import sys


def classify_runtime_failure(message: str, *, platform: str | None = None):
    if (platform or sys.platform) == 'win32' and 'DLL load failed' in message and 'OCP' in message:
        return {'code': 'NATIVE_KERNEL_LOAD_REFUSED', 'message': 'Windows refused to load the CAD native module.', 'guidance': 'Check CodeIntegrity Event ID 3077 for the OCP module. A WSL fallback requires a separate Linux Python 3.13/Node setup and full preflight; that route has not been verified here. Keep operating-system security settings unchanged.'}
    return {'code': 'RUNTIME_UNAVAILABLE', 'message': 'A required CAD component did not load.', 'guidance': 'Run the explicit preflight command and install the locked runtime and matching Chromium browser.'}


def runtime_versions():
    versions = {'python': platform_module.python_version()}
    missing = []
    if sys.version_info[:2]!=(3,13):missing.append('Python 3.13')
    expected={'cadgen':'0.7.21','build123d':'0.11.1','cadquery-ocp-novtk':'7.9.3.1.1','playwright':'1.63.0'}
    for name in ('cadgen', 'build123d', 'cadquery-ocp-novtk', 'playwright'):
        try:
            versions[name] = importlib.metadata.version(name)
            if versions[name]!=expected[name]:missing.append(name+' version '+expected[name])
        except importlib.metadata.PackageNotFoundError:
            missing.append(name)
    node = shutil.which('node')
    if node:
        try:
            versions['node'] = subprocess.check_output([node, '--version'], text=True, timeout=5).strip()
            if versions['node']!='v24.13.0':missing.append('Node 24.13.0')
        except (OSError, subprocess.SubprocessError):
            missing.append('node')
    else:
        missing.append('node')
    return {'versions': versions, 'missing_components': missing, 'kernel_probe': 'explicit_preflight_required'}
