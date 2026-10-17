"""Persist and render genuine cumulative stock exports for all supplied projects."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from woodwork.exports.stock import add_stock,validate_stock_output
from woodwork.exports.core import write_json,sha256_file
from woodwork.cad_adapter import validate_artifact_set


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--renderer',default='pdftoppm')
    args=parser.parse_args()
    root=args.output.resolve();root.mkdir(parents=True,exist_ok=False)
    expected=json.loads((Path(__file__).parents[1]/'tests/fixtures/bookcase-expected.json').read_text())['fixtures']
    observations=[]
    for case in expected:
        stem=case['input_file'].removesuffix('.json')
        source=args.source/stem
        manifest=json.loads((source/'manifest.json').read_text())
        spec=json.loads((source/'project.json').read_text());resolved=json.loads((source/'resolved-project.json').read_text())
        metadata={k:manifest[k] for k in ('project_id','revision_id','revision_number','spec_sha256','resolved_sha256')}
        metadata.update(artifact_set_id='stock_'+stem.replace('-','_'),source_artifact_set_id=manifest['artifact_set_id'])
        output=root/stem
        result=add_stock(source,output,metadata,spec,resolved)
        validate_artifact_set(output,inspect_geometry=False)
        evidence=validate_stock_output(output,spec,resolved,metadata)
        render=root/'rendered'/stem;render.mkdir(parents=True)
        subprocess.run([args.renderer,'-png','-r','110',str(output/'stock-layout.pdf'),str(render/'stock')],check=True,capture_output=True)
        pages=list(render.glob('*.png'))
        assert len(pages)==evidence['pdf_pages']
        observations.append({'fixture':case['input_file'],'directory':str(output),'manifest_sha256':sha256_file(output/'manifest.json'),'stock_pdf_sha256':sha256_file(output/'stock-layout.pdf'),'pages_rendered':len(pages),'status':'passed','visual_review':'pending','artifact_set_id':result['artifact_set_id']})
        print(json.dumps({'fixture':stem,'status':'passed','pages':len(pages)}),flush=True)
    write_json(root/'stock-corpus-evidence.json',{'status':'passed','scope':'nine genuine cumulative exports; exact cut-tree replay and PDF text/identity checks, all stock pages rendered','fixtures':observations})


if __name__=='__main__':main()
