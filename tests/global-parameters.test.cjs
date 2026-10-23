const assert=require('node:assert/strict');
const m=require('../前端设计稿/global-parameters.js');
const rows=m.seed();assert.equal(rows.length,18);assert.equal(new Set(rows.map(m.key)).size,18);
assert.equal(m.getDefault(rows,'PO 建储','PARM01'),60);assert.equal(m.getDefault(rows,'STO 建储','PARM02'),5);
const po=rows.find(r=>r.buildType==='PO 建储'&&r.code==='PARM06');po.def='14';
assert.equal(m.getDefault(rows,'PO 建储','PARM06'),14);assert.equal(m.getDefault(rows,'STO 建储','PARM06'),7);
assert.throws(()=>m.getDefault(rows,'STO 建储','PARM01'));
for(const r of rows)assert.deepEqual(m.validate(r),[]);
for(const [code,good,bad] of [['PARM03','0','-1'],['PARM04','95.12','100'],['PARM05','1.65','1.656'],['PARM06','7','7.5'],['PARM08','-99','-100'],['PARM07','3','10']]){
 const row=rows.find(r=>r.code===code);assert.deepEqual(m.validate({...row,def:good}),[]);assert(m.validate({...row,def:bad}).length);
 assert(m.validate({...row,def:' '}).length);
}
const restored=m.restore(JSON.parse(JSON.stringify(rows)));assert.equal(m.getDefault(restored,'PO 建储','PARM06'),14);assert.equal(m.getDefault(restored,'STO 建储','PARM06'),7);
assert.equal(m.restore([{...po,def:'bad'}]).find(r=>m.key(r)===m.key(po)).def,'7');
assert.equal(m.restore([{code:'PARM06',def:22}]).find(r=>m.key(r)===m.key(po)).def,'7');
console.log('PASS 18条配置唯一、类型隔离、默认值校验、持久化恢复及无跨类型回退');
