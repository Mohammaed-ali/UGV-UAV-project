import {describe,it,expect} from 'vitest';
import {routeBoundsError,formatApiError} from './validation';
import type {Mission} from './types';
describe('route boundary errors',()=>{
  const mission={start:{x:-28,y:-22},stops:[{label:'Alpha',x:-33,y:117.5}]} as Mission;
  it('identifies the stop, axis, input, units and permitted range',()=>{
    expect(routeBoundsError(mission)).toContain('Alpha: North / Y = 117.5 m');
    expect(routeBoundsError(mission)).toContain('−108 to +108 m');
  });
  it('accepts either boundary and rejects beyond it',()=>{
    expect(routeBoundsError({...mission,stops:[{...mission.stops[0],x:-108,y:108}]})).toBeNull();
    expect(routeBoundsError({...mission,stops:[{...mission.stops[0],x:-108.5,y:0}]})).toContain('East / X');
  });
  it('keeps the backend field location in the operator error',()=>{
    expect(formatApiError([{loc:['body','stops',0,'y'],msg:'Input should be less than or equal to 108'}],JSON.stringify(mission)))
      .toBe('Alpha: North / Y: Input should be less than or equal to 108 (meters from map origin)');
  });
});
