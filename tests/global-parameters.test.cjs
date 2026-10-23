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

const annotated=m.seed();const poRate=annotated.find(r=>r.buildType==='PO 建储'&&r.code==='PARM04');poRate.remark='PO促销保障说明';const notes=m.restore(JSON.parse(JSON.stringify(annotated)));assert.equal(notes.find(r=>m.key(r)===m.key(poRate)).remark,'PO促销保障说明');assert.notEqual(notes.find(r=>r.buildType==='STO 建储'&&r.code==='PARM04').remark,'PO促销保障说明');poRate.remark='';assert.equal(m.restore(annotated).find(r=>m.key(r)===m.key(poRate)).remark,'');const old={...poRate};delete old.remark;assert.equal(m.restore([old]).find(r=>m.key(r)===m.key(poRate)).remark,m.seed().find(r=>m.key(r)===m.key(poRate)).remark);assert(m.validate({...poRate,remark:'字'.repeat(501)}).length);assert.deepEqual(m.validate({...poRate,remark:'字'.repeat(500)}),[]);const legacy=[{id:'通用|X',buildType:'通用',code:'X',desc:'通用说明',def:'ON',remark:'原备注'}];assert.equal(m.restoreLegacy(legacy,[{...legacy[0],remark:'通用修改备注'}])[0].remark,'通用修改备注');assert.equal(m.restoreLegacy(legacy,[{...legacy[0],remark:''}])[0].remark,'');assert.equal(m.restoreLegacy(legacy,[{...legacy[0],buildType:'PO 建储',remark:'不得串用'}])[0].remark,'原备注');console.log('PASS 备注修改/清空/刷新恢复、类型隔离、旧数据兼容和通用参数备注保存');
