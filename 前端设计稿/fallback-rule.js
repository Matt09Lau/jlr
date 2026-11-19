/* 兜底规则配置页：与「库存策略参数」同风格，数据仅保存在当前浏览器，不连接原系统。
 * 字段来源：配件主数据 + 指标宽表（dws_part_wh_metric_snapshot / dws_part_metric_snapshot）
 * 匹配逻辑与后端 FallbackRuleMatcher 保持一致：按规则组优先级 → 组内分档优先级，首个命中生效。
 */
(function(root){
'use strict';
const { ref, reactive, computed } = Vue;

const OP = { EQ:'=', NE:'≠', GT:'>', GE:'≥', LT:'<', LE:'≤', BETWEEN:'区间', IN:'属于', NOT_IN:'不属于', IS_NULL:'为空', IS_NOT_NULL:'不为空' };
const ALL_OPS = ['EQ','NE','GT','GE','LT','LE','BETWEEN','IN','NOT_IN','IS_NULL','IS_NOT_NULL'];

// 字段注册表：配件主数据 + 指标宽表
const FIELD_REGISTRY = [
  // 配件主数据
  { fieldName:'abcClassification', fieldLabel:'ABC分类', fieldGroup:'配件主数据', valueType:'ENUM', enumValues:[['S0','S0'],['S1','S1'],['S2','S2'],['S3','S3'],['A','A'],['B','B'],['C','C'],['D','D'],['E','E']], supportedOps:['EQ','NE','IN','NOT_IN'] },
  { fieldName:'xyzClassification', fieldLabel:'XYZ分类', fieldGroup:'配件主数据', valueType:'ENUM', enumValues:[['X','X'],['Y','Y'],['Z','Z']], supportedOps:['EQ','NE','IN','NOT_IN'] },
  { fieldName:'volumeClassification', fieldLabel:'体积分类', fieldGroup:'配件主数据', valueType:'ENUM', enumValues:[['S','小'],['M','中'],['L','大']], supportedOps:['EQ','NE','IN','NOT_IN'] },
  { fieldName:'moneyClassification', fieldLabel:'金额分类', fieldGroup:'配件主数据', valueType:'ENUM', enumValues:[['H','高'],['M','中'],['L','低']], supportedOps:['EQ','NE','IN','NOT_IN'] },
  { fieldName:'salesPrice', fieldLabel:'销售价', fieldGroup:'配件主数据', valueType:'NUMBER', enumValues:null, supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
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
  // 指标宽表：历史需求
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
  // 指标宽表：兜底频次
  { fieldName:'positive_order_line_cnt_12m', fieldLabel:'近12个月正销量订单行数', fieldGroup:'指标-兜底频次', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'positive_order_line_cnt_12m_all', fieldLabel:'近12月全局正订单行数', fieldGroup:'指标-兜底频次', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'fallback_c_week_avg', fieldLabel:'兜底C类周均销量', fieldGroup:'指标-兜底频次', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  // 指标宽表：预测
  { fieldName:'forecast_next_week_manual_qty', fieldLabel:'下周人工预测', fieldGroup:'指标-预测', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'forecast_next_month_manual_qty', fieldLabel:'下月仓库人工预测', fieldGroup:'指标-预测', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'forecast_next_month_manual_qty_all', fieldLabel:'下月全仓人工预测', fieldGroup:'指标-预测', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  // 指标宽表：配置匹配
  { fieldName:'target_fill_rate_pct', fieldLabel:'目标满足率(%)', fieldGroup:'指标-配置匹配', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'service_factor_z', fieldLabel:'服务水平Z值', fieldGroup:'指标-配置匹配', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'extra_stock_days', fieldLabel:'有效增储天数', fieldGroup:'指标-配置匹配', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'purchase_lt_effective_days', fieldLabel:'有效采购LT(天)', fieldGroup:'指标-配置匹配', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'planning_cycle_days', fieldLabel:'有效计划周期(天)', fieldGroup:'指标-配置匹配', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'risk_low_factor', fieldLabel:'最低风控线系数', fieldGroup:'指标-配置匹配', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'risk_high_factor', fieldLabel:'最高风控线系数', fieldGroup:'指标-配置匹配', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'interwarehouse_lt_days', fieldLabel:'有效库间LT(天)', fieldGroup:'指标-配置匹配', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'stock_allowed_flag', fieldLabel:'是否允许备货', fieldGroup:'指标-配置匹配', valueType:'BOOLEAN', enumValues:[['true','是'],['false','否']], supportedOps:['EQ','NE'] },
  // 指标宽表：库存与供应
  { fieldName:'on_hand_qty', fieldLabel:'账面库存', fieldGroup:'指标-库存供应', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'available_qty', fieldLabel:'可用库存', fieldGroup:'指标-库存供应', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'purchase_inbound_qty', fieldLabel:'采购在途数量', fieldGroup:'指标-库存供应', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'transfer_inbound_qty', fieldLabel:'调拨在途数量', fieldGroup:'指标-库存供应', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
  { fieldName:'backorder_qty', fieldLabel:'未交需求数量', fieldGroup:'指标-库存供应', valueType:'NUMBER', supportedOps:['EQ','NE','GT','GE','LT','LE','BETWEEN'] },
];
const REGISTRY_ORDER = ['配件主数据','指标-历史需求','指标-兜底频次','指标-预测','指标-配置匹配','指标-库存供应'];

// 初始化示例：与后端 SQL 初始化一致
function seedGroups(){
  const cTiers = [
    ['C_PRICE_1','销售价 空或≤0.01',5,'OR',[['salesPrice','LE','0.01'],['salesPrice','IS_NULL','']]],
    ['C_PRICE_2','销售价 >0.01 且 ≤2',50,'AND',[['salesPrice','GT','0.01'],['salesPrice','LE','2']]],
    ['C_PRICE_3','销售价 >2 且 ≤20',10,'AND',[['salesPrice','GT','2'],['salesPrice','LE','20']]],
    ['C_PRICE_4','销售价 >20 且 ≤60',8,'AND',[['salesPrice','GT','20'],['salesPrice','LE','60']]],
    ['C_PRICE_5','销售价 >60 且 ≤200',6,'AND',[['salesPrice','GT','60'],['salesPrice','LE','200']]],
    ['C_PRICE_6','销售价 >200 且 ≤500',5,'AND',[['salesPrice','GT','200'],['salesPrice','LE','500']]],
    ['C_PRICE_7','销售价 >500 且 ≤2000',4,'AND',[['salesPrice','GT','500'],['salesPrice','LE','2000']]],
    ['C_PRICE_8','销售价 >2000',3,'AND',[['salesPrice','GT','2000']]],
  ];
  const make = (code,name,prio,val,mode,conds,reason)=>({
    id:0, ruleCode:code, ruleName:name, priority:prio, fallbackValue:val, matchMode:mode, enabled:true, reason,
    conditions: conds.map(([fn,op,v,v2],i)=>{ const f=FIELD_REGISTRY.find(x=>x.fieldName===fn)||{}; return { seqNo:i+1, fieldName:fn, fieldLabel:f.fieldLabel||fn, operator:op, valueType:f.valueType||'STRING', value1:v, value2:v2||'' }; })
  });
  // C/D 类：组级前置条件「兜底C类周均销量 < 8」固定 AND 到每个价格档位；
  // 档位内部若为 OR（如「销售价 空或≤0.01」），拆成多条规则以避免与前置条件混在同一 matchMode 下
  function buildTiers(tiers, reasonPrefix, weekField){
    const out=[];
    tiers.forEach((t,i)=>{
      const [code,name,val,mode,conds]=t; const prio=i+1;
      if(mode==='OR'){
        conds.forEach((pc,j)=>{ out.push(make(code+'_'+j, name, prio, val, 'AND', [[weekField,'LT','8'], pc], reasonPrefix+'-'+name)); });
      } else {
        out.push(make(code, name, prio, val, 'AND', [[weekField,'LT','8'], ...conds], reasonPrefix+'-'+name));
      }
    });
    return out;
  }
  const cRules = buildTiers(cTiers, 'C类兜底', 'fallback_c_week_avg');
  const dRules = buildTiers(cTiers.slice(0,4), 'D类兜底', 'fallback_c_week_avg').map(r=>({...r, ruleCode:r.ruleCode.replace('C_','D_')}));
  return [
    { id:1, groupCode:'C_CLASS_FALLBACK', groupName:'C类兜底', priority:1, enabled:true, description:'ABC分类=C类 且 兜底C类周均销量<8，按销售价分档', rules:cRules },
    { id:2, groupCode:'D_CLASS_FALLBACK', groupName:'D类兜底', priority:2, enabled:true, description:'ABC分类=D类 且 兜底C类周均销量<8，按销售价分档（同C类）', rules:dRules },
    { id:3, groupCode:'SE_CLASS_FALLBACK', groupName:'S/E类兜底', priority:3, enabled:true, description:'S1/S2/S3/E类配件，按近一年频次（近12月全局正订单行数）兜底', rules:[
      make('SE_FREQ_HIGH','近一年频次 ≥3',1,3,'AND',[['abcClassification','IN','S1,S2,S3,E'],['positive_order_line_cnt_12m_all','GE','3']],'S/E类兜底-高频'),
      make('SE_FREQ_LOW','近一年频次 1~2',2,2,'AND',[['abcClassification','IN','S1,S2,S3,E'],['positive_order_line_cnt_12m_all','BETWEEN','1','2']],'S/E类兜底-低频'),
    ]},
    { id:4, groupCode:'S0_CLASS_FALLBACK', groupName:'S0类兜底', priority:4, enabled:true, description:'S0类且无法行驶，兜底值固定为1', rules:[
      make('S0_FIXED','S0且无法行驶',1,1,'AND',[['abcClassification','EQ','S0'],['potentialUnitDown','EQ','true']],'S0类兜底-无法行驶'),
    ]},
  ];
}

let _nid = 1000;
function nextId(){ return ++_nid; }

const ruleColumns = [
  { title:'优先级', dataIndex:'priority', key:'priority', width:90 },
  { title:'分档名称', dataIndex:'ruleName', key:'ruleName', width:180 },
  { title:'条件预览', key:'conditions' },
  { title:'条件逻辑', dataIndex:'matchMode', key:'matchMode', width:110 },
  { title:'兜底值', dataIndex:'fallbackValue', key:'fallbackValue', width:90 },
  { title:'状态', dataIndex:'enabled', key:'enabled', width:90 },
  { title:'操作', key:'action', width:140, fixed:'right' },
];
const regCols = [
  { title:'字段名', dataIndex:'fieldName', key:'fieldName', width:260 },
  { title:'中文名', dataIndex:'fieldLabel', key:'fieldLabel', width:180 },
  { title:'类型', dataIndex:'valueType', key:'valueType', width:100 },
  { title:'支持的操作符', key:'supportedOps' },
];

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
function fieldSelectOptions(){
  const g={}; FIELD_REGISTRY.forEach(f=>{ const k=f.fieldGroup||'其他'; (g[k]=g[k]||[]).push(f); });
  return REGISTRY_ORDER.filter(k=>g[k]).map(k=>({ label:k+'（'+g[k].length+'）', options:g[k].map(f=>({value:f.fieldName,label:f.fieldLabel})) }));
}
function registryGroups(){
  const g={}; FIELD_REGISTRY.forEach(f=>{ const k=f.fieldGroup||'其他'; (g[k]=g[k]||[]).push(f); });
  return REGISTRY_ORDER.filter(k=>g[k]).map(k=>({ name:k, fields:g[k] }));
}

// 匹配引擎（与后端 FallbackRuleMatcher 一致）
function evalCond(c, mat){
  let actual = mat[c.fieldName];
  if(c.operator==='IS_NULL') return actual===null||actual===undefined||actual==='';
  if(c.operator==='IS_NOT_NULL') return !(actual===null||actual===undefined||actual==='');
  if(actual===null||actual===undefined) return false;
  if(c.valueType==='NUMBER'){
    const a=parseFloat(actual), b1=parseFloat(c.value1), b2=parseFloat(c.value2);
    if(isNaN(a)) return false;
    switch(c.operator){ case'EQ':return !isNaN(b1)&&a===b1; case'NE':return !isNaN(b1)&&a!==b1; case'GT':return !isNaN(b1)&&a>b1; case'GE':return !isNaN(b1)&&a>=b1; case'LT':return !isNaN(b1)&&a<b1; case'LE':return !isNaN(b1)&&a<=b1; case'BETWEEN':return !isNaN(b1)&&!isNaN(b2)&&a>=b1&&a<=b2; default:return false; }
  }
  const a=String(actual), v1=String(c.value1==null?'':c.value1);
  if(c.operator==='IN'){ return v1.split(',').map(s=>s.trim()).includes(a); }
  if(c.operator==='NOT_IN'){ return !v1.split(',').map(s=>s.trim()).includes(a); }
  switch(c.operator){ case'EQ':return a===v1; case'NE':return a!==v1; case'GT':return a>v1; case'GE':return a>=v1; case'LT':return a<v1; case'LE':return a<=v1; default:return false; }
}
function evalRule(rule, mat){
  const cs=rule.conditions||[]; if(!cs.length) return false;
  const mode=(rule.matchMode||'AND').toUpperCase();
  return mode==='OR' ? cs.some(c=>evalCond(c,mat)) : cs.every(c=>evalCond(c,mat));
}
function matchGroup(group, mat){
  const rules=[...(group.rules||[])].sort((a,b)=>a.priority-b.priority);
  for(const r of rules){ if(!r.enabled) continue; if(evalRule(r,mat)) return r; }
  return null;
}

root.JlrFallbackRule = {
  setup(){
    const groups = ref(seedGroups());
    groups.value.forEach(g=>g.rules.forEach(r=>{ r.id=nextId(); r.conditions.forEach(c=>{ /* id assigned on edit */ }); }));
    const selectedGroupId = ref(groups.value[0]?groups.value[0].id:null);
    const editState = ref(null);
    const groupModalOpen = ref(false);
    const groupForm = reactive({ id:null, groupCode:'', groupName:'', priority:99, enabled:true, description:'' });
    const registryOpen = ref(false);
    const testValues = reactive({});
    const testResult = ref(null);

    const groupsSorted = computed(()=>[...groups.value].sort((a,b)=>a.priority-b.priority));
    const activeGroup = computed(()=>groups.value.find(g=>g.id===selectedGroupId.value)||null);
    const testFields = computed(()=>{
      const set=new Set();
      (activeGroup.value?.rules||[]).forEach(r=>(r.conditions||[]).forEach(c=>set.add(c.fieldName)));
      return [...set];
    });
    // 切换组时重置测试输入默认值
    const defaults = { abcClassification:'C', salesPrice:'300', fallback_c_week_avg:'5', potentialUnitDown:'false' };

    function selectGroup(id){ selectedGroupId.value=id; editState.value=null; testResult.value=null;
      for(const k in testValues) delete testValues[k];
      testFields.value.forEach(fn=>{ if(defaults[fn]!=null) testValues[fn]=defaults[fn]; });
    }

    // ENUM 多选值在存储时为逗号字符串，编辑器内为数组，打开/保存时互转
    function normForEdit(e){ (e.conditions||[]).forEach(c=>{ if(c.valueType==='ENUM' && typeof c.value1==='string'){ c.value1 = c.value1? c.value1.split(',').map(s=>s.trim()).filter(Boolean) : []; } }); }
    function normForSave(e){ (e.conditions||[]).forEach(c=>{ if(c.valueType==='ENUM' && Array.isArray(c.value1)){ c.value1 = c.value1.join(','); } }); }
    function openRuleEditor(rule){
      if(rule){ const e=JSON.parse(JSON.stringify(rule)); normForEdit(e); editState.value=e; }
      else {
        const g=activeGroup.value; const maxP=(g.rules||[]).reduce((m,r)=>Math.max(m,r.priority),0);
        editState.value = { id:0, ruleCode:'', ruleName:'新分档规则', priority:maxP+1, fallbackValue:5, matchMode:'AND', enabled:true, reason:'', conditions:[] };
      }
    }
    function saveRule(){
      const e=editState.value, g=activeGroup.value;
      if(!e.ruleName||!e.ruleName.trim()){ antd.message.error('请填写分档名称'); return; }
      if(e.fallbackValue==null||e.fallbackValue<0){ antd.message.error('兜底值不能为负'); return; }
      if(!(e.conditions||[]).length){ antd.message.error('请至少配置一条条件'); return; }
      normForSave(e);
      e.conditions.forEach((c,i)=>c.seqNo=i+1);
      const idx=g.rules.findIndex(r=>r.id===e.id);
      if(idx>=0) g.rules[idx]=e; else { e.id=nextId(); g.rules.push(e); }
      editState.value=null;
      antd.message.success('已保存（本地演示）');
    }
    function deleteRule(id){ const g=activeGroup.value; g.rules=g.rules.filter(r=>r.id!==id); antd.message.success('已删除（本地演示）'); }
    function addCondition(){
      const e=editState.value; const f=FIELD_REGISTRY[0];
      e.conditions.push({ seqNo:e.conditions.length+1, fieldName:f.fieldName, fieldLabel:f.fieldLabel, operator:f.supportedOps[0], valueType:f.valueType, value1:'', value2:'' });
    }
    function onFieldChange(idx){
      const e=editState.value; const c=e.conditions[idx]; const f=fieldMeta(c.fieldName);
      if(f){ c.fieldLabel=f.fieldLabel; c.valueType=f.valueType; c.operator=f.supportedOps[0]; c.value1=''; c.value2=''; }
    }

    function openGroupModal(g){
      if(g){ Object.assign(groupForm, { id:g.id, groupCode:g.groupCode, groupName:g.groupName, priority:g.priority, enabled:g.enabled, description:g.description }); }
      else { Object.assign(groupForm, { id:null, groupCode:'', groupName:'', priority:99, enabled:true, description:'' }); }
      groupModalOpen.value=true;
    }
    function saveGroup(){
      if(!groupForm.groupName.trim()){ antd.message.error('请填写规则组名称'); return; }
      if(!groupForm.groupCode.trim()){ antd.message.error('请填写规则组编码'); return; }
      const g = { id:groupForm.id||nextId(), groupCode:groupForm.groupCode.trim(), groupName:groupForm.groupName.trim(), priority:Number(groupForm.priority)||99, enabled:groupForm.enabled, description:groupForm.description||'', rules:groupForm.id? (groups.value.find(x=>x.id===groupForm.id)||{rules:[]}).rules : [] };
      const idx=groups.value.findIndex(x=>x.id===g.id);
      if(idx>=0) groups.value[idx]=g; else groups.value.push(g);
      groups.value.sort((a,b)=>a.priority-b.priority);
      selectedGroupId.value=g.id;
      groupModalOpen.value=false;
      antd.message.success('已保存（本地演示）');
    }
    function deleteGroup(){
      groups.value=groups.value.filter(g=>g.id!==selectedGroupId.value);
      selectedGroupId.value=groups.value[0]?groups.value[0].id:null;
      editState.value=null; antd.message.success('已删除（本地演示）');
    }

    function runGroupTest(){
      const g=activeGroup.value; if(!g) return;
      const r=matchGroup(g, testValues);
      if(r) testResult.value={ hit:true, ruleName:r.ruleName, fallbackValue:r.fallbackValue, reason:r.reason };
      else testResult.value={ hit:false };
    }

    return {
      OP, groups, groupsSorted, selectedGroupId, activeGroup, selectGroup,
      editState, openRuleEditor, saveRule, deleteRule, addCondition, onFieldChange,
      groupModalOpen, groupForm, openGroupModal, saveGroup, deleteGroup,
      registryOpen, registryGroups:registryGroups(), regCols, fieldLabel, fieldType, enumOptions, opOptionsFor, condValueText, fieldSelectOptions:fieldSelectOptions(),
      testValues, testFields, testResult, runGroupTest, ruleColumns,
    };
  },
  template:`
  <section class="strategy-page fallback-page">
    <div class="strategy-heading">
      <div><h2>兜底规则</h2>
      <div class="strategy-sub">按「规则组 → 分档规则 → 条件」三层配置兜底策略；规则按优先级依次匹配，首个命中规则生效。</div></div>
    </div>
    <a-alert type="info" show-icon style="margin-bottom:14px" message="条件字段来自配件主数据与指标宽表（如 销售价、ABC分类、近12月正订单行数），用什么字段、什么规则均可在页面上自由组合配置。" />
    <div class="fallback-layout">
      <div class="card fallback-side">
        <div class="fallback-side-hd">
          <span class="fallback-side-title">规则组（{{ groups.length }}）</span>
          <a-button type="primary" size="small" @click="openGroupModal(null)">+ 新增</a-button>
        </div>
        <div class="fallback-group-list">
          <div v-for="g in groupsSorted" :key="g.id" class="fallback-group-item" :class="{active:g.id===selectedGroupId}" @click="selectGroup(g.id)">
            <div class="fgi-top"><span class="fgi-name">{{ g.groupName }}</span><a-tag :color="g.enabled?'green':'default'" style="margin:0">{{ g.enabled?'启用':'停用' }}</a-tag></div>
            <div class="fgi-meta"><span class="fgi-prio">优先级 {{ g.priority }}</span><span>{{ (g.rules||[]).length }} 条分档</span></div>
          </div>
          <a-empty v-if="!groups.length" description="暂无规则组" />
        </div>
      </div>
      <div class="card fallback-main">
        <div v-if="!activeGroup" class="fallback-empty"><a-empty description="请在左侧选择一个规则组" /></div>
        <template v-else>
          <div class="strategy-toolbar">
            <span style="font-size:15px;font-weight:600;color:#223047">{{ activeGroup.groupName }}</span>
            <span class="strategy-sub" style="margin-left:8px">{{ activeGroup.description }}</span>
            <div style="margin-left:auto;display:flex;gap:10px">
              <a-button size="small" @click="openGroupModal(activeGroup)">编辑组</a-button>
              <a-button size="small" type="primary" @click="openRuleEditor(null)">+ 新增分档规则</a-button>
              <a-popconfirm title="确认删除该规则组及其所有分档规则？" @confirm="deleteGroup"><a-button size="small" danger>删除组</a-button></a-popconfirm>
            </div>
          </div>
          <div class="bt-sec-t">分档规则列表</div>
          <a-table :columns="ruleColumns" :data-source="activeGroup.rules" row-key="id" size="middle" :pagination="false" :scroll="{x:'max-content'}">
            <template #bodyCell="{column,record}">
              <template v-if="column.key==='priority'"><a-tag color="orange">{{ record.priority }}</a-tag></template>
              <template v-else-if="column.key==='conditions'">
                <span v-if="!(record.conditions||[]).length" style="color:#bfbfbf">无条件</span>
                <template v-else>
                  <template v-for="(c,i) in record.conditions" :key="i">
                    <span v-if="i>0" class="fb-link">{{ record.matchMode }}</span>
                    <span class="fb-chip">{{ c.fieldLabel }}</span><span class="fb-chip fb-op">{{ OP[c.operator] }}</span><span class="fb-chip">{{ condValueText(c) }}</span>
                  </template>
                </template>
              </template>
              <template v-else-if="column.key==='matchMode'"><a-tag :color="record.matchMode==='AND'?'blue':'purple'">{{ record.matchMode }}</a-tag></template>
              <template v-else-if="column.key==='fallbackValue'"><b style="color:#1677ff">{{ record.fallbackValue }}</b></template>
              <template v-else-if="column.key==='enabled'"><a-tag :color="record.enabled?'green':'default'">{{ record.enabled?'启用':'停用' }}</a-tag></template>
              <template v-else-if="column.key==='action'">
                <a @click="openRuleEditor(record)">编辑</a>
                <a-popconfirm title="确认删除该分档规则？" @confirm="deleteRule(record.id)"><a style="margin-left:12px;color:#ff4d4f">删除</a></a-popconfirm>
              </template>
            </template>
            <template #emptyText><a-empty description="暂无分档规则，点击右上角「+ 新增分档规则」" /></template>
          </a-table>

          <div v-if="editState" class="fallback-editor">
            <div class="bt-sec-t">{{ editState.id ? '编辑分档规则' : '新增分档规则' }}</div>
            <div class="strategy-grid">
              <label><span><span class="jlrs-req">*</span>分档名称</span><a-input v-model:value="editState.ruleName" placeholder="如 销售价 >2000"/></label>
              <label><span><span class="jlrs-req">*</span>优先级</span><a-input-number v-model:value="editState.priority" :min="1" style="width:100%"/></label>
              <label><span><span class="jlrs-req">*</span>兜底值</span><a-input-number v-model:value="editState.fallbackValue" :min="0" :precision="0" style="width:100%"/></label>
              <label><span>状态</span><a-select v-model:value="editState.enabled" :options="[{value:true,label:'启用'},{value:false,label:'停用'}]"/></label>
            </div>
            <div style="margin:14px 0 8px;display:flex;align-items:center;gap:12px">
              <span style="font-size:13px;color:#45536a">条件逻辑：</span>
              <a-radio-group v-model:value="editState.matchMode" button-style="solid">
                <a-radio-button value="AND">AND（全部满足）</a-radio-button>
                <a-radio-button value="OR">OR（任一满足）</a-radio-button>
              </a-radio-group>
            </div>
            <div class="fallback-cond-box">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                <span style="font-size:13px;font-weight:600;color:#1f1f1f">条件列表</span>
                <a-button type="primary" size="small" @click="addCondition">+ 添加条件</a-button>
              </div>
              <div v-if="!editState.conditions.length" class="strategy-sub">暂无条件，请点击「+ 添加条件」</div>
              <div v-for="(c,idx) in editState.conditions" :key="idx" class="fallback-cond-row">
                <span class="fb-seq">{{ idx+1 }}</span>
                <a-select v-model:value="c.fieldName" style="width:200px" @change="onFieldChange(idx)" :options="fieldSelectOptions"/>
                <a-select v-model:value="c.operator" style="width:110px" :options="opOptionsFor(c)"/>
                <template v-if="!['IS_NULL','IS_NOT_NULL'].includes(c.operator)">
                  <template v-if="c.operator==='BETWEEN'">
                    <a-input v-model:value="c.value1" placeholder="下限" style="width:110px" :type="fieldType(c.fieldName)==='NUMBER'?'number':'text'"/>
                    <span style="color:#8c8c8c">~</span>
                    <a-input v-model:value="c.value2" placeholder="上限" style="width:110px" :type="fieldType(c.fieldName)==='NUMBER'?'number':'text'"/>
                  </template>
                  <a-select v-else-if="fieldType(c.fieldName)==='ENUM'" v-model:value="c.value1" mode="multiple" allow-clear style="min-width:170px" :options="enumOptions(c.fieldName)"/>
                  <a-input v-else v-model:value="c.value1" placeholder="值" :type="fieldType(c.fieldName)==='NUMBER'?'number':'text'" style="width:140px"/>
                </template>
                <a style="margin-left:8px;color:#ff4d4f" @click="editState.conditions.splice(idx,1)">删除</a>
              </div>
            </div>
            <div class="strategy-grid" style="margin-top:14px">
              <label style="grid-column:1 / -1"><span>兜底原因（匹配后写入结果表）</span><a-input v-model:value="editState.reason" placeholder="如 C类兜底-销售价极高"/></label>
            </div>
            <div class="strategy-modal-footer">
              <a-button @click="editState=null">取消</a-button>
              <a-button type="primary" @click="saveRule">保存</a-button>
            </div>
          </div>

          <div class="bt-sec-t" style="margin-top:24px">规则模拟测试（{{ activeGroup.groupName }}）</div>
          <div class="fallback-test">
            <div class="strategy-grid" style="grid-template-columns:repeat(3,minmax(0,1fr))">
              <label v-for="fn in testFields" :key="fn"><span>{{ fieldLabel(fn) }}</span>
                <a-select v-if="fieldType(fn)==='ENUM'" v-model:value="testValues[fn]" allow-clear :options="enumOptions(fn)"/>
                <a-input v-else v-model:value="testValues[fn]" :type="fieldType(fn)==='NUMBER'?'number':'text'" :placeholder="fieldType(fn)==='NUMBER'?'数字':'文本'"/>
              </label>
            </div>
            <div style="margin-top:12px;display:flex;gap:8px;align-items:center">
              <a-button type="primary" size="small" @click="runGroupTest">运行测试</a-button>
              <a-button size="small" @click="registryOpen=true">字段注册表</a-button>
            </div>
            <div v-if="testResult" :class="['fallback-test-result', testResult.hit?'hit':'miss']">
              <template v-if="testResult.hit">命中规则 <b>{{ testResult.ruleName }}</b> → 兜底值 = <b>{{ testResult.fallbackValue }}</b>（原因：{{ testResult.reason }}）</template>
              <template v-else>未命中该组任何规则，不应用兜底</template>
            </div>
          </div>
        </template>
      </div>
    </div>
    <div class="strategy-footnote">匹配顺序：按规则组优先级升序 → 组内分档优先级升序，首个全部条件命中的规则生效；命中后将「兜底值 / 兜底原因」写入建储结果。条件字段统一来自配件主数据与指标宽表，引擎不区分来源。</div>

    <a-modal v-model:open="groupModalOpen" :title="groupForm.id?'编辑规则组':'新增规则组'" :width="560" :footer="null" :mask-closable="false">
      <div class="strategy-grid">
        <label><span><span class="jlrs-req">*</span>规则组名称</span><a-input v-model:value="groupForm.groupName" placeholder="如 C类兜底"/></label>
        <label><span><span class="jlrs-req">*</span>规则组编码</span><a-input v-model:value="groupForm.groupCode" placeholder="如 C_CLASS_FALLBACK"/></label>
        <label><span><span class="jlrs-req">*</span>执行优先级</span><a-input-number v-model:value="groupForm.priority" :min="1" style="width:100%"/></label>
        <label><span>状态</span><a-select v-model:value="groupForm.enabled" :options="[{value:true,label:'启用'},{value:false,label:'停用'}]"/></label>
        <label style="grid-column:1 / -1"><span>描述</span><a-input v-model:value="groupForm.description" placeholder="如 ABC分类=C类 且 兜底C类周均销量<8，按销售价分档"/></label>
      </div>
      <div class="strategy-modal-footer"><a-button @click="groupModalOpen=false">取消</a-button><a-button type="primary" @click="saveGroup">确定</a-button></div>
    </a-modal>

    <a-modal v-model:open="registryOpen" title="可用字段注册表（主数据 + 指标宽表）" :width="900" :footer="null">
      <div style="max-height:60vh;overflow:auto">
        <div v-for="g in registryGroups" :key="g.name" style="margin-bottom:18px">
          <div class="bt-sec-t" style="margin-bottom:8px">{{ g.name }}（{{ g.fields.length }} 个字段）</div>
          <a-table :columns="regCols" :data-source="g.fields" row-key="fieldName" size="small" :pagination="false">
            <template #bodyCell="{column,record}">
              <template v-if="column.key==='fieldName'"><span class="fallback-reg-code">{{ record.fieldName }}</span></template>
              <template v-else-if="column.key==='supportedOps'">
                <a-tag v-for="o in record.supportedOps" :key="o" color="orange" style="margin:0 4px 4px 0">{{ OP[o] }}</a-tag>
              </template>
              <template v-else>{{ record[column.dataIndex] }}</template>
            </template>
          </a-table>
        </div>
      </div>
    </a-modal>
  </section>`
};
})(typeof window!=='undefined'?window:{});
