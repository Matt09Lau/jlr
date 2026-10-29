const assert=require('node:assert/strict'),m=require('../前端设计稿/inventory-strategy.js');
const r={...m.seed('increase')[0],start:'2027-01-01',end:'2027-02-01'};
for(const [start,end] of [['2027-01-15','2027-03-01'],['2027-01-10','2027-01-20'],['2026-12-01','2027-03-01']])assert(m.validate('increase',{...r,start,end},[r]).some(x=>x.includes('交叉')));
assert.equal(m.validate('increase',{...r,start:r.end,end:'2027-03-01'},[r]).length,0);assert.equal(m.validate('increase',r,[r],r.id).length,0);assert.equal(m.validate('increase',{...r,buildType:'STO 建储'},[r]).length,0);
assert.equal(m.effectiveFields({...r,status:'审批通过'},'2027-02-01').expiryStatus,'已失效');assert.equal(m.effectiveFields({...r,status:'审批通过'},'2027-01-31').expiryStatus,'未失效');assert.equal(m.effectiveFields({...r,status:'待审批'},'2027-01-31').expiryStatus,'—');assert.equal(m.effectiveFields({...r,status:'审批通过'},'2027-02-01').effectiveEnd,r.end);
console.log('PASS 有效期交叉、相邻边界、修改排除自身、类型隔离及失效状态');
