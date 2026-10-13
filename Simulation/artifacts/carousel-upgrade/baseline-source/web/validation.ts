import type { Mission } from './types';
export const ROUTE_LIMIT=68;
export function routeBoundsError(mission:Mission):string|null {
  for(const point of [{...mission.start,label:'Start'},...mission.stops]) {
    for(const axis of ['x','y'] as const) {
      const value=point[axis];
      if(!Number.isFinite(value)||Math.abs(value)>ROUTE_LIMIT)
        return `${point.label}: ${axis==='x'?'East / X':'North / Y'} = ${value} m. Enter a value from −68 to +68 m, inside the marked route boundary.`;
    }
  }
  return null;
}
export function formatApiError(detail:unknown,body?:string):string {
  if(typeof detail==='string')return detail;
  if(!Array.isArray(detail))return 'Request failed.';
  let payload:Record<string,unknown>={};
  try {if(body)payload=JSON.parse(body);}catch { /* No parsed payload is needed for a generic error. */ }
  return detail.map((error:{loc?:Array<string|number>;msg:string})=>{
    const path=error.loc??[];const stopIndex=path.indexOf('stops');
    const stops=payload.stops as Mission['stops']|undefined;
    const stop=stopIndex>=0?stops?.[Number(path[stopIndex+1])]:undefined;
    const field=String(path.at(-1)??'input');
    const label=field==='x'?'East / X':field==='y'?'North / Y':field.replaceAll('_',' ');
    return `${stop?`${stop.label}: `:''}${label}: ${error.msg.replace('Value error, ','')}${['x','y'].includes(field)?' (meters from map origin)':''}`;
  }).join(' ');
}
