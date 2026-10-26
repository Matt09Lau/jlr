(function(root){
'use strict';
const storageKey='cspp-build-global-parameters-v1';
const dictionary=[
 ['PARM01','默认采购LT',60,'integer',0,999,'采购到货提前期，单位天，仅PO使用'],
 ['PARM02','默认库间LT',5,'integer',0,99,'仓间运输提前期，单位天，仅STO使用'],
 ['PARM03','默认增储天数',0,'integer',-1,99,'未命中已批准增储配置时取值，单位天'],
 ['PARM04','默认目标满足率',95,'decimal',0,100,'百分数，95表示95%，最多2位小数'],
 ['PARM05','默认服务水平系数',1.64,'decimal',-99,99,'根据同建储类型的默认目标满足率自动计算，保留2位小数，不允许手工修改'],
 ['PARM06','默认计划周期天数',7,'integer',0,99,'当前建储类型的默认计划周期，单位天'],
 ['PARM07','默认最高风控线系数',3,'decimal',0,10,'最高风控线的默认系数，最多2位小数'],
 ['PARM08','默认最高风控线调整天数',0,'integer',-100,100,'最高线覆盖期调整天数，允许0和负数'],
 ['PARM09','默认最低风控线系数',1,'decimal',0,10,'最低风控线的默认系数，最多2位小数'],
 ['PARM10','默认最低风控线调整天数',0,'integer',-100,100,'最低线覆盖期调整天数，允许0和负数']
].map(([code,desc,def,type,min,max,remark])=>({code,desc,def:String(def),type,min,max,remark}));
function normalQuantile(p){
 if(!(p>0&&p<1))return null;
 const a=[-39.6968302866538,220.946098424521,-275.928510446969,138.357751867269,-30.6647980661472,2.50662827745924],b=[-54.4760987982241,161.585836858041,-155.698979859887,66.8013118877197,-13.2806815528857],c=[-.00778489400243029,-.322396458041136,-2.40075827716184,-2.54973253934373,4.37466414146497,2.93816398269878],d=[.00778469570904146,.32246712907004,2.445134137143,3.75440866190742];
 let q,r,z;if(p<.02425){q=Math.sqrt(-2*Math.log(p));z=(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);}else if(p>1-.02425){q=Math.sqrt(-2*Math.log(1-p));z=-(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);}else{q=p-.5;r=q*q;z=((((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q)/(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1);}return z;
}
function coefficient(rate){const z=normalQuantile(Number(rate)/100);if(z===null)throw new Error('默认目标满足率须大于0且小于100');return z.toFixed(2);}
function derive(rows){return rows.map(row=>{if(row.code!=='PARM05'||!['PO 建储','STO 建储'].includes(row.buildType))return {...row};const rate=rows.find(r=>r.buildType===row.buildType&&r.code==='PARM04');if(!rate||validate(rate).length)throw new Error('缺少有效默认目标满足率：'+row.buildType);return {...row,def:coefficient(rate.def)};});}
function key(row){return row.buildType+'|'+row.code;}
function validateRemark(row){return String(row.remark??'').trim().length>500?['备注最多500字']:[];}
function savedRemark(old,fallback){return Object.hasOwn(old,'remark')&&typeof old.remark==='string'&&!validateRemark(old).length?old.remark:fallback;}
function seed(){return ['PO 建储','STO 建储'].flatMap(buildType=>dictionary.filter(r=>r.code!==(buildType==='PO 建储'?'PARM02':'PARM01')).map(r=>({...r,id:key({...r,buildType}),buildType,editor:'系统初始化',time:''})));}
function validate(row){
 const spec=dictionary.find(r=>r.code===row.code);const errors=validateRemark(row);
 if(!spec)return ['未知参数代码'];
 if(!['PO 建储','STO 建储'].includes(row.buildType))return ['建储类型必填'];
 if(row.code===(row.buildType==='PO 建储'?'PARM02':'PARM01'))errors.push('参数不适用于当前建储类型');
 const text=String(row.def??'').trim(),n=Number(text);
 if(!text)return [...errors,'默认值必填'];
 if(!Number.isFinite(n)||!(/^-?\d+(\.\d+)?$/).test(text))return [...errors,'默认值必须为有效数字'];
 if(spec.type==='integer'&&!Number.isInteger(n))errors.push('默认值必须为整数');
 if(spec.type==='decimal'&&!(/^-?\d+(\.\d{1,2})?$/).test(text))errors.push('默认值最多2位小数');
 if(!(n>spec.min&&n<spec.max))errors.push('默认值须大于'+spec.min+'且小于'+spec.max);
 return errors;
}
function restore(saved){const current=seed();if(!Array.isArray(saved))return derive(current);return derive(current.map(row=>{const old=saved.find(r=>key(r)===key(row));return old&&validate({...row,def:old.def}).length===0?{...row,def:String(old.def),remark:savedRemark(old,row.remark),editor:old.editor||row.editor,time:old.time||''}:row;}));}
function restoreLegacy(rows,saved){return rows.map(row=>{const old=Array.isArray(saved)?saved.find(r=>key(r)===key(row)):null;return old&&String(old.def??'').trim()?{...row,def:String(old.def),remark:savedRemark(old,row.remark),editor:old.editor||row.editor,time:old.time||''}:row;});}
function getDefault(rows,buildType,code){if(code==='PARM05')return Number(coefficient(getDefault(rows,buildType,'PARM04')));const row=rows.find(r=>r.buildType===buildType&&r.code===code);if(!row||validate(row).length)throw new Error('缺少有效全局参数：'+buildType+' '+code);return Number(row.def);}
const api={coefficient,derive,storageKey,dictionary,key,seed,validate,validateRemark,restore,restoreLegacy,getDefault};
if(typeof module!=='undefined'&&module.exports)module.exports=api;root.CsppGlobalParameters=api;
})(typeof window!=='undefined'?window:globalThis);
