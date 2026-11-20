/* 兜底规则配置页（分层版·组内自定义条件分档）：
 *   规则组(组级适用范围 AND) → 组内条件分档(任意字段 AND/OR) → 首个命中生效。
 * 每个规则组各自持有独立的分档列表 tiers，组间完全隔离。分档条件由业务自定义，
 * 可基于销量、近一年销售频次、仓库编码、销售价等任意注册字段；不含专门的价格分档机制
 * （无 tierMode / tierField / 共享表 / 价格边界校验），也不预置生产规则。
 * 「近一年销售频次」采用指标宽表权威口径（按配件号统计近 12 月销售数量>0 且非空的订单行数）。
 * 页面首次打开展示的 4 组仅为示例数据，业务可自行增删改；不提供一键还原入口。
 * 数据仅保存在当前浏览器，不连接原系统。档位/范围条件字段仅来自三类数据源：配件主数据 / 仓库主数据 / 指标宽表
 * （指标范围以《迭代 4：库存策略》4.3 节为准）；全局参数类字段（LT、目标满足率、风控系数、备货标识等）不纳入。
 */
(function(root){
'use strict';
const { ref, reactive, computed } = root.Vue || {};

const OP = { EQ:'=', NE:'≠', GT:'>', GE:'≥', LT:'<', LE:'≤', BETWEEN:'区间', IN:'属于', NOT_IN:'不属于', IS_NULL:'为空', IS_NOT_NULL:'不为空' };
const ALL_OPS = ['EQ','NE','GT','GE','LT','LE','BETWEEN','IN','NOT_IN','IS_NULL','IS_NOT_NULL'];

// 可配置字段清单：三类来源——配件主数据 / 仓库主数据 / 指标宽表（历史需求、兜底频次、预测、库存供应）
const FIELD_REGISTRY = [
  { fieldName:'abcClassification', fieldLabel:'ABC分类', fieldGroup:'配件主数据', valueType:'ENUM', enumValues:[['S0','S0'],['S1','S1'],['S2','S2'],['S3','S3'],['A','A'],['B','B'],['C','C'],['D','D'],['E','E']], supportedOps:['EQ','NE','IN','NOT_IN'] },
  { fieldName:'warehouseCode', fieldLabel:'仓库编码', fieldGroup:'仓库主数据', valueType:'STRING', enumValues:null, supportedOps:['EQ','NE','IN','NOT_IN','IS_NULL','IS_NOT_NULL'] },
  { fieldName:'xyzClassification', fieldLabel:'XYZ分类', fieldGroup:'配件主数据', valueType:'ENUM', enumValues:[['X','X'],['Y','Y'],['Z','Z']], supportedOps:['EQ','NE','IN','NOT_IN'] },
  { fieldName:'volumeClassification', fieldLabel:'体积分类', fieldGroup:'配件主数据', valueType:'ENUM', enumValues:[['S','小'],['M','中'],['L','大']], supportedOps:['EQ','NE','IN','NOT_IN'] },
  { fieldName:'moneyClassification', fieldLabel:'金额分类', fieldGroup:'配件主数据', valueType:'ENUM', enumValues:[['H','高'],['M','中'],['L','低']], supportedOps:['EQ','NE','IN','NOT_IN'] },
  { fieldName:'salesPrice', fieldLabel:'销售价', fieldGroup:'配件主数据', valueType:'NUMBER', enumValues:null, supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN','IS_NULL'] },
  { fieldName:'minPackageQty', fieldLabel:'最小包装量', fieldGroup:'配件主数据', valueType:'NUMBER', enumValues:null, supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'minOrderQty', fieldLabel:'起订量', fieldGroup:'配件主数据', valueType:'NUMBER', enumValues:null, supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'grossWeight', fieldLabel:'毛重', fieldGroup:'配件主数据', valueType:'NUMBER', enumValues:null, supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'netWeight', fieldLabel:'净重', fieldGroup:'配件主数据', valueType:'NUMBER', enumValues:null, supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'potentialUnitDown', fieldLabel:'无法行驶', fieldGroup:'配件主数据', valueType:'BOOLEAN', enumValues:[['true','是'],['false','否']], supportedOps:['EQ','NE'] },
  { fieldName:'isCutOffPart', fieldLabel:'是否断供件', fieldGroup:'配件主数据', valueType:'BOOLEAN', enumValues:[['true','是'],['false','否']], supportedOps:['EQ','NE'] },
  { fieldName:'isBreakPointPart', fieldLabel:'是否断点件', fieldGroup:'配件主数据', valueType:'BOOLEAN', enumValues:[['true','是'],['false','否']], supportedOps:['EQ','NE'] },
  { fieldName:'isDangerousGoods', fieldLabel:'是否危险品', fieldGroup:'配件主数据', valueType:'BOOLEAN', enumValues:[['true','是'],['false','否']], supportedOps:['EQ','NE'] },
  { fieldName:'isExpiryPart', fieldLabel:'是否效期件', fieldGroup:'配件主数据', valueType:'BOOLEAN', enumValues:[['true','是'],['false','否']], supportedOps:['EQ','NE'] },
  { fieldName:'partsClassify', fieldLabel:'配件分类', fieldGroup:'配件主数据', valueType:'STRING', enumValues:null, supportedOps:['EQ','NE','IN','NOT_IN'] },
  { fieldName:'tier1Category', fieldLabel:'一级分类', fieldGroup:'配件主数据', valueType:'STRING', enumValues:null, supportedOps:['EQ','NE','IN','NOT_IN'] },
  { fieldName:'tier2Category', fieldLabel:'二级分类', fieldGroup:'配件主数据', valueType:'STRING', enumValues:null, supportedOps:['EQ','NE','IN','NOT_IN'] },
  { fieldName:'planner', fieldLabel:'计划员', fieldGroup:'配件主数据', valueType:'STRING', enumValues:null, supportedOps:['EQ','NE','IN','NOT_IN'] },
  { fieldName:'purchaseType', fieldLabel:'采购类别', fieldGroup:'配件主数据', valueType:'ENUM', enumValues:null, supportedOps:['EQ','NE','IN','NOT_IN'] },
  { fieldName:'demand_week_avg_12w', fieldLabel:'近12周周均销量', fieldGroup:'指标-历史需求', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'demand_week_avg_8w', fieldLabel:'近8周周均销量', fieldGroup:'指标-历史需求', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'demand_week_std_8w', fieldLabel:'近8周需求标准差', fieldGroup:'指标-历史需求', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'demand_month_avg_3m', fieldLabel:'近3个月月均销量', fieldGroup:'指标-历史需求', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'demand_month_avg_3m_all', fieldLabel:'近3月全仓月均销量', fieldGroup:'指标-历史需求', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'demand_month_std_6m', fieldLabel:'近6个月需求标准差', fieldGroup:'指标-历史需求', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'demand_month_std_6m_all', fieldLabel:'近6月全仓需求标准差', fieldGroup:'指标-历史需求', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'demand_qty_3m', fieldLabel:'近3个月需求量', fieldGroup:'指标-历史需求', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'demand_qty_12m', fieldLabel:'近12个月需求量', fieldGroup:'指标-历史需求', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'demand_qty_12m_all', fieldLabel:'近12月全仓需求量', fieldGroup:'指标-历史需求', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'days_since_last_demand', fieldLabel:'无需求天数', fieldGroup:'指标-历史需求', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'sales_frequency_1y', fieldLabel:'近一年销售频次', fieldGroup:'指标-兜底频次', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'fallback_c_week_avg', fieldLabel:'兜底C类周均销量', fieldGroup:'指标-兜底频次', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'forecast_next_week_manual_qty', fieldLabel:'下周人工预测', fieldGroup:'指标-预测', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'forecast_next_month_manual_qty', fieldLabel:'下月仓库人工预测', fieldGroup:'指标-预测', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'forecast_next_month_manual_qty_all', fieldLabel:'下月全仓人工预测', fieldGroup:'指标-预测', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'on_hand_qty', fieldLabel:'账面库存', fieldGroup:'指标-库存供应', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'available_qty', fieldLabel:'可用库存', fieldGroup:'指标-库存供应', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'purchase_inbound_qty', fieldLabel:'采购在途数量', fieldGroup:'指标-库存供应', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'transfer_inbound_qty', fieldLabel:'调拨在途数量', fieldGroup:'指标-库存供应', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'backorder_qty', fieldLabel:'未交需求数量', fieldGroup:'指标-库存供应', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
];
const REGISTRY_ORDER = ['配件主数据','仓库主数据','指标-历史需求','指标-兜底频次','指标-预测','指标-库存供应'];
// 字段来源仅三类：配件主数据 / 仓库主数据 / 指标宽表。全局参数类字段（LT、目标满足率、风控系数、备货标识等）不纳入档位条件。
function fieldSourceLabel(k){
  if(k==='配件主数据'||k==='仓库主数据') return k;
  return '指标宽表·'+String(k).replace(/^指标-/,'');
}
function fieldSourceGroups(){
  const g={};
  FIELD_REGISTRY.forEach(f=>{ const k=f.fieldGroup||'其他'; (g[k]=g[k]||[]).push(f); });
  return REGISTRY_ORDER.filter(k=>g[k]).map(k=>({key:k,label:fieldSourceLabel(k),fields:g[k]}));
}

let _nid = 1000;
function nextId(){ return ++_nid; }

/* ============ 纯逻辑（可被 Node 测试 require，不依赖 Vue/DOM） ============ */

function fieldMeta(fn){ return FIELD_REGISTRY.find(f=>f.fieldName===fn); }
function fieldLabel(fn){ const f=fieldMeta(fn); return f?f.fieldLabel:fn; }
function fieldType(fn){ const f=fieldMeta(fn); return f?f.valueType:'STRING'; }
function enumOptions(fn){ const f=fieldMeta(fn); return (f&&f.enumValues)?f.enumValues.map(([v,l])=>({value:v,label:l})):[]; }
function opOptionsFor(c){ const f=fieldMeta(c.fieldName); const ops=f?f.supportedOps:ALL_OPS; return ops.map(o=>({value:o,label:OP[o]})); }
function condValueText(c){
  if(['IS_NULL','IS_NOT_NULL'].includes(c.operator)) return '';
  if(c.operator==='BETWEEN') return (c.value1||'')+' ~ '+(c.value2||'');
  const f=fieldMeta(c.fieldName);
  if(f && f.valueType==='ENUM' && f.enumValues){
    const labels=(c.value1||'').split(',').map(v=>{ const en=f.enumValues.find(e=>e[0]===v.trim()); return en?en[1]:v; });
    return labels.join(', ');
  }
  return c.value1==null?'':String(c.value1);
}
function mkCond(fieldName, operator, value1, value2){
  const f=fieldMeta(fieldName)||{};
  return { seqNo:1, fieldName, fieldLabel:f.fieldLabel||fieldName, operator, valueType:f.valueType||'STRING', value1:value1==null?'':String(value1), value2:value2==null?'':String(value2) };
}
function conds(list){ return list.map((c,i)=>{ const o=mkCond(c[0],c[1],c[2],c[3]); o.seqNo=i+1; return o; }); }

// C/D 示例组的价格区间档位：用普通条件（销售价字段 + > / ≤ / 为空）表达，非专门价格分档机制。
// 区间与 V 取自需求说明 13.6 权威价档表；每次调用返回独立副本，C/D 各自持有、互不影响。
function priceRangeTiers(prefix){
  const p=prefix||'G';
  return [
    { id:p+'_T1', seq:10, name:'销售价 空或≤0.01', matchMode:'OR',
      conditions:conds([['salesPrice','IS_NULL',''],['salesPrice','LE','0.01']]), fallbackValue:5, reason:'价格空或极低兜底', enabled:true },
    { id:p+'_T2', seq:20, name:'销售价 >0.01 且 ≤2', matchMode:'AND',
      conditions:conds([['salesPrice','GT','0.01'],['salesPrice','LE','2']]), fallbackValue:50, reason:'价格0.01~2兜底', enabled:true },
    { id:p+'_T3', seq:30, name:'销售价 >2 且 ≤20', matchMode:'AND',
      conditions:conds([['salesPrice','GT','2'],['salesPrice','LE','20']]), fallbackValue:10, reason:'价格2~20兜底', enabled:true },
    { id:p+'_T4', seq:40, name:'销售价 >20 且 ≤60', matchMode:'AND',
      conditions:conds([['salesPrice','GT','20'],['salesPrice','LE','60']]), fallbackValue:8, reason:'价格20~60兜底', enabled:true },
    { id:p+'_T5', seq:50, name:'销售价 >60 且 ≤200', matchMode:'AND',
      conditions:conds([['salesPrice','GT','60'],['salesPrice','LE','200']]), fallbackValue:6, reason:'价格60~200兜底', enabled:true },
    { id:p+'_T6', seq:60, name:'销售价 >200 且 ≤500', matchMode:'AND',
      conditions:conds([['salesPrice','GT','200'],['salesPrice','LE','500']]), fallbackValue:5, reason:'价格200~500兜底', enabled:true },
    { id:p+'_T7', seq:70, name:'销售价 >500 且 ≤2000', matchMode:'AND',
      conditions:conds([['salesPrice','GT','500'],['salesPrice','LE','2000']]), fallbackValue:4, reason:'价格500~2000兜底', enabled:true },
    { id:p+'_T8', seq:80, name:'销售价 >2000', matchMode:'AND',
      conditions:conds([['salesPrice','GT','2000']]), fallbackValue:3, reason:'价格>2000兜底', enabled:true },
  ];
}

// 示例数据（非系统预置生产规则）：首次打开展示 4 组，业务可自行增删改。
// 各组按 ABC 分类互斥；每组自带独立条件分档；C/D 组示例档位按销售价区间给出不同 V。
function exampleGroups(){
  return [
    { id:'G_S0', groupCode:'S0_CLASS_FALLBACK', groupName:'S0类兜底（示例）', priority:10, enabled:true,
      description:'示例：ABC=S0 且无法行驶=是，固定 V=1（安全件优先，排在最前）',
      scope:{ matchMode:'AND', conditions:conds([['abcClassification','EQ','S0'],['potentialUnitDown','EQ','true']]) },
      tiers:[
        { id:'S0_T1', seq:10, name:'S0安全件固定示例', matchMode:'AND', conditions:[], fallbackValue:1, reason:'S0类兜底-无法行驶', enabled:true },
      ]},
    { id:'G_SE', groupCode:'SE_CLASS_FALLBACK', groupName:'S/E类兜底（示例）', priority:20, enabled:true,
      description:'示例：ABC∈S1/S2/S3/E 且近一年销售频次≥1；频次≥3→V=3，1~2→V=2',
      scope:{ matchMode:'AND', conditions:conds([['abcClassification','IN','S1,S2,S3,E'],['sales_frequency_1y','GE','1']]) },
      tiers:[
        { id:'SE_T1', seq:10, name:'近一年销售频次 ≥3', matchMode:'AND', conditions:conds([['sales_frequency_1y','GE','3']]), fallbackValue:3, reason:'S/E类兜底-高频卖一补一', enabled:true },
        { id:'SE_T2', seq:20, name:'近一年销售频次 1~2', matchMode:'AND', conditions:conds([['sales_frequency_1y','BETWEEN','1','2']]), fallbackValue:2, reason:'S/E类兜底-低频卖一补一', enabled:true },
      ]},
    { id:'G_C', groupCode:'C_CLASS_FALLBACK', groupName:'C类兜底（示例）', priority:30, enabled:true,
      description:'示例：ABC=C 且近3个月月均销量<8；按销售价区间给出不同兜底 V（8 档），可按需修改',
      scope:{ matchMode:'AND', conditions:conds([['abcClassification','EQ','C'],['demand_month_avg_3m','LT','8']]) },
      tiers:priceRangeTiers('C') },
    { id:'G_D', groupCode:'D_CLASS_FALLBACK', groupName:'D类兜底（示例）', priority:40, enabled:true,
      description:'示例：ABC=D，无销量门槛；按销售价区间给出不同兜底 V（8 档），与 C 组各自独立',
      scope:{ matchMode:'AND', conditions:conds([['abcClassification','EQ','D']]) },
      tiers:priceRangeTiers('D') },
  ];
}
const seedGroups = exampleGroups; // 兼容既有调用方；语义为"示例数据"而非系统预置规则

function evalCond(c, mat){
  if(!c || !mat) return false;
  const actual = mat[c.fieldName];
  if(c.operator==='IS_NULL') return actual===null||actual===undefined||actual==='';
  if(c.operator==='IS_NOT_NULL') return !(actual===null||actual===undefined||actual==='');
  if(actual===null||actual===undefined) return false;
  if(fieldType(c.fieldName)==='NUMBER' || (c.valueType==='NUMBER')){
    const a=parseFloat(actual), b1=parseFloat(c.value1), b2=parseFloat(c.value2);
    if(isNaN(a)) return false;
    switch(c.operator){ case'EQ':return !isNaN(b1)&&a===b1; case'NE':return !isNaN(b1)&&a!==b1; case'GT':return !isNaN(b1)&&a>b1; case'GE':return !isNaN(b1)&&a>=b1; case'LT':return !isNaN(b1)&&a<b1; case'LE':return !isNaN(b1)&&a<=b1; case'BETWEEN':return !isNaN(b1)&&!isNaN(b2)&&a>=b1&&a<=b2; default:return false; }
  }
  const a=String(actual), v1=String(c.value1==null?'':c.value1);
  if(c.operator==='IN'){ return v1.split(',').map(s=>s.trim()).includes(a); }
  if(c.operator==='NOT_IN'){ return !v1.split(',').map(s=>s.trim()).includes(a); }
  switch(c.operator){ case'EQ':return a===v1; case'NE':return a!==v1; case'GT':return a>v1; case'GE':return a>=v1; case'LT':return a<v1; case'LE':return a<=v1; default:return false; }
}
function evalRule(tier, mat){
  const cs=tier.conditions||[];
  if(!cs.length) return true; // 适用范围已限定的组内，无条件分档视为该层默认命中
  const mode=(tier.matchMode||'AND').toUpperCase();
  return mode==='OR' ? cs.some(c=>evalCond(c,mat)) : cs.every(c=>evalCond(c,mat));
}
function evalScope(group, mat){
  const scope=group.scope||{};
  const cs=scope.conditions||[];
  if(!cs.length) return false; // 保护：无适用范围的组不允许参与匹配
  const mode=(scope.matchMode||'AND').toUpperCase();
  return mode==='OR' ? cs.some(c=>evalCond(c,mat)) : cs.every(c=>evalCond(c,mat));
}
// 只用该组自己的 tiers 匹配，不依赖任何外部表或特殊分档模式
function matchGroup(group, mat){
  if(!group || group.enabled===false) return null;
  if(!evalScope(group, mat)) return null;
  const tiers=(group.tiers||[]).filter(t=>t.enabled!==false).slice().sort((a,b)=>a.seq-b.seq);
  for(const t of tiers){ if(evalRule(t,mat)) return Object.assign({},t); }
  return null;
}
function matchAll(groups, mat){
  const gs=(groups||[]).slice().sort((a,b)=>a.priority-b.priority);
  for(const g of gs){ const hit=matchGroup(g,mat); if(hit) return {group:g, rule:hit}; }
  return null;
}
// 规则组编码由系统自动生成，无需人工填写；新建时为空会在保存前自动补号。
function nextGroupCode(){ return 'FG_'+String(nextId()); }
function validateGroup(g){
  const errs=[];
  if(!g.groupName||!g.groupName.trim()) errs.push('请填写规则组名称');
  if(!(g.scope&&g.scope.conditions&&g.scope.conditions.length)) errs.push('组级适用范围至少要有一条条件（防止跨类别误命中）');
  else if(!g.scope.conditions.some(c=>c.fieldName==='abcClassification')) errs.push('组级适用范围必须包含 ABC分类 条件（否则会跨类别抢占）');
  const seqs=(g.tiers||[]).filter(t=>t.enabled!==false).map(t=>t.seq);
  if(new Set(seqs).size!==seqs.length) errs.push('组内分档序号不能重复');
  (g.tiers||[]).forEach(t=>{ if(t.fallbackValue==null||t.fallbackValue<0) errs.push('分档「'+t.name+'」兜底值不能为负'); });
  return errs;
}
function validateTier(t){
  const errs=[];
  if(!t.name||!t.name.trim()) errs.push('请填写档位名称');
  if(t.fallbackValue==null||t.fallbackValue<0) errs.push('兜底值不能为负');
  return errs;
}

const api = { OP, FIELD_REGISTRY, REGISTRY_ORDER, OP_LABELS:OP, fieldSourceLabel, fieldSourceGroups,
  exampleGroups, seedGroups, priceRangeTiers, nextGroupCode, mkCond, conds, fieldMeta, fieldLabel, fieldType, enumOptions, opOptionsFor, condValueText,
  evalCond, evalRule, evalScope, matchGroup, matchAll, validateGroup, validateTier };
if(typeof module!=='undefined'&&module.exports) module.exports=api;
if(!root.Vue) return;
root.JlrFallbackRuleLogic = api;

/* ============ Vue 组件（配置页 UI） ============ */

const STORE_KEY='JLR_FALLBACK_RULE_COND_TIERS_V8';
function readStore(){ try{ const raw=root.localStorage&&root.localStorage.getItem(STORE_KEY); if(!raw)return null; const o=JSON.parse(raw); if(o&&Array.isArray(o.groups))return o.groups; }catch(e){} return null; }
function writeStore(groups){ try{ if(root.localStorage) root.localStorage.setItem(STORE_KEY, JSON.stringify({groups})); }catch(e){} }

root.JlrFallbackRule = {
  setup(){
    const stored=readStore();
    const groups = ref(stored?stored:seedGroups());
    const selectedGroupId = ref(groups.value[0]?groups.value[0].id:null);

    const groupModalOpen = ref(false);
    // 规则组编码不在表单中：新建由系统自动生成，编辑时沿用原编码。
    const groupForm = reactive({ id:null, groupName:'', priority:99, enabled:true, description:'', scope:{matchMode:'AND',conditions:[]} });
    const tierState = ref(null);          // 组内分档编辑（弹窗）

    const groupsSorted = computed(()=>[...groups.value].sort((a,b)=>a.priority-b.priority));
    const activeGroup = computed(()=>groups.value.find(g=>g.id===selectedGroupId.value)||null);
    const activeTiers = computed(()=>activeGroup.value?[...(activeGroup.value.tiers||[])].filter(t=>t.enabled!==false).sort((a,b)=>a.seq-b.seq):[]);
    // 分档编辑器以弹窗呈现：tierState 有值即打开，关闭即清空
    const tierModalOpen = computed({ get(){ return !!tierState.value; }, set(v){ if(!v) tierState.value=null; } });

    function persist(){ writeStore(groups.value); }
    function notify(msg,type){ if(root.antd&&root.antd.message) root.antd.message[type||'success'](msg); }
    function selectGroup(id){ selectedGroupId.value=id; tierState.value=null; }

    function normForEdit(e){ if(e.scope) normCondArrForEdit(e.scope.conditions); if(e.conditions) normCondArrForEdit(e.conditions); }
    function normForSave(e){ if(e.scope) normCondArrForSave(e.scope.conditions); if(e.conditions) normCondArrForSave(e.conditions); }
    function normCondArrForEdit(cs){ (cs||[]).forEach(c=>{ if(c.valueType==='ENUM' && typeof c.value1==='string'){ c.value1 = c.value1? c.value1.split(',').map(s=>s.trim()).filter(Boolean) : []; } }); }
    function normCondArrForSave(cs){ (cs||[]).forEach(c=>{ if(c.valueType==='ENUM' && Array.isArray(c.value1)){ c.value1 = c.value1.join(','); } }); }

    function addCondToList(list){ list.push(mkCond(FIELD_REGISTRY[0].fieldName, FIELD_REGISTRY[0].supportedOps[0], '', '')); }
    function onCondFieldChange(c){ const f=fieldMeta(c.fieldName); if(f){ c.fieldLabel=f.fieldLabel; c.valueType=f.valueType; c.operator=f.supportedOps[0]; c.value1=''; c.value2=''; } }

    /* ---- 规则组 ---- */
    function openGroupModal(g){
      if(g){ Object.assign(groupForm,{id:g.id,groupCode:g.groupCode,groupName:g.groupName,priority:g.priority,enabled:g.enabled,description:g.description,scope:JSON.parse(JSON.stringify(g.scope||{matchMode:'AND',conditions:[]}))}); normForEdit(groupForm); }
      else { Object.assign(groupForm,{id:null,groupName:'',priority:(groups.value.reduce((m,x)=>Math.max(m,x.priority),0)||0)+10,enabled:true,description:'',scope:{matchMode:'AND',conditions:[mkCond('abcClassification','EQ','C','')]}}); delete groupForm.groupCode; }
      groupModalOpen.value=true;
    }
    function saveGroup(){
      normForSave(groupForm);
      const existing=groupForm.id?groups.value.find(x=>x.id===groupForm.id):null;
      const tiers=existing?JSON.parse(JSON.stringify(existing.tiers||[])):[];
      const g={ id:existing?existing.id:('G_'+nextId()), groupCode:existing?existing.groupCode:nextGroupCode(), groupName:groupForm.groupName.trim(),
        priority:Number(groupForm.priority)||99, enabled:groupForm.enabled, description:groupForm.description||'',
        tiers, scope:JSON.parse(JSON.stringify(groupForm.scope)) };
      const errs=validateGroup(g);
      if(errs.length){ notify(errs.join('；'),'error'); return; }
      const idx=groups.value.findIndex(x=>x.id===g.id);
      if(idx>=0) groups.value[idx]=g; else groups.value.push(g);
      groups.value.sort((a,b)=>a.priority-b.priority); selectedGroupId.value=g.id; groupModalOpen.value=false; persist(); notify('已保存规则组');
    }
    function deleteGroup(){ const id=selectedGroupId.value; groups.value=groups.value.filter(g=>g.id!==id); selectedGroupId.value=groups.value[0]?groups.value[0].id:null; tierState.value=null; persist(); notify('已删除规则组'); }
    function duplicateGroup(g){ if(!g)return; const copy=JSON.parse(JSON.stringify(g)); const tag=nextId(); copy.id='G_'+tag; copy.groupCode=nextGroupCode(); copy.groupName=g.groupName+'（副本）'; copy.priority=groups.value.reduce((m,x)=>Math.max(m,x.priority),0)+10; copy.tiers=(copy.tiers||[]).map(t=>({...t,id:'T_'+tag+'_'+t.id})); groups.value.push(copy); groups.value.sort((a,b)=>a.priority-b.priority); selectedGroupId.value=copy.id; persist(); notify('已复制规则组（含独立分档副本）'); }

    /* ---- 组内分档 ---- */
    function openTierEditor(tier){
      const g=activeGroup.value; if(!g)return;
      if(tier){ const e=JSON.parse(JSON.stringify(tier)); normForEdit(e); tierState.value=e; }
      else {
        const maxS=(g.tiers||[]).reduce((m,t)=>Math.max(m,t.seq),0);
        tierState.value={ id:'T_'+nextId(), seq:maxS+10, name:'新档位', matchMode:'AND',
          conditions:[], fallbackValue:5, reason:'', enabled:true };
      }
    }
    function saveTier(){
      const e=tierState.value,g=activeGroup.value; if(!e||!g)return;
      normForSave(e);
      const errs=validateTier(e);
      if(errs.length){ notify(errs.join('；'),'error'); return; }
      e.conditions.forEach((c,i)=>c.seqNo=i+1);
      const others=(g.tiers||[]).filter(t=>t.id!==e.id);
      if(others.some(t=>t.seq===e.seq)){ notify('档位序号不能重复','error'); return; }
      const idx=g.tiers.findIndex(t=>t.id===e.id);
      if(idx>=0) g.tiers[idx]=e; else g.tiers.push(e);
      g.tiers.sort((a,b)=>a.seq-b.seq); tierState.value=null; persist(); notify('已保存本组分档');
    }
    function deleteTier(id){ const g=activeGroup.value; g.tiers=(g.tiers||[]).filter(t=>t.id!==id); persist(); notify('已删除档位'); }
    function duplicateTier(t){ const g=activeGroup.value; if(!g||!t)return; const copy=JSON.parse(JSON.stringify(t)); copy.id='T_'+nextId(); copy.seq=g.tiers.reduce((m,x)=>Math.max(m,x.seq),0)+10; copy.name=(t.name||'')+'（副本）'; g.tiers.push(copy); g.tiers.sort((a,b)=>a.seq-b.seq); persist(); notify('已复制档位'); }
    function moveTier(id, dir){
      const g=activeGroup.value; if(!g)return;
      const list=[...(g.tiers||[])].sort((a,b)=>a.seq-b.seq);
      const i=list.findIndex(t=>t.id===id); const j=i+dir;
      if(i<0||j<0||j>=list.length)return;
      const tmp=list[i].seq; list[i].seq=list[j].seq; list[j].seq=tmp;
      g.tiers=list; persist();
    }

    const fieldSelectOptions=fieldSourceGroups().map(k=>({label:k.label+'（'+k.fields.length+'）',options:k.fields.map(f=>({value:f.fieldName,label:f.fieldLabel}))}));

    return {
      OP, groups, groupsSorted, selectedGroupId, activeGroup, activeTiers,
      selectGroup, persist,
      groupModalOpen, groupForm, openGroupModal, saveGroup, deleteGroup, duplicateGroup,
      tierState, tierModalOpen, openTierEditor, saveTier, deleteTier, duplicateTier, moveTier,
      addCondToList, onCondFieldChange, normForEdit, normForSave,
      fieldMeta, fieldLabel, fieldType, enumOptions, opOptionsFor, condValueText, fieldSelectOptions,
    };
  },
  template:`
  <section class="strategy-page fallback-page">
    <div class="strategy-heading"><div><h2>兜底规则</h2>
      <div class="strategy-sub">分层配置：规则组（组级适用范围，AND）→ 组内条件分档（配件主数据/指标宽表字段 AND/OR）→ 首个命中生效；命中后仅当 S1&lt;V 才实际应用兜底。</div></div>
      <a-tag color="blue">当前 4 组为示例数据</a-tag>
    </div>
    <a-alert type="info" show-icon style="margin-bottom:14px" message="系统不预置生产规则：首次进入展示的 4 组仅为示例数据，可自行增删改。每个规则组各自维护一套独立分档：第一层限定配件适用范围（如 ABC 分类、仓库编码、销量门槛，全部满足才进入该组）；第二层在该组内按序号分档取兜底值 V。档位条件字段仅取自配件主数据与指标宽表，组间互不影响；无销售价分档逻辑。" />

    <div class="fallback-layout">
      <div class="card fallback-side">
        <div class="fallback-side-hd"><span class="fallback-side-title">规则组</span>
          <div style="display:flex;gap:6px"><a-button size="small" @click="openGroupModal(null)">+ 规则组</a-button></div>
        </div>
        <div class="fallback-group-list">
          <div v-for="g in groupsSorted" :key="g.id" class="fallback-group-item" :class="{active:g.id===selectedGroupId}" @click="selectGroup(g.id)">
            <div class="fgi-top"><span class="fgi-name">{{ g.groupName }}</span><a-tag :color="g.enabled?'green':'default'" style="margin:0">{{ g.enabled?'启用':'停用' }}</a-tag></div>
            <div class="fgi-meta"><span class="fgi-prio">优先级 {{ g.priority }}</span><span>条件分档 {{ (g.tiers||[]).length }} 条</span></div>
          </div>
          <a-empty v-if="!groups.length" description="暂无规则组" />
        </div>
      </div>

      <div class="card fallback-main">
        <template v-if="activeGroup">
          <div class="strategy-toolbar">
            <span style="font-size:15px;font-weight:600;color:#223047">{{ activeGroup.groupName }}</span>
            <a-tag color="purple">优先级 {{ activeGroup.priority }}</a-tag>
            <a-tag :color="activeGroup.enabled?'green':'default'">{{ activeGroup.enabled?'启用':'停用' }}</a-tag>
            <div style="margin-left:auto;display:flex;gap:10px">
              <a-button size="small" @click="openGroupModal(activeGroup)">编辑组与适用范围</a-button>
              <a-button size="small" @click="duplicateGroup(activeGroup)">复制组</a-button>
              <a-popconfirm title="确认删除该规则组及其分档？" @confirm="deleteGroup"><a-button size="small" danger>删除组</a-button></a-popconfirm>
            </div>
          </div>
          <div class="strategy-sub" style="margin:2px 0 12px">{{ activeGroup.description }}</div>

          <div class="bt-sec-t">第一层 · 适用范围（组级前置条件，{{ (activeGroup.scope.conditions||[]).length }} 条，全部满足才进入本组）</div>
          <div class="fallback-cond-box" style="margin-bottom:16px">
            <div v-for="(c,i) in activeGroup.scope.conditions" :key="i" class="fallback-cond-box" style="margin-bottom:6px;border:none;padding:0">
              <span class="fb-seq" style="margin-right:8px">{{ i+1 }}</span>
              <span class="fb-chip">{{ c.fieldLabel }}</span><span class="fb-chip fb-op">{{ OP[c.operator] }}</span><span class="fb-chip">{{ condValueText(c) }}</span>
            </div>
            <div class="strategy-sub">在「编辑组与适用范围」中修改；建议至少保留一条 ABC 分类条件以保证各组互斥。</div>
          </div>

          <div class="bt-sec-t">第二层 · 本组分档（{{ activeTiers.length }} 条，自定义条件，按序号首个命中生效）</div>
          <div class="strategy-toolbar" style="margin:2px 0 10px"><span class="strategy-sub">按序号升序匹配，首个命中生效；本组分档独立维护，条件字段仅限配件主数据/指标宽表</span><div style="margin-left:auto"><a-button size="small" type="primary" @click="openTierEditor(null)">+ 新增档位</a-button></div></div>
          <div v-if="!activeTiers.length" class="fallback-empty"><a-empty description="本组暂无分档，点击右上角新增"/></div>
          <div v-else class="fb-rule-list">
            <div v-for="t in activeTiers" :key="t.id" class="fb-rule-card" :class="{disabled:t.enabled===false}">
              <div class="fbrc-hd"><span class="fb-prio">{{ t.seq }}</span><span class="fbrc-name">{{ t.name }}</span>
                <a-tag v-if="t.enabled!==false" color="green">启用</a-tag><a-tag v-else color="default">停用</a-tag></div>
              <div class="fbrc-body"><template v-if="!(t.conditions||[]).length"><span class="fbrc-none">无条件（本组默认命中）</span></template><template v-else><template v-for="(c,i) in t.conditions" :key="i"><span v-if="i>0" class="fb-link">{{ t.matchMode }}</span><span class="fb-chip">{{ c.fieldLabel }}</span><span class="fb-chip fb-op">{{ OP[c.operator] }}</span><span class="fb-chip">{{ condValueText(c) }}</span></template></template></div>
              <div class="fbrc-ft">兜底值 <b>{{ t.fallbackValue }}</b>
                <span style="float:right"><a @click.stop="moveTier(t.id,-1)" style="margin-right:8px">上移</a><a @click.stop="moveTier(t.id,1)" style="margin-right:8px">下移</a><a @click.stop="duplicateTier(t)" style="margin-right:8px">复制</a><a @click.stop="openTierEditor(t)" style="margin-right:8px">编辑</a><a @click.stop="deleteTier(t.id)" style="color:#ff4d4f">删除</a></span></div>
            </div>
          </div>
        </template>
        <div v-else class="fallback-empty"><a-empty description="请选择一个规则组"/></div>
      </div>
    </div>

    <div class="strategy-footnote">匹配顺序：规则组优先级升序 → 组级适用范围（全部条件满足）→ 本组分档序号升序 → 首个命中生效；命中后仅当风控后目标 S1&lt;V 才应用兜底，写回兜底值与原因。各组独立配置，互不影响。</div>

    <!-- 规则组 + 适用范围 -->
    <a-modal v-model:open="groupModalOpen" :title="groupForm.id?'编辑规则组与适用范围':'新增规则组'" :width="720" :footer="null" :mask-closable="false">
      <div class="strategy-grid">
        <label><span><span class="jlrs-req">*</span>规则组名称</span><a-input v-model:value="groupForm.groupName" placeholder="如 C类兜底"/></label>
        <label><span><span class="jlrs-req">*</span>执行优先级</span><a-input-number v-model:value="groupForm.priority" :min="1" style="width:100%"/></label>
        <label><span>状态</span><a-select v-model:value="groupForm.enabled" :options="[{value:true,label:'启用'},{value:false,label:'停用'}]"/></label>
        <label style="grid-column:1 / -1"><span>描述</span><a-input v-model:value="groupForm.description" placeholder="如 ABC=C 且近3个月月均销量<8"/></label>
      </div>
      <div class="bt-sec-t" style="margin-top:16px">第一层 · 适用范围（组级前置条件，全部满足才进入本组）</div>
      <div class="fallback-cond-box">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><span style="font-size:13px;color:#45536a">条件逻辑：AND（全部满足）</span><a-button type="primary" size="small" @click="addCondToList(groupForm.scope.conditions)">+ 添加条件</a-button></div>
        <div v-for="(c,idx) in groupForm.scope.conditions" :key="idx" class="fallback-cond-row">
          <span class="fb-seq">{{ idx+1 }}</span>
          <a-select v-model:value="c.fieldName" style="width:200px" @change="onCondFieldChange(c)" :options="fieldSelectOptions"/>
          <a-select v-model:value="c.operator" style="width:110px" :options="opOptionsFor(c)"/>
          <template v-if="!['IS_NULL','IS_NOT_NULL'].includes(c.operator)">
            <template v-if="c.operator==='BETWEEN'"><a-input v-model:value="c.value1" placeholder="下限" style="width:100px"/><span style="color:#8c8c8c">~</span><a-input v-model:value="c.value2" placeholder="上限" style="width:100px"/></template>
            <a-select v-else-if="fieldType(c.fieldName)==='ENUM'" v-model:value="c.value1" mode="multiple" allow-clear style="min-width:160px" :options="enumOptions(c.fieldName)"/>
            <a-input v-else v-model:value="c.value1" placeholder="值" :type="fieldType(c.fieldName)==='NUMBER'?'number':'text'" style="width:130px"/>
          </template>
          <a style="margin-left:8px;color:#ff4d4f" @click="groupForm.scope.conditions.splice(idx,1)">删除</a>
        </div>
      </div>
      <div class="strategy-modal-footer"><a-button @click="groupModalOpen=false">取消</a-button><a-button type="primary" @click="saveGroup">保存</a-button></div>
    </a-modal>

    <!-- 组内分档编辑（弹窗） -->
    <a-modal v-model:open="tierModalOpen" :title="tierState&&tierState.id?'编辑本组分档':'新增本组分档'" :width="760" :mask-closable="false" @cancel="tierState=null">
      <template v-if="tierState">
        <div class="strategy-grid">
          <label><span><span class="jlrs-req">*</span>档位名称</span><a-input v-model:value="tierState.name" placeholder="如 销售价>2 且 ≤20"/></label>
          <label><span><span class="jlrs-req">*</span>序号</span><a-input-number v-model:value="tierState.seq" :min="1" style="width:100%"/></label>
          <label><span><span class="jlrs-req">*</span>兜底值 V(件)</span><a-input-number v-model:value="tierState.fallbackValue" :min="0" :precision="0" style="width:100%"/></label>
          <label><span>状态</span><a-select v-model:value="tierState.enabled" :options="[{value:true,label:'启用'},{value:false,label:'停用'}]"/></label>
        </div>
        <div style="margin:14px 0 8px;display:flex;align-items:center;gap:12px">
          <span style="font-size:13px;color:#45536a">条件逻辑：</span>
          <a-radio-group v-model:value="tierState.matchMode" button-style="solid"><a-radio-button value="AND">AND（全部满足）</a-radio-button><a-radio-button value="OR">OR（任一满足）</a-radio-button></a-radio-group>
          <span class="strategy-sub">无销售价分档逻辑；如需按其他字段分档，直接添加条件即可</span>
        </div>
        <div class="fallback-cond-box">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><span style="font-size:13px;font-weight:600;color:#1f1f1f">档位条件</span><a-button type="primary" size="small" @click="addCondToList(tierState.conditions)">+ 添加条件</a-button></div>
          <div class="strategy-sub" v-if="!tierState.conditions.length">无条件：在适用范围已限定的本组内，该分档默认命中（适合固定 V 值场景）。</div>
          <div v-for="(c,idx) in tierState.conditions" :key="idx" class="fallback-cond-row">
            <span class="fb-seq">{{ idx+1 }}</span>
            <a-select v-model:value="c.fieldName" style="width:200px" @change="onCondFieldChange(c)" :options="fieldSelectOptions"/>
            <a-select v-model:value="c.operator" style="width:110px" :options="opOptionsFor(c)"/>
            <template v-if="!['IS_NULL','IS_NOT_NULL'].includes(c.operator)">
              <template v-if="c.operator==='BETWEEN'"><a-input v-model:value="c.value1" placeholder="下限" style="width:100px"/><span style="color:#8c8c8c">~</span><a-input v-model:value="c.value2" placeholder="上限" style="width:100px"/></template>
              <a-select v-else-if="fieldType(c.fieldName)==='ENUM'" v-model:value="c.value1" mode="multiple" allow-clear style="min-width:160px" :options="enumOptions(c.fieldName)"/>
              <a-input v-else v-model:value="c.value1" placeholder="值" :type="fieldType(c.fieldName)==='NUMBER'?'number':'text'" style="width:130px"/>
            </template>
            <a style="margin-left:8px;color:#ff4d4f" @click="tierState.conditions.splice(idx,1)">删除</a>
          </div>
        </div>
        <div class="strategy-grid" style="margin-top:14px"><label style="grid-column:1 / -1"><span>兜底原因（命中后写入结果表）</span><a-input v-model:value="tierState.reason" placeholder="如 价格2~20兜底"/></label></div>
      </template>
      <div class="strategy-modal-footer"><a-button @click="tierState=null">取消</a-button><a-button type="primary" @click="saveTier">保存档位</a-button></div>
    </a-modal>

  </section>`
};
})(typeof window!=='undefined'?window:{});
