import type {Artifact,Manifest} from './api';

export function designPdfLabel(manifest:Manifest){
  const illustrated=manifest.construction.status==='complete'&&manifest.validation.documents==='passed'&&manifest.artifacts.some(a=>a.relative_path==='beginner-guide.json');
  return illustrated?'Build guide PDF':'Measured design PDF';
}

/** Files already offered by their model, cut-list or output controls stay out of the raw list. */
export function additionalRevisionFiles(manifest:Manifest,promoted:Artifact[]){
  const promotedIds=new Set(promoted.map(a=>a.artifact_id));
  const promotedPaths=new Set(promoted.map(a=>a.relative_path));
  const directPaths=new Set(['project.json','assembly.step','cut-list.csv','stock-layout.json','cost-estimate.json']);
  return manifest.artifacts.filter(a=>{
    if(promotedIds.has(a.artifact_id)||directPaths.has(a.relative_path))return false;
    if(a.kind==='pdf'&&a.definition_id||a.kind==='svg'&&a.relative_path.includes('stock'))return false;
    if(['design-packet.pdf','stock-layout.pdf'].includes(a.relative_path)&&!promotedPaths.has(a.relative_path))return false;
    return true;
  });
}
