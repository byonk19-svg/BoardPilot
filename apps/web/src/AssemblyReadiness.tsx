import type {RecipeOption} from './api';
import {formatMeasurement} from './measurements';

export function AssemblyReadiness({selected,recipe,status,checking,dirty,unit,precision,downloadRevision}:{selected:boolean;recipe?:RecipeOption;status?:string;checking:boolean;dirty:boolean;unit:'in'|'mm';precision:number;downloadRevision?:number}){
  const warning=!checking&&!!status&&!['recipe_complete','recipe_unselected'].includes(status);
  const bounds=recipe?.modeling_bounds;
  const sizeKeys=['outside_width_mm','outside_height_mm','outside_depth_mm'];
  const limit=(values:[string,string],units:'in'|'mm')=>values[0]===values[1]?formatMeasurement(values[0],units,precision):`${formatMeasurement(values[0],units,precision)} to ${formatMeasurement(values[1],units,precision)}`;
  const size=bounds&&sizeKeys.every(key=>bounds['dimensions.'+key])?sizeKeys.map((key,i)=>`${limit(bounds['dimensions.'+key],unit)} ${['W','H','D'][i]}`).join(' × '):null;
  const main=bounds?.['materials.main.actual_thickness_mm'],back=bounds?.['materials.back.actual_thickness_mm'];
  const shelves=recipe?.shelf_count;
  const ordinary=!checking&&status?(status==='recipe_unselected'?'Assembly method still needed; checked dimensions are not assembly instructions.':status==='recipe_complete'?'Technical fabrication method complete; physical review pending':''):
    selected?(checking?'Checking whether the assembly method applies…':'Assembly method selected; correct measurements to recheck fabrication readiness.'):'Assembly method still needed; checked dimensions are not assembly instructions.';
  return <div id="assembly-guide-status" className={'assembly-readiness'+(warning?' assembly-warning':'')} data-testid="recipe-state" role="status" aria-label="Assembly guide availability" aria-atomic="true">
    {warning?<>
      <strong>{status==='recipe_incompatible'?`Build guide won't apply to this ${dirty?'draft':'design'}`:`Assembly instructions aren't ready for this ${dirty?'draft':'design'}`}</strong>
      <p>The selected assembly method is {status==='recipe_incompatible'?'incompatible with these settings':'incomplete for these settings'}. You can still update the model and cut list, then use Get plans for measured drawings. A matching Build guide PDF and assembly steps will not be generated.</p>
      {size||main||back||shelves?<div className="method-limits"><span>Selected method supports:</span>
        {size&&<p>{size}</p>}
        {(main||back)&&<p>Actual panels: {main&&`${limit(main,'mm')} main`}{main&&back?' / ':''}{back&&`${limit(back,'mm')} back`}.</p>}
        {shelves&&<p>{shelves[0]===shelves[1]?shelves[0]:`${shelves[0]} to ${shelves[1]}`} fixed {shelves[0]===1&&shelves[1]===1?'shelf':'shelves'}.</p>}
      </div>:<p>The supported limits could not be loaded. Review the selected method in Advanced settings.</p>}
      {downloadRevision!==undefined&&<p>Existing downloads for revision {downloadRevision} still describe that revision.</p>}
    </>:ordinary}
  </div>;
}
