(function(root){
 function expand(form,materials,warehouses,existing){
  const parts=[...new Set(form.parts||[])];
  if(!parts.length)return {error:'请选择至少一个配件'};
  const wh=warehouses.find(w=>w.code===form.wh);
  if(!wh)return {error:'请选择主数据中有效的仓库'};
  if(!['允许','禁止'].includes(form.flag))return {error:'请选择备货标识'};
  const remark=String(form.remark||'').trim();if(remark.length>500)return {error:'备注最多500字'};
  if(parts.some(p=>!materials.some(m=>m.material_code===p)))return {error:'配件必须存在于配件主数据'};
  const duplicates=parts.filter(p=>existing.some(r=>r.code===p&&r.whCode===wh.code));
  if(duplicates.length)return {error:'以下配件在所选仓库已有规则，请移除后保存：'+duplicates.join('、')};
  return {rows:parts.map(p=>({code:p,name:materials.find(m=>m.material_code===p).material_name,whCode:wh.code,whName:wh.name,stock_flag:form.flag,remark}))};
 }
 root.CSPPStockingRules={expand};if(typeof module==='object')module.exports={expand};
})(typeof window==='object'?window:globalThis);
