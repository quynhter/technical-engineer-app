import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createPowerSearchConfig} from '@astryxdesign/core/PowerSearch';
import {filterValue} from '../src/table-values.js';

test('PowerSearch compares Russian quantities numerically and calendar dates chronologically',()=>{
 const {config,applyFilters}=createPowerSearchConfig([{key:'quantity',type:'number'},{key:'date',type:'date'}]);
 const rows=[['1 234,5','05.11.2026'],['100','13.11.2026'],['—','Не указана'],['0','01.10.2026']].map(([quantity,date],id)=>({id,quantity:filterValue(quantity,'number'),date:filterValue(date,'date')}));
 assert.deepEqual(config.fields[0].operators.map(op=>op.key),['equals','not_equals','greater_than','less_than','greater_than_or_equal','less_than_or_equal']);
 assert.deepEqual(config.fields[1].operators.map(op=>op.key),['before','after','between']);
 const number=(operator,value)=>({field:'quantity',operator,value:{type:'float',value}});
 assert.deepEqual(applyFilters([number('greater_than',100)],rows).map(r=>r.id),[0]);
 assert.deepEqual(applyFilters([number('less_than_or_equal',100)],rows).map(r=>r.id),[1,3]);
 assert.deepEqual(applyFilters([number('equals',0)],rows).map(r=>r.id),[3]);
 const date=(operator,text)=>({field:'date',operator,value:{type:'date_absolute',unixSeconds:filterValue(text,'date').getTime()/1000}});
 assert.deepEqual(applyFilters([date('before','10.11.2026')],rows).map(r=>r.id),[0,3]);
 assert.deepEqual(applyFilters([date('after','10.11.2026'),number('equals',100)],rows).map(r=>r.id),[1]);
});
