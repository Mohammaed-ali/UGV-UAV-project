import { Suspense,useEffect,useMemo,useRef,useState } from 'react';
import { Canvas,useFrame,useLoader,useThree } from '@react-three/fiber';
import { OrbitControls,Html,Line } from '@react-three/drei';
import * as THREE from 'three';
import { ColladaLoader } from 'three/examples/jsm/loaders/ColladaLoader.js';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import type { AssetManifest,Drone,Mission,Scene,SceneObject,Snapshot,Vec3,ViewMode } from './types';
import { droneColor } from './types';

const up=new THREE.Vector3(0,0,1);
function Box({size,position=[0,0,0],color='#425a53',metalness=0,roughness=.8}:{size:Vec3;position?:Vec3;color?:string;metalness?:number;roughness?:number}){
  return <mesh position={position} castShadow receiveShadow><boxGeometry args={size}/><meshStandardMaterial color={color} metalness={metalness} roughness={roughness}/></mesh>;
}
function Tag({id}:{id:number}){
  const map=useLoader(THREE.TextureLoader,`/assets-sim/models/tags/tag_${id}.png`);
  map.colorSpace=THREE.SRGBColorSpace;map.magFilter=THREE.NearestFilter;
  return <mesh position={[0,0,.029]}><planeGeometry args={[.38,.38]}/><meshStandardMaterial map={map} roughness={1}/></mesh>;
}
function Carrier({snapshot,mission,scene}:{snapshot:Snapshot;mission:Mission;scene:Scene}){
  const ref=useRef<THREE.Group>(null);const wheels=useRef<Record<string,THREE.Group>>({});
  useFrame((_,dt)=>{if(ref.current){ref.current.position.lerp(new THREE.Vector3(...snapshot.carrier.position),Math.min(1,dt*12));ref.current.quaternion.slerp(new THREE.Quaternion(...snapshot.carrier.quaternion),Math.min(1,dt*12));}for(const [name,wheel] of Object.entries(wheels.current))wheel.rotation.y=snapshot.wheel_angles?.[name]??0;});
  const rack=scene.rack;
  const loop=Array.from({length:65},(_,i)=>[0,rack.radius*Math.sin(i*Math.PI/32),rack.center_z+rack.half_height*Math.cos(i*Math.PI/32)] as Vec3);
  return <group ref={ref} position={snapshot.carrier.position}>
    <Box size={[rack.chassis_size,rack.chassis_size,.5]} color="#29403a"/><Box size={[rack.deck_size,rack.deck_size,.12]} position={[0,0,.31]} color="#60716a"/>
    <Box size={[.04,2.4,.09]} position={[rack.chassis_size/2+.02,0,.09]} color="#dcf7bd"/><Box size={[.04,2.4,.09]} position={[-rack.chassis_size/2-.02,0,.09]} color="#b47155"/>
    {[-1.48,1.48].map(x=><group key={x} position={[x,0,0]}>
      <Line points={loop} color="#526960" lineWidth={3}/>
      {[-1.35,1.35].map(y=><Box key={y} size={[.075,.075,1.94]} position={[0,y,1.29]} color="#52665d"/>)}
      <Box size={[.08,2.75,.07]} position={[0,0,2.29]} color="#71856e"/>
    </group>)}
    {(mission.wheels===4?[-rack.wheel_x,rack.wheel_x]:[-rack.wheel_x,0,rack.wheel_x]).flatMap(x=>[rack.wheel_y,-rack.wheel_y].map(y=>{
      const side=y>0?'left':'right';const name=`wheel_${side}_${String(x).replace('.','_').replace('-','m')}_joint`;
      return <group position={[x,y,-.36]} key={name}><group ref={g=>{if(g)wheels.current[name]=g;}}>
        <mesh castShadow><cylinderGeometry args={[.38,.38,.3,24]}/><meshStandardMaterial color="#252b29" roughness={.94}/></mesh>
        <mesh position={[0,y>0?.16:-.16,0]}><cylinderGeometry args={[.24,.24,.025,20]}/><meshStandardMaterial color="#84958d" metalness={.55} roughness={.45}/></mesh>
        {Array.from({length:12},(_,i)=>{const a=i*Math.PI/6;return <group key={i} position={[.375*Math.cos(a),0,.375*Math.sin(a)]} rotation={[0,-a,0]}><Box size={[.03,.31,.055]} color="#35433c"/></group>;})}
        {[0,1,2,3,4,5].map(i=><mesh key={i} position={[.15*Math.cos(i*Math.PI/3),y>0?.18:-.18,.15*Math.sin(i*Math.PI/3)]}><sphereGeometry args={[.027,6,6]}/><meshStandardMaterial color="#d6dfd0"/></mesh>)}
      </group></group>;
    }))}
    {(['upper','lower'] as const).map(level=>{
      const t=snapshot.carousel?.trays[level]??{y:0,z:level==='upper'?rack.upper_z:rack.lower_z};
      return <group key={level} position={[0,t.y,t.z]}>
        <Box size={[2.65,2.65,.08]} color={level==='upper'?'#738b73':'#738f99'}/>
        <Box size={[.045,2.62,.065]} position={[1.31,0,.055]} color={level==='upper'?'#d2e991':'#a9d5e4'}/>
        <Box size={[.045,2.62,.065]} position={[-1.31,0,.055]} color={level==='upper'?'#d2e991':'#a9d5e4'}/>
        {scene.slots.filter(s=>s.level===level).map(s=><group key={s.id} position={[s.x,s.y,rack.pad_z]}>
          <Box size={[1.04,1.04,.055]} color="#c0cbb8"/>
          <Suspense fallback={null}><Tag id={s.tag_id}/></Suspense>
        </group>)}
      </group>;
    })}
    <Html position={[0,0,3.05]} center distanceFactor={13} zIndexRange={[5,0]}><div className="world-label carrier-label"><span className="status-dot"/> CARRIER 01</div></Html>
  </group>;
}
function Aircraft({drone,selected,onSelect}:{drone:Drone;selected:boolean;onSelect:()=>void}){
  const ref=useRef<THREE.Group>(null);const rotors=useRef<THREE.Mesh[]>([]);
  useFrame((_,dt)=>{if(ref.current){ref.current.position.lerp(new THREE.Vector3(...drone.position),Math.min(1,dt*14));ref.current.quaternion.slerp(new THREE.Quaternion(...drone.quaternion),Math.min(1,dt*12));}if(drone.armed)rotors.current.forEach((r,i)=>r.rotation.z+=dt*(i%2?35:-35));});
  const airborne=!['STORED','DOCKED','PREPARING','ARMING','RELEASING'].includes(drone.state);
  return <group ref={ref} position={drone.position} onClick={e=>{e.stopPropagation();onSelect();}}>
    <Box size={[.28,.22,.09]} color={selected?'#dcf38f':'#e0e4d4'} roughness={.4}/><Box size={[.1,.12,.05]} position={[.02,0,.065]} color="#405657"/>
    {[-1,1].flatMap((x,xi)=>[-1,1].map((y,yi)=><group key={`${x}${y}`}>
      <mesh position={[x*.09,y*.09,.015]} rotation={[0,0,x*y*Math.PI/4]} castShadow><boxGeometry args={[.26,.025,.025]}/><meshStandardMaterial color="#3d4845"/></mesh>
      <mesh position={[x*.174,y*.174,.04]} rotation={[Math.PI/2,0,0]}><cylinderGeometry args={[.034,.034,.05,10]}/><meshStandardMaterial color="#7f8c84"/></mesh>
      <mesh position={[x*.174,y*.174,.075]} ref={el=>{if(el)rotors.current[xi*2+yi]=el;}}><boxGeometry args={[.28,.026,.008]}/><meshStandardMaterial color="#263a32" transparent opacity={drone.armed?.5:1}/></mesh>
      <Box size={[.02,.02,.21]} position={[x*.1,y*.11,-.12]} color="#53645a"/>
    </group>))}
    <Box size={[.25,.016,.016]} position={[0,-.132,-.22]} color="#66746b"/><Box size={[.25,.016,.016]} position={[0,.132,-.22]} color="#66746b"/>
    {airborne&&<Html position={[0,0,.6]} center distanceFactor={16} zIndexRange={[8,0]}><div className={`world-label drone-label ${selected?'selected':''}`}><span style={{background:droneColor(drone.state)}} className="status-dot"/>{drone.id.toUpperCase()}</div></Html>}
    {selected&&<mesh position={[0,0,-.24]}><ringGeometry args={[.42,.46,48]}/><meshBasicMaterial color="#d5f16a" side={THREE.DoubleSide}/></mesh>}
  </group>;
}
function AssetPart({part}:{part:{file:string;color:[number,number,number]}}){
  const file=useLoader(ColladaLoader,part.file);
  const clone=useMemo(()=>{const c=file.scene.clone(true);c.traverse(o=>{if(o instanceof THREE.Mesh){o.material=new THREE.MeshStandardMaterial({color:new THREE.Color(...part.color),roughness:.82});o.castShadow=true;o.receiveShadow=true;}});return c;},[file,part]);
  // Compose the conversion with ColladaLoader's root rotation. Setting rotation
  // on the primitive would overwrite that rotation and lay Z-up assets sideways.
  return <group rotation={[Math.PI/2,0,0]}><primitive object={clone}/></group>;
}
function FallbackPerson(){return <group><mesh position={[0,0,1.5]}><sphereGeometry args={[.13,10,10]}/><meshStandardMaterial color="#bc8e6b"/></mesh><Box size={[.36,.23,.64]} position={[0,0,1.04]} color="#607d89"/>{[-.11,.11].map(x=><Box key={x} size={[.12,.16,.72]} position={[x,0,.36]} color="#394d51"/>)}</group>;}
function ObjectModel({obj,assets,onTarget}:{obj:SceneObject;assets:AssetManifest;onTarget:(kind:string)=>void}){
  if(obj.kind==='building')return <group position={[obj.x,obj.y,0]}>
    <Box size={[obj.sx!,obj.sy!,obj.sz!]} position={[0,0,obj.sz!/2]} color={['#b9b8a5','#a2b1a7','#bdac98','#c1c3b5'][obj.variant??0]}/>
    <Box size={[obj.sx!+.4,obj.sy!+.4,.3]} position={[0,0,obj.sz!+.1]} color="#929d92"/>
    <Box size={[obj.sx!*.45,obj.sy!*.4,.7]} position={[0,0,obj.sz!+.6]} color="#a3a99b"/>
    {Array.from({length:Math.max(1,Math.floor(obj.sx!/2.5))},(_,i)=><group key={i}>
      <Box size={[1.15,.04,1.45]} position={[-obj.sx!/2+1.6+i*2.4,-obj.sy!/2-.03,2.7]} color="#70898a"/>
      {obj.sz!>6&&<Box size={[1.15,.04,1.45]} position={[-obj.sx!/2+1.6+i*2.4,-obj.sy!/2-.03,5.6]} color="#70898a"/>}
    </group>)}
  </group>;
  const name=obj.kind==='person'?`human_mesh_${obj.variant??0}`:`${obj.kind}_mesh_0`;
  return <group position={[obj.x,obj.y,obj.z]} rotation={[0,0,obj.yaw]} onClick={e=>{e.stopPropagation();onTarget(obj.kind);}}>
    <Suspense fallback={obj.kind==='person'?<FallbackPerson/>:<Box size={[3.8,1.8,1.4]} position={[0,0,.7]} color="#657c78"/>}>
      {assets[name]?.map(part=><AssetPart key={part.file} part={part}/>)}
    </Suspense>
  </group>;
}
function Cameras({mode,snapshot,selected,fitRequest}:{mode:ViewMode;snapshot:Snapshot;selected:string;fitRequest:number}){
  const controls=useRef<OrbitControlsImpl>(null);const {camera}=useThree();const last=useRef('');
  useEffect(()=>{camera.up.copy(up);},[camera]);
  useEffect(()=>{last.current='';},[fitRequest]);
  useFrame((_,dt)=>{
    if(!controls.current)return;
    const signature=`${mode}/${mode==='drone'?selected:''}/${fitRequest}`;
    const p=new THREE.Vector3(...(mode==='drone'?(snapshot.drones.find(d=>d.id===selected)?.position??snapshot.carrier.position):snapshot.carrier.position));
    if(mode==='carrier'||mode==='dock')p.z+=1.4;
    if(signature!==last.current){
      const offsets:Record<ViewMode,Vec3>={orbit:[38,-52,42],top:[0,-.1,150],carrier:[9,-12,7],drone:[5,-7,4],dock:[6,-8,5]};
      camera.position.copy(p.clone().add(new THREE.Vector3(...offsets[mode])));controls.current.target.copy(p);controls.current.update();last.current=signature;
    }else if(['carrier','drone','dock'].includes(mode)){
      const delta=p.clone().sub(controls.current.target);camera.position.add(delta.multiplyScalar(Math.min(1,dt*4)));controls.current.target.lerp(p,Math.min(1,dt*4));
    }
  });
  return <OrbitControls ref={controls} makeDefault maxPolarAngle={Math.PI/2-.03} minDistance={2} maxDistance={290} enableDamping dampingFactor={.08}/>;
}
function FrameMeter({report}:{report:(n:number)=>void}){const frames=useRef(0),elapsed=useRef(0);useFrame((_,dt)=>{frames.current++;elapsed.current+=dt;if(elapsed.current>=1){report(Math.round(frames.current/elapsed.current));frames.current=0;elapsed.current=0;}});return null;}

export default function World({mission,scene,assets,snapshot,selected,selectDrone,selectedStop,selectStop,view,fitRequest,editing,onPlace,onTarget,reportFps}:{mission:Mission;scene:Scene;assets:AssetManifest;snapshot:Snapshot;selected:string;selectDrone:(id:string)=>void;selectedStop:string;selectStop:(id:string)=>void;view:ViewMode;fitRequest:number;editing:boolean;onPlace:(x:number,y:number,add:boolean)=>void;onTarget:(kind:string)=>void;reportFps:(n:number)=>void}){
  const points:Vec3[]=[[mission.start.x,mission.start.y,.08],...mission.stops.map(s=>[s.x,s.y,.08] as Vec3)];
  const [showGrid]=useState(true);
  return <Canvas shadows={mission.graphics_quality!=='low'} dpr={[1,mission.graphics_quality==='high'?2:mission.graphics_quality==='low'?1:1.5]} camera={{position:[0,-50,40],up:[0,0,1],fov:42,near:.05,far:430}} gl={{antialias:true,alpha:false}}>
    <color attach="background" args={['#dce4d9']}/><fog attach="fog" args={['#dce4d9',190,380]}/>
    <ambientLight intensity={1.2}/><hemisphereLight args={['#eef3e6','#7e896f',1.1]} position={[0,0,50]}/>
    <directionalLight castShadow position={[-25,-35,65]} intensity={2.3} shadow-mapSize={[mission.graphics_quality==='high'?2048:1024,mission.graphics_quality==='high'?2048:1024]} shadow-camera-left={-70} shadow-camera-right={70} shadow-camera-top={70} shadow-camera-bottom={-70} shadow-camera-near={1} shadow-camera-far={180} shadow-bias={-.0003}/>
    <mesh receiveShadow onPointerDown={e=>{if(editing){e.stopPropagation();onPlace(Math.round(e.point.x*2)/2,Math.round(e.point.y*2)/2,e.shiftKey);}}}>
      <planeGeometry args={[scene.size+10,scene.size+10]}/><meshStandardMaterial color="#abb093" roughness={1}/>
    </mesh>
    {showGrid&&<gridHelper args={[scene.size,48,'#a8b09b','#b0b79e']} rotation={[Math.PI/2,0,0]} position={[0,0,.014]}/>}
    {editing&&<Line points={[[-108,-108,.045],[108,-108,.045],[108,108,.045],[-108,108,.045],[-108,-108,.045]]} color="#54776b" lineWidth={2} dashed dashSize={1} gapSize={.7}/>}
    {scene.roads.map(road=><group key={road.id} position={[road.x,road.y,0]}>
      <mesh position={[0,0,.017]} receiveShadow><planeGeometry args={[road.sx+3.5,road.sy+3.5]}/><meshStandardMaterial color="#bbc0b1" roughness={1}/></mesh>
      <mesh position={[0,0,.021]} receiveShadow><planeGeometry args={[road.sx,road.sy]}/><meshStandardMaterial color="#788480" roughness={1}/></mesh>
      {Array.from({length:45},(_,i)=><mesh position={road.sx>road.sy?[(i-22)*5,0,.028]:[0,(i-22)*5,.028]} key={i}><planeGeometry args={road.sx>road.sy?[2.4,.12]:[.12,2.4]}/><meshBasicMaterial color="#e0e2c9"/></mesh>)}
    </group>)}
    {scene.objects.map(o=><ObjectModel key={o.id} obj={o} assets={assets} onTarget={onTarget}/>)}
    <Line points={points} color="#dcedad" lineWidth={3} dashed={false}/>
    {mission.stops.map((s,i)=><group key={s.id} position={[s.x,s.y,.05]} onClick={e=>{e.stopPropagation();selectStop(s.id);}}>
      <mesh rotation={[0,0,0]}><ringGeometry args={[1.45,1.52,64]}/><meshBasicMaterial color={s.id===selectedStop?'#fbffe6':'#dce5c2'}/></mesh>
      <mesh><circleGeometry args={[1.44,64]}/><meshBasicMaterial color="#d5ef86" transparent opacity={.1}/></mesh>
      <Html position={[0,0,.2]} center zIndexRange={[10,0]}><button className={`stop-pin ${s.id===selectedStop?'active':''}`} onClick={()=>selectStop(s.id)}>{String.fromCharCode(65+i)}</button></Html>
      {s.id===selectedStop&&<Line points={Array.from({length:65},(_,j)=>[s.search_radius*Math.cos(j*Math.PI/32),s.search_radius*Math.sin(j*Math.PI/32),.035] as Vec3)} color="#e4efc9" dashed dashSize={.5} gapSize={.5} lineWidth={1}/>}
    </group>)}
    <Carrier snapshot={snapshot} mission={mission} scene={scene}/>
    {snapshot.drones.map(d=><Aircraft key={d.id} drone={d} selected={d.id===selected} onSelect={()=>selectDrone(d.id)}/>)}
    {snapshot.tracks.filter(t=>t.position).map(t=><Html key={t.id} position={t.position!} center><div className="world-label detection-label">{t.class.toUpperCase()} · {(t.confidence*100).toFixed(0)}%</div></Html>)}
    <Cameras mode={view} snapshot={snapshot} selected={selected} fitRequest={fitRequest}/><FrameMeter report={reportFps}/>
  </Canvas>;
}
