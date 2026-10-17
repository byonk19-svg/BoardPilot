import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Viewer, type SceneManifest} from './Viewer';
import './style.css';
import {App} from './App';
const probe:SceneManifest={part_definitions:[{definition_id:'panel',finished_mm:{length_mm:'726',width_mm:'298.8',thickness_mm:'18'},member_instance_ids:['panel_left','panel_right'],quantity:2,material_id:'probe'}],part_instances:['panel_left','panel_right'].map((id,i)=>({instance_id:id,definition_id:'panel',center_mm:{x:i?'250':'-250',y:'0',z:'363'},rotation_cad_rows:[[0,1,0],[0,0,1],[1,0,0]]}))};
function Probe(){const [selected,setSelected]=useState<string[]>([]);return <><header><span className="wordmark">Woodworking Planner</span><span className="muted">CAD integration check</span></header><main className="probe"><div className="section-heading"><div><h1>One genuine part, two physical instances</h1><p>Saved cadgen geometry. Millimeters in CAD, meters in the viewer.</p></div></div><Viewer manifest={probe} urls={{panel:'/probes/part.glb'}} selected={selected} onSelect={setSelected} initialView="front"/><nav aria-label="Part instances">{probe.part_instances.map(i=><button key={i.instance_id} aria-pressed={selected.includes(i.instance_id)} onClick={()=>setSelected([i.instance_id])}>{i.instance_id}</button>)}</nav><p className="muted">This diagnostic verifies shared geometry and independent selection. Project workflow is under implementation.</p></main></>}
createRoot(document.getElementById('root')!).render(new URLSearchParams(location.search).get('probe')==='m0'?<Probe/>:<App/>);
