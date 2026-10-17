"""Independently reopen the genuine browser flow's saved CAD and stock sets."""
import argparse
import json
from pathlib import Path
import re

from woodwork.cad_adapter.windows_runtime import configure_native_platform
configure_native_platform()
from woodwork.cad_adapter import validate_artifact_set
from woodwork.exports.stock import validate_stock_output
from woodwork.exports.core import write_json


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-root',type=Path,required=True)
    parser.add_argument('--cases',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    cases=json.loads(args.cases.read_text(encoding='utf-8'))
    rows=[]
    for case in cases:
        ids=[case['artifact_set_id'],case['generation_artifact_set_id']]
        assert all(isinstance(i,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,99}',i) for i in ids)
        stock_root=args.data_root/'artifacts'/ids[0]
        generated_root=args.data_root/'artifacts'/ids[1]
        stock_set=validate_artifact_set(stock_root,inspect_geometry=True)
        generated=validate_artifact_set(generated_root,inspect_geometry=True)
        spec=json.loads((stock_root/'project.json').read_text())
        resolved=json.loads((stock_root/'resolved-project.json').read_text())
        manifest=json.loads((stock_root/'manifest.json').read_text())
        stock=validate_stock_output(stock_root,spec,resolved,manifest)
        assert generated['revision_id']==stock_set['revision_id']==case['revision_id']
        assert spec['dimensions']==case['dimensions']
        assert generated['geometry']['assembly']['world_aabb_mm']==stock_set['geometry']['assembly']['world_aabb_mm']
        assert stock['layout_status']=='complete' and stock['cut_tree_replay']=='passed'
        assert case['generation_seconds']<120
        row={'revision':case['revision'],'revision_id':case['revision_id'],'generation_seconds':case['generation_seconds'],'generated_set':ids[1],'cumulative_set':ids[0],'saved_geometry':'passed','cut_tree_replay':'passed','artifact_count':stock_set['artifact_count'],'physical_panels':stock_set['geometry']['assembly']['solid_count']}
        rows.append(row);print(json.dumps(row),flush=True)
    assert [case['revision'] for case in cases]==[1,2,3,4,4]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    write_json(args.output,{'status':'passed','cases':rows,'native_saved_sets_reopened':2*len(rows)})


if __name__=='__main__':main()
