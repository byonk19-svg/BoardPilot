"""Explicit local compilation/build commands; no browser or AI required."""
import argparse
import json
from pathlib import Path
import sys
import uuid
import os

class BuildError(ValueError):
    def __init__(self,code,message):
        self.code=code
        super().__init__(message)


def main():
    parser = argparse.ArgumentParser(description='Deterministic woodworking planner')
    commands = parser.add_subparsers(dest='command', required=True)
    compile_command = commands.add_parser('compile', help='Validate and compile exact panel ledger')
    compile_command.add_argument('project', type=Path)
    build_command = commands.add_parser('build', help='Generate and verify genuine CAD into a new output directory')
    build_command.add_argument('project', type=Path)
    build_command.add_argument('--output', type=Path, required=True)
    build_command.add_argument('--project-id', default='sample_bookcase')
    build_command.add_argument('--revision-id', default=None)
    build_command.add_argument('--revision-number', type=int, default=1)
    preflight_command=commands.add_parser('preflight',help='Run the trusted baseline in a contained native worker')
    preflight_command.add_argument('--output',type=Path)
    preflight_command.set_defaults(project=None,project_id='runtime_preflight',revision_id=None,revision_number=1)
    args = parser.parse_args()
    from woodwork.domain import ProjectSpec, DomainError
    from woodwork.application import compile_design as compile_project
    try:
        if args.command=='preflight':
            from woodwork.templates import default_project_spec
            spec=ProjectSpec.model_validate(default_project_spec())
        else:
            with args.project.open('rb') as stream:
                raw=stream.read(256*1024+1)
            if len(raw) > 256 * 1024:raise ValueError('Project exceeds 256 KiB')
            spec = ProjectSpec.model_validate(json.loads(raw))
        resolved = compile_project(spec)
        if args.command == 'compile':
            print(json.dumps(resolved, indent=2))
            return
        from woodwork.cad_adapter import validate_artifact_set
        data_root=Path(os.environ.get('WOODWORK_DATA_ROOT',str(Path.home()/'AppData/Local/WoodworkingPlanner/data') if os.name=='nt' else str(Path.home()/'.local/share/woodworking-planner'))).resolve()
        output = args.output.resolve() if args.output else data_root/'preflights'/uuid.uuid4().hex
        if output.exists():
            raise ValueError('Output directory exists; immutable artifacts require a new directory')
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = output.parent / ('.staging-' + uuid.uuid4().hex)
        metadata = {'project_id': args.project_id, 'revision_id': args.revision_id or 'rev_' + uuid.uuid4().hex, 'revision_number': args.revision_number, 'artifact_set_id': 'set_' + uuid.uuid4().hex, 'source_artifact_set_id': None}
        from woodwork.jobs.process import ProcessSupervisor
        from woodwork.jobs.environment import worker_environment
        staging.mkdir()
        (staging/'input.json').write_text(json.dumps({'kind':'generate','spec':spec.model_dump(mode='json'),'resolved':resolved,'metadata':metadata}),encoding='utf-8')
        with ProcessSupervisor() as supervisor:
            result=supervisor.run([sys.executable,'-u','-m','woodwork.jobs.worker',str(staging)],cwd=Path(__file__).resolve().parents[4],env=worker_environment(data_root),log_path=staging/'worker.log',timeout_seconds=120)
        if result.returncode or result.timed_out or result.cancelled:
            code='CAD_TIMEOUT' if result.timed_out else 'WORKER_FAILED'
            for line in result.log_tail.splitlines():
                try:
                    event_data=json.loads(line)
                    if 'error_code' in event_data:code=event_data['error_code']
                except (ValueError,TypeError):pass
            raise BuildError(code,'CAD job did not publish a result; unpublished staging retained for diagnosis')
        validate_artifact_set(staging/'out',inspect_geometry=False)
        manifest=json.loads((staging/'out/manifest.json').read_text(encoding='utf-8'))
        (staging/'out').rename(output)
        metrics={'elapsed_seconds':result.elapsed_seconds,'peak_sampled_process_tree_rss_bytes':result.peak_rss_bytes}
        if args.command=='preflight':
            from woodwork.exports.core import write_json
            from woodwork.runtime import runtime_versions
            from woodwork.storage import now
            data_root.mkdir(parents=True,exist_ok=True)
            write_json(data_root/'runtime-preflight.json',{'status':'passed','checked_at':now(),**runtime_versions(),'kernel_probe':'passed','metrics':metrics})
        print(json.dumps({'output': str(output), 'revision_id': manifest['revision_id'], 'artifact_set_id': manifest['artifact_set_id'], 'validation': manifest['validation'],'metrics':metrics}, indent=2))
    except DomainError as error:
        print(json.dumps({'error': 'VALIDATION_FAILED', 'findings': error.findings}), file=sys.stderr)
        raise SystemExit(2)
    except BuildError as error:
        print(json.dumps({'error':error.code,'message':str(error)}),file=sys.stderr)
        raise SystemExit(3)
    except (ValueError, OSError) as error:
        print(json.dumps({'error': 'INPUT_FAILED', 'message': str(error)}), file=sys.stderr)
        raise SystemExit(2)


if __name__ == '__main__':
    main()
