"""Bounded diagnostic of a staged maintained batch and its helper imports."""
import argparse
from pathlib import Path
import sys

from woodwork.cad_adapter.runtime import _cad_environment
from woodwork.exports.core import write_json
from woodwork.jobs.process import ProcessSupervisor


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--batch',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); root=args.output.resolve(); root.mkdir(parents=True,exist_ok=False)
    bootstrap=root/'bootstrap'; bootstrap.mkdir()
    # Diagnostic-only startup hooks write stacks locally; no persistent Python
    # installation or application environment is changed.
    (bootstrap/'sitecustomize.py').write_text(
        'import faulthandler,os\nfrom pathlib import Path\n'
        f"_trace=Path({str(root)!r})/(str(os.getpid())+'.trace.txt')\n"
        "_stream=_trace.open('w')\nfaulthandler.enable(file=_stream)\n"
        "faulthandler.dump_traceback_later(5,repeat=True,file=_stream)\n",encoding='utf-8')
    env=_cad_environment(root); env['PYTHONPATH']=str(bootstrap)
    batch=args.batch.resolve()
    with ProcessSupervisor() as supervisor:
        result=supervisor.run([sys.executable,'-u',str(batch)],cwd=batch.parent,env=env,log_path=root/'worker.log',timeout_seconds=60)
    write_json(root/'process-result.json',{'returncode':result.returncode,'timed_out':result.timed_out,'elapsed_seconds':result.elapsed_seconds,'peak_rss_bytes':result.peak_rss_bytes})
    print(root,flush=True)


if __name__=='__main__':main()
