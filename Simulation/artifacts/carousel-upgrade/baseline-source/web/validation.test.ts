import {describe,it,expect} from 'vitest';
import {routeBoundsError,formatApiError} from './validation';
import type {Mission} from './types';
describe('route boundary errors',()=>{
  const mission={start:{x:-28,y:-22},stops:[{label:'Alpha',x:-33,y:77.5}]} as Mission;
  it('identifies the stop, axis, input, units and permitted range',()=>{
    expect(routeBoundsError(mission)).toContain('Alpha: North / Y = 77.5 m');
    expect(routeBoundsError(mission)).toContain('−68 to +68 m');
  });
  it('accepts either boundary and rejects beyond it',()=>{
    expect(routeBoundsError({...mission,stops:[{...mission.stops[0],x:-68,y:68}]})).toBeNull();
    expect(routeBoundsError({...mission,stops:[{...mission.stops[0],x:-68.5,y:0}]})).toContain('East / X');
  });
  it('keeps the backend field location in the operator error',()=>{
    expect(formatApiError([{loc:['body','stops',0,'y'],msg:'Input should be less than or equal to 68'}],JSON.stringify(mission)))
      .toBe('Alpha: North / Y: Input should be less than or equal to 68 (meters from map origin)');
  });
});
