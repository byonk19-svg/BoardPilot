import type {ProjectSpec} from './contracts';
import {api,ApiError,type Resolved} from './api';

export type Unit='in'|'mm';
export type Measurement={text:string;default_unit:Unit};
export type Form={version:1;spec:ProjectSpec;measurements:Record<string,Measurement>;prices:Record<string,string>};
export type Validated={spec:ProjectSpec;resolved:Resolved};
const dimensionPaths=['dimensions.outside_width_mm','dimensions.outside_height_mm','dimensions.outside_depth_mm'];

export function measurementPaths(spec:ProjectSpec){return [...dimensionPaths,'materials.main.actual_thickness_mm','materials.back.actual_thickness_mm','manufacturing.saw_kerf_mm','manufacturing.rough_allowance_per_edge_mm','manufacturing.sheet_edge_trim_mm',...spec.manufacturing.stock_sheets.flatMap((_,i)=>[`manufacturing.stock_sheets.${i}.length_mm`,`manufacturing.stock_sheets.${i}.width_mm`])];}
function valueAt(spec:ProjectSpec,path:string){let value:unknown=spec;for(const key of path.split('.'))value=(value as Record<string,unknown>)[key];return String(value);}
function writeValue(spec:ProjectSpec,path:string,value:string){const pieces=path.split('.');let target=spec as unknown as Record<string,unknown>;for(const key of pieces.slice(0,-1))target=target[key] as Record<string,unknown>;target[pieces.at(-1)!]=value;}

// Only exact finite inch conversions become editable text. Repeating values stay
// canonical mm; rounded presentation labels never feed back into a measurement.
function editableMeasurement(mm:string,unit:Unit){
  if(unit==='mm')return mm+' mm';
  const [whole,fraction='']=mm.split('.');let numerator=BigInt(whole+fraction)*5n;let denominator=10n**BigInt(fraction.length)*127n;
  let a=numerator,b=denominator;while(b){const remainder=a%b;a=b;b=remainder;}numerator/=a||1n;denominator/=a||1n;
  let twos=0,fives=0;while(denominator%2n===0n){denominator/=2n;twos++;}while(denominator%5n===0n){denominator/=5n;fives++;}
  if(denominator!==1n||Math.max(twos,fives)>12)return mm+' mm';
  const places=Math.max(twos,fives);const scaled=numerator*2n**BigInt(places-twos)*5n**BigInt(places-fives);
  const digits=scaled.toString().padStart(places+1,'0');const text=places?(digits.slice(0,-places)+'.'+digits.slice(-places)).replace(/0+$/,'').replace(/\.$/,''):digits;
  return text+' in';
}
export function formFrom(spec:ProjectSpec):Form{return {version:1,spec:structuredClone(spec),measurements:Object.fromEntries(measurementPaths(spec).map(path=>[path,{text:editableMeasurement(valueAt(spec,path),dimensionPaths.includes(path)?spec.display.preferred_unit:'mm'),default_unit:dimensionPaths.includes(path)?spec.display.preferred_unit:'mm'}])),prices:Object.fromEntries(spec.manufacturing.stock_sheets.map(s=>[s.stock_id,s.unit_price||'']))};}
export function restoreForm(raw:unknown):Form|null {
  if(!raw||typeof raw!=='object')return null;const value=raw as Partial<Form>;
  try{
    const spec=value.spec;
    if(value.version!==1||!spec||typeof spec.project_name!=='string'||!spec.dimensions||!spec.display||!spec.materials?.main||!spec.materials.back||!spec.documents||!spec.construction||!Array.isArray(spec.manufacturing?.stock_sheets)||spec.manufacturing.stock_sheets.length>12||!value.measurements||!value.prices)return null;
    for(const path of measurementPaths(spec)){const field=value.measurements[path];if(!field||typeof field.text!=='string'||!['in','mm'].includes(field.default_unit))return null;}
    for(const material of Object.values(spec.materials))if(typeof material.nominal_label!=='string'||typeof material.actual_thickness_mm!=='string')return null;
    for(const sheet of spec.manufacturing.stock_sheets)if(typeof sheet.stock_id!=='string'||typeof value.prices[sheet.stock_id]!=='string')return null;
    return value as Form;
  }catch{return null;}
}
export function displayUnit(form:Form,unit:Unit):Form {const copy=structuredClone(form);copy.spec.display.preferred_unit=unit;for(const path of dimensionPaths){const measurement=copy.measurements[path];if(!/(mm|cm|in|\")\s*$/i.test(measurement.text))measurement.text+=' '+measurement.default_unit;measurement.default_unit=unit;}return copy;}
export async function validateForm(form:Form):Promise<Validated>{
  const paths=measurementPaths(form.spec);
  const normalized=await api<{values:{field:string;value_mm:string}[];errors:unknown[]}>('/inputs/normalize',paths.map(field=>({field,...form.measurements[field]})));
  const spec=structuredClone(form.spec);
  for(const field of paths){const row=normalized.values.find(value=>value.field===field);if(!row)throw new Error('The measurement service returned an incomplete result.');writeValue(spec,field,row.value_mm);}
  for(const [i,stock] of spec.manufacturing.stock_sheets.entries()){
    const text=(form.prices[stock.stock_id]||'').trim();
    if(text&&!/^\d+(?:\.\d{1,2})?$/.test(text))throw new ApiError(422,[{field:`manufacturing.stock_sheets.${i}.unit_price`,message:'Enter a nonnegative USD price with at most two decimal places.'}],'Check the sheet price.');
    if(text){const [whole,fraction='']=text.split('.');stock.unit_price=BigInt(whole).toString()+'.'+fraction.padEnd(2,'0');}else stock.unit_price=null;
  }
  return api<Validated>('/specs/validate',spec);
}
export function sameSpec(a:ProjectSpec,b:ProjectSpec){const canonical=(value:unknown):unknown=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([key,value])=>[key,canonical(value)])):value;return JSON.stringify(canonical(a))===JSON.stringify(canonical(b));}
export function changeSummary(previous:Resolved|undefined,current:Resolved){
  if(!previous)return [`${current.part_instance_count} panels · ${current.openings.length} clear openings`,`Inside width ${current.inside_width_mm} mm · panel depth ${current.carcass_depth_mm} mm`,`Clear height target ${current.rounded_clear_height_target_mm} mm`];
  const changes:string[]=[];
  for(const next of current.part_definitions){const old=previous.part_definitions.find(p=>p.definition_id===next.definition_id);if(!old)continue;for(const [axis,label] of [['length_mm','length'],['width_mm',next.definition_id==='panel_back'?'width':'depth'],['thickness_mm','thickness']] as const){if(old.finished_mm[axis]!==next.finished_mm[axis])changes.push(`${groupLabel(next.definition_id)} ${label}: ${old.finished_mm[axis]} → ${next.finished_mm[axis]} mm`);}if(old.quantity!==next.quantity)changes.push(`${groupLabel(next.definition_id)}: ${old.quantity} → ${next.quantity} panels`);}
  if(previous.rounded_clear_height_target_mm!==current.rounded_clear_height_target_mm)changes.push(`Clear height: ${previous.rounded_clear_height_target_mm} → ${current.rounded_clear_height_target_mm} mm`);
  return [`${current.part_instance_count} panels · ${current.openings.length} clear openings`,...(changes.length?changes:['Panel geometry unchanged. Labels, manufacturing settings, and output preferences remain part of this revision.'])];
}
export function groupLabel(id:string){return {panel_side:'Sides',panel_horizontal:'Horizontal panels',panel_back:'Applied back'}[id]||'Interchangeable panels';}
