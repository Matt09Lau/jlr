/* 已确认的演示仓网。CN00在JB09链路为区域节点，在自身链路为中心节点。 */
(function(root){
 const warehouses=[
  {code:'CJDC',name:'CJDC 中心仓',type:2,roles:['中心仓']},
  {code:'JB09',name:'JB09（RDC）中心仓',type:2,roles:['中心仓']},
  {code:'CN00',name:'CN00',type:2,roles:['中心仓','区域仓']},
  ...['CJV0','CJV1','CJV2','CJV3','CN01','CN02','CN03'].map(code=>({code,name:code+' 区域仓',type:1,roles:['区域仓']}))
 ];
 const routes=[...['CJV0','CJV1','CJV2','CJV3'].map(to=>({from:'CJDC',to})),...['CN00','CN01','CN02','CN03'].map(to=>({from:'JB09',to})),...['CN01','CN02','CN03'].map(to=>({from:'CN00',to}))];
 const names=Object.fromEntries(warehouses.map(w=>[w.code,w.name]));
 const api={warehouses,routes,names,centers:['CJDC','JB09','CN00'],regions:['CJV0','CJV1','CJV2','CJV3','CN00','CN01','CN02','CN03']};
 root.CSPPWarehouseNetwork=api;if(typeof module==='object')module.exports=api;
})(typeof window==='object'?window:globalThis);
