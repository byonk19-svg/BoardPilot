"""Native verification follows the application's isolated, daemon-free policy."""
import os
from pathlib import Path

import pytest


@pytest.fixture(scope='session',autouse=True)
def native_reader_environment():
    # Independent readers run in pytest, outside the supervised application
    # worker. cadgen otherwise starts its default resident pool while inspecting
    # saved STEP files, retaining extra kernels across corpus cases.
    with pytest.MonkeyPatch.context() as environment:
        for key,value in {'CADGEN_DAEMON':'0','CADGEN_JOBS':'1',
                          'CADGEN_TELEMETRY':'0','CADGEN_UPDATE_CHECK':'0'}.items():
            environment.setenv(key,value)
        if os.environ.get('WOODWORK_RUN_CAD_CORPUS')=='1' or os.environ.get('WOODWORK_RUN_DOCUMENT_CORPUS')=='1':
            from woodwork.jobs.environment import worker_environment
            root=os.environ.get('WOODWORK_CAD_CORPUS_ROOT') or os.environ.get('WOODWORK_GEOMETRY_CORPUS_ROOT')
            if root:
                approved=worker_environment(Path(root))
                for key in ('CADGEN_CACHE_DIR','CADGEN_STATE_DIR','MPLCONFIGDIR'):
                    environment.setenv(key,approved[key])
        from woodwork.cad_adapter.windows_runtime import configure_native_platform
        configure_native_platform()
        yield
