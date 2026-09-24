import { describe, expect, it } from 'vitest';
import { baselineWorkspace, editCells, effectiveAbility } from '../shared/game/abilities/workshop/workspace';
import { assertWorkspace } from '../shared/game/abilities/workshop/validation';
import { gridRows, queryRows, WorkspaceHistory, type GridView } from '../shared/game/abilities/workshop/grid';
import { evaluateRules, conditionalAmount } from '../shared/game/abilities/workshop/conditions';

const baseline = () => baselineWorkspace('a'.repeat(40), 'b'.repeat(64));
const view = (): GridView => ({ name:'Damage', columns:['class','ability','damage'], widths:{damage:150}, pinned:['class','ability'], filters:{}, sort:[], classes:[], compact:false });
describe('ability spreadsheet operations', () => {
  it('combines filters with AND and choices with OR; keeps zero distinct from absent', () => {
    const workspace=baseline(); workspace.abilities[0].effects[0].amount={min:0,max:0};
    const rows=gridRows(workspace), saved=view();
    saved.filters={class:{kind:'values',values:[workspace.classes[0].name,workspace.classes[1].name]},damage:{kind:'number',operator:'eq',value:0}};
    expect(queryRows(rows,saved).map(row=>row.ability.id)).toEqual([workspace.abilities[0].id]);
    saved.filters.damage={kind:'empty',empty:true};
    expect(queryRows(rows,saved).every(row=>row.values.damage===undefined)).toBe(true);
    expect(JSON.parse(JSON.stringify(saved))).toEqual(saved);
  });
  it('validates a complete rectangle before committing and provides undo/redo', () => {
    const data=baseline(), history=new WorkspaceHistory(data), a=data.assignments[0], b=data.assignments[1];
    const selected=new Set([a.id,b.id]);
    expect(()=>history.edit([{assignmentId:a.id,path:'cooldownSec',operation:'set',value:12},{assignmentId:b.id,path:'cooldownSec',operation:'set',value:-5}],selected)).toThrow();
    expect(history.current).toEqual(data);
    expect(()=>history.edit([{assignmentId:a.id,path:'cooldownSec',operation:'set',value:12},{assignmentId:a.id,path:'cooldownSec',operation:'set',value:13}],selected)).toThrow('repeats');
    expect(history.current).toEqual(data);
    history.edit([{assignmentId:a.id,path:'cooldownSec',operation:'multiply',value:2},{assignmentId:b.id,path:'cooldownSec',operation:'add',value:1}],selected);
    expect(history.current.assignments[0].overrides).toHaveLength(1);
    expect(history.undo()).toBe(true); expect(history.current).toEqual(data);
    expect(history.redo()).toBe(true);
    const reset=editCells(history.current,[{assignmentId:a.id,path:'cooldownSec',operation:'reset'}],selected);
    expect(reset.assignments[0].overrides).toEqual([]);
  });
  it('queries a valid 5,000-assignment catalog deterministically', () => {
    const data=baseline(), template=structuredClone(data.abilities[0]);
    template.resource={manaCost:0,careerBuild:0,careerCost:0};
    data.abilities=Array.from({length:209},(_,i)=>({...structuredClone(template),id:`custom.spell_${i}`,name:`Spell ${i}`,cooldownSec:i}));
    data.assignments=data.abilities.flatMap((ability,i)=>data.classes.map(c=>({id:`${c.id}:${ability.id}`,classId:c.id,abilityId:ability.id,unlockLevel:1,displayOrder:i,presentations:{},overrides:[]}))).slice(0,5000);
    assertWorkspace(data);
    const saved=view(); saved.filters.cooldownSec={kind:'number',operator:'between',value:100,upper:105}; saved.sort=[{column:'cooldownSec',descending:true}];
    const matches=queryRows(gridRows(data),saved);
    expect(matches).toHaveLength(144); expect(matches[0].ability.cooldownSec).toBe(105); expect(matches.at(-1)!.ability.cooldownSec).toBe(100);
  });
  it('uses edited timing while reset preserves the original timing convention', () => {
    const data=baseline(), a=data.assignments[0], selected=new Set([a.id]);
    const edited=editCells(data,[{assignmentId:a.id,path:'timing/castSec',operation:'set',value:2}],selected);
    expect(effectiveAbility(edited,edited.assignments[0]).authoredTiming).toBe(true);
    const reset=editCells(edited,[{assignmentId:a.id,path:'timing/castSec',operation:'reset'}],selected);
    expect(effectiveAbility(reset,reset.assignments[0]).authoredTiming).toBeUndefined();
  });
  it('treats prototype-like stable IDs as data, without mutating global prototypes', () => {
    const result=evaluateRules([{id:'r',name:'r',event:'application',condition:{kind:'all',children:[{kind:'hot',subject:'caster',source:'self',not:true}]},actions:[{kind:'flat',effectId:'__proto__',value:10}]}], 'application', {now:0,caster:{id:'caster',realm:'aegis',alive:true,statuses:[]}});
    expect(conditionalAmount(100,'__proto__',[result])).toBe(110);
    expect(({} as {flat?:number}).flat).toBeUndefined();
  });
});
