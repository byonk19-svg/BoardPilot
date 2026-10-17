import { Component, Suspense, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, useGLTF } from '@react-three/drei';
import * as THREE from 'three';

export type Definition = {definition_id:string;finished_mm:{length_mm:string;width_mm:string;thickness_mm:string};member_instance_ids:string[];quantity:number;material_id:string};
export type Instance = {instance_id:string;definition_id:string;center_mm:{x:string;y:string;z:string};rotation_cad_rows:number[][]};
export type SceneManifest = {part_definitions:Definition[];part_instances:Instance[]};
type Props = {manifest:SceneManifest;urls:Record<string,string>;selected:string[];onSelect:(ids:string[])=>void;initialView?:string};
const A = new THREE.Matrix3().set(1,0,0,0,0,1,0,-1,0);

function frame(manifest:SceneManifest) {
  const box = new THREE.Box3();
  for (const instance of manifest.part_instances) {
    const definition = manifest.part_definitions.find(d=>d.definition_id===instance.definition_id)!;
    const dims = [definition.finished_mm.length_mm,definition.finished_mm.width_mm,definition.finished_mm.thickness_mm].map(Number);
    const r=instance.rotation_cad_rows;
    const c=[instance.center_mm.x,instance.center_mm.y,instance.center_mm.z].map(Number);
    const half=r.map(row=>row.reduce((s,v,i)=>s+Math.abs(v)*dims[i]/2,0));
    for (const signs of [[-1,-1,-1],[1,1,1]]) box.expandByPoint(new THREE.Vector3(...c.map((v,i)=>(v+signs[i]*half[i])*0.001) as [number,number,number]).applyMatrix3(A));
  }
  return {center:box.getCenter(new THREE.Vector3()),radius:Math.max(box.getSize(new THREE.Vector3()).length()/2,0.1)};
}

function CameraRig({center,radius,view}:{center:THREE.Vector3;radius:number;view:string}) {
  const {camera,invalidate}=useThree();
  useEffect(()=>{
    const direction = view.startsWith('front')?new THREE.Vector3(0,0,1):view.startsWith('side')?new THREE.Vector3(1,0,0):view.startsWith('top')?new THREE.Vector3(0,1,0.001):new THREE.Vector3(1,.65,1);
    camera.position.copy(center).add(direction.normalize().multiplyScalar(radius*3.2));
    camera.up.set(0,1,0);
    camera.lookAt(center);
    camera.updateProjectionMatrix();
    invalidate();
  },[camera,center,radius,view,invalidate]);
  return <OrbitControls makeDefault target={center} minDistance={radius*.5} maxDistance={radius*12}/>;
}

function Board({instance,url,selected,explosion,center,onSelect,onLoad}:{instance:Instance;url:string;selected:boolean;explosion:number;center:THREE.Vector3;onSelect:()=>void;onLoad:(id:string)=>void}) {
  const {scene}=useGLTF(url);
  const copy=useMemo(()=>{
    const clone=scene.clone(true);
    clone.traverse(object=>{
      if(object instanceof THREE.Mesh) {
        object.material=new THREE.MeshStandardMaterial({color:selected?'#246650':'#cab99c',roughness:.78,metalness:0});
      }
    });
    return clone;
  },[scene,selected]);
  useEffect(()=>{onLoad(instance.instance_id+'|'+url);return()=>{copy.traverse(o=>{if(o instanceof THREE.Mesh)(o.material as THREE.Material).dispose();});};},[copy,instance.instance_id,onLoad,url]);
  const matrix=useMemo(()=>{
    const r=instance.rotation_cad_rows;
    const rotation=new THREE.Matrix3().set(...r.flat() as [number,number,number,number,number,number,number,number,number]);
    const converted=A.clone().multiply(rotation).multiply(A.clone().transpose());
    const c=new THREE.Vector3(Number(instance.center_mm.x),Number(instance.center_mm.y),Number(instance.center_mm.z)).multiplyScalar(.001).applyMatrix3(A);
    c.add(c.clone().sub(center).multiplyScalar(explosion));
    const e=converted.elements;
    return new THREE.Matrix4().set(e[0],e[3],e[6],c.x,e[1],e[4],e[7],c.y,e[2],e[5],e[8],c.z,0,0,0,1);
  },[instance,center,explosion]);
  return <group name={instance.instance_id} matrixAutoUpdate={false} matrix={matrix} onPointerDown={event=>{event.stopPropagation();onSelect();}}><primitive object={copy}/></group>;
}

export function Viewer({manifest,urls,selected,onSelect,initialView='iso'}:Props) {
  const [view,setView]=useState(initialView);
  const [hidden,setHidden]=useState<string[]>([]);
  const [isolate,setIsolate]=useState(false);
  const [explosion,setExplosion]=useState(0);
  const [loaded,setLoaded]=useState<string[]>([]);
  const sizing=useMemo(()=>frame(manifest),[manifest]);
  const onLoad=useMemo(()=>(id:string)=>setLoaded(ids=>ids.includes(id)?ids:[...ids,id]),[]);
  const identity=JSON.stringify(manifest);
  useEffect(()=>{setHidden([]);setIsolate(false);setExplosion(0);},[identity]);
  const loadedCount=manifest.part_instances.filter(i=>loaded.includes(i.instance_id+'|'+urls[i.definition_id])).length;
  const shown=manifest.part_instances.filter(i=>!hidden.includes(i.instance_id)&&(!isolate||selected.includes(i.instance_id)));
  return <section className="viewer" aria-label="3D model viewer">
    <div className="viewer-toolbar">
      {['front','side','top','iso'].map(v=><button key={v} onClick={()=>setView(v+Date.now())}>{v==='iso'?'Isometric':v[0].toUpperCase()+v.slice(1)}</button>)}
      <button onClick={()=>setView('iso'+Date.now())}>Fit</button>
      <button disabled={!selected.length} onClick={()=>setHidden(ids=>[...new Set([...ids,...selected])])}>Hide selected</button>
      <button disabled={!selected.length} aria-pressed={isolate} onClick={()=>setIsolate(!isolate)}>Isolate</button>
      <button onClick={()=>{setHidden([]);setIsolate(false);setExplosion(0);}}>Restore</button>
      <label>Explode <input aria-label="Explode view" type="range" min="0" max="1" step="0.1" value={explosion} onChange={e=>setExplosion(Number(e.target.value))}/></label>
    </div>
    <PreviewBoundary><div className="canvas-wrap"><Canvas frameloop="demand" camera={{fov:38,near:.001,far:100}} onPointerMissed={()=>onSelect([])}>
      <color attach="background" args={['#ecece5']}/><ambientLight intensity={1.4}/><directionalLight position={[3,5,3]} intensity={2.1}/><directionalLight position={[-3,2,-1]} intensity={.5}/>
      <CameraRig {...sizing} view={view}/>
      <Suspense fallback={null}>{shown.map(i=><Board key={i.instance_id} instance={i} url={urls[i.definition_id]} selected={selected.includes(i.instance_id)} center={sizing.center} explosion={explosion} onSelect={()=>onSelect([i.instance_id])} onLoad={onLoad}/>)}</Suspense>
    </Canvas></div></PreviewBoundary>
    <div className="viewer-caption"><span data-testid="asset-loaded">{loadedCount} part instances loaded</span><span data-testid="visible-instances">{shown.length} panels visible</span><span>Selection: <strong data-testid="selected-ids">{selected.join(', ')||'None'}</strong></span></div>
  </section>;
}

class PreviewBoundary extends Component<{children:ReactNode},{failed:boolean}>{
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  render(){return this.state.failed?<div className="empty-model" role="status"><h3>3D preview unavailable</h3><p>Your saved dimensions and cut-list downloads remain available. Reopen the saved project to retry the preview.</p></div>:this.props.children;}
}
