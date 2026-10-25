import type {ProjectSpec} from './contracts';
import type {Definition, SceneManifest} from './Viewer';

export type Finding={field:string;message:string;code?:string;details?:Record<string,unknown>};
export type CutGroup=Definition & {group_id:string;definition_ids:string[];rough_mm:Definition['finished_mm'];grain_axis:string;manufacturing_sha256:string};
export type Resolved=SceneManifest & {cut_groups:CutGroup[];part_instance_count:number;part_definition_count:number;inside_width_mm:string;carcass_depth_mm:string;rounded_clear_height_target_mm:string;openings:{opening_index:number;resolved_clear_height_mm:string}[];construction_status:string;geometry_sha256:string};
export type Revision={id:string;project_id:string;number:number;parent_id:string|null;spec:ProjectSpec;resolved:Resolved;preferred_artifact_set_id:string|null};
export type Project={id:string;title:string;latest_accepted_revision_id:string;latest_successful_revision_id:string|null};
export type Artifact={artifact_id:string;kind:string;relative_path:string;definition_id:string|null};
export type Construction={status:string;recipe_id:string|null;recipe_version:string|null;physical_review:string;findings:string[]};
export type Manifest=SceneManifest & {revision_id:string;revision_number:number;artifact_set_id:string;artifacts:Artifact[];capabilities:string[];construction:Construction;validation:{geometry:string;documents:string;stock_layout:string}};
export type Job={id:string;revision_id?:string;kind?:string;state:string;stage:string;idempotency_key?:string;source_artifact_set_id?:string|null;started_at?:string|null;finished_at?:string|null;diagnostic_code?:string|null;result_artifact_set_id?:string|null;result_artifact_id?:string|null};
export type RecipeOption={id:string;version:string;title:string;required_tools:string[];modeling_bounds?:Record<string,[string,string]>;shelf_count?:[number,number]|null};
export type Template={id:string;version:string;default_spec:ProjectSpec;recipes:RecipeOption[]};
export const terminal=(state:string)=>['succeeded','failed','cancelled','interrupted'].includes(state);

export class ApiError extends Error {
  constructor(public status:number, public findings:Finding[], message:string){super(message);}
}

export class ServiceUnavailableError extends Error {
  constructor(){super('The local service is unavailable. Open the Woodworking Planner desktop shortcut, then try again. Your inputs and selected files are kept.');}
}

async function fetchLocal(url:string,options?:RequestInit){
  try{return await fetch(url,options);}
  catch{throw new ServiceUnavailableError();}
}

async function responseJson(response:Response,fallback='This operation could not be completed.'){
  let data;
  try{data=await response.json();}
  catch{throw new ServiceUnavailableError();}
  if(!data||typeof data!=='object')throw new ServiceUnavailableError();
  if(!response.ok){const error=data.error||{};const findings:Finding[]=error.details?.findings||data.errors||[];throw new ApiError(response.status,findings,error.message||findings[0]?.message||fallback);}
  return data;
}

let csrf='';
async function session(){const response=await fetchLocal('/api/v1/session');if(!response.ok)throw new ServiceUnavailableError();const data=await responseJson(response);if(typeof data.csrf_token!=='string'||!data.csrf_token)throw new ServiceUnavailableError();csrf=data.csrf_token;}
export async function api<T>(path:string, body?:unknown, method=body===undefined?'GET':'POST'):Promise<T>{
  const mutation=method!=='GET';
  if(mutation&&!csrf)await session();
  const send=()=>fetchLocal('/api/v1'+path,{method,headers:mutation?{'Content-Type':'application/json','X-Woodwork-CSRF':csrf}:{},body:body===undefined?undefined:JSON.stringify(body)});
  let response=await send();
  if(response.status===403&&mutation){await session();response=await send();}
  return await responseJson(response) as T;
}
export const artifactUrl=(id:string)=>'/api/v1/artifacts/'+encodeURIComponent(id)+'/download';
export const requestKey=()=>crypto.randomUUID();

export async function uploadApi<T>(path:string,file:Blob):Promise<T>{
  if(!csrf)await session();
  const send=()=>fetchLocal('/api/v1'+path,{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Woodwork-CSRF':csrf},body:file});
  let response=await send();
  if(response.status===403){await session();response=await send();}
  return await responseJson(response,'The project package could not be validated.') as T;
}
