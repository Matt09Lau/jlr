const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const m=require('../前端设计稿/fallback-rule.js');
let checks=0;function test(name,fn){fn();checks++;console.log('PASS '+name);}

const examples=()=>m.exampleGroups();
const groupByCode=(g,code)=>g.find(x=>x.groupCode===code);
const tiersOf=(g,code)=>groupByCode(g,code).tiers;

// 权威价档表（需求说明 13.6）：空/≤0.01→5；>0.01~2→50；>2~20→10；>20~60→8；>60~200→6；>200~500→5；>500~2000→4；>2000→3
const PRICE_CASES=[
  [null,5],[0.01,5],[0.02,50],[2,50],[2.01,10],[20,10],[20.01,8],
  [60,8],[60.01,6],[200,6],[200.01,5],[500,5],[500.01,4],[2000,4],[2000.01,3],
];

test('示例数据：4 个规则组均具备组级适用范围且含 ABC 条件',()=>{
  const g=examples();
  assert.equal(g.length,4);
  for(const x of g){
    assert.ok(x.scope&&x.scope.conditions.length,'组 '+x.groupName+' 缺适用范围');
    assert.ok(x.scope.conditions.some(c=>c.fieldName==='abcClassification'),'组 '+x.groupName+' 缺ABC分类条件');
    assert.ok(Array.isArray(x.tiers),'组 '+x.groupName+' 缺组内分档');
    assert.ok(x.groupName.includes('示例'),'组 '+x.groupName+' 应标注为示例数据');
    assert.ok(!('tierMode' in x)&&!('tierField' in x),'组 '+x.groupName+' 不应存在价格分档模式/依据字段');
  }
  assert.deepEqual(g.map(x=>x.priority),[10,20,30,40]);
  assert.equal(g[0].groupName,'S0类兜底（示例）');
});

test('C/D 示例按销售价区间给出不同兜底值：8 档区间与权威价档表一致',()=>{
  const g=examples();
  for(const code of ['C_CLASS_FALLBACK','D_CLASS_FALLBACK']){
    const ts=tiersOf(g,code);
    assert.equal(ts.length,8,code+' 应有 8 档');
    assert.deepEqual(ts.map(t=>t.fallbackValue),[5,50,10,8,6,5,4,3],code+' 各档 V 应与权威价档一致');
    for(const t of ts){
      assert.ok(t.conditions.every(c=>c.fieldName==='salesPrice'),code+' 档位条件应全部为销售价：'+t.name);
    }
  }
  // 首档用 OR 表达「空或≤0.01」
  const first=tiersOf(g,'C_CLASS_FALLBACK')[0];
  assert.equal(first.matchMode,'OR');
  assert.ok(first.conditions.some(c=>c.operator==='IS_NULL'));
  assert.ok(first.conditions.some(c=>c.operator==='LE'&&c.value1==='0.01'));
});

test('C/D 价格区间边界逐一命中正确档位（含空值与各档临界值）',()=>{
  const g=examples();
  for(const [price,v] of PRICE_CASES){
    const c=m.matchAll(g,{abcClassification:'C',demand_month_avg_3m:5,salesPrice:price});
    const d=m.matchAll(g,{abcClassification:'D',salesPrice:price});
    assert.ok(c,'C 类价格 '+price+' 应命中');
    assert.ok(d,'D 类价格 '+price+' 应命中');
    assert.equal(c.rule.fallbackValue,v,'C 类价格 '+price+' 兜底值');
    assert.equal(d.rule.fallbackValue,v,'D 类价格 '+price+' 兜底值');
  }
});

test('组间隔离：改 C 组某档 V 不影响 D 组，反之亦然',()=>{
  const g=examples();
  const cIdx=g.findIndex(x=>x.groupCode==='C_CLASS_FALLBACK');
  const editedC=JSON.parse(JSON.stringify(g[cIdx]));
  editedC.tiers=editedC.tiers.map(x=>({...x,fallbackValue:99}));
  const g2=g.map((x,i)=>i===cIdx?editedC:x);
  assert.equal(m.matchAll(g2,{abcClassification:'C',demand_month_avg_3m:5,salesPrice:20}).rule.fallbackValue,99);
  assert.equal(m.matchAll(g2,{abcClassification:'D',salesPrice:20}).rule.fallbackValue,10);
  assert.equal(m.matchAll(g,{abcClassification:'D',salesPrice:20}).rule.fallbackValue,10);
  // C/D 档位对象不共享引用
  assert.notEqual(tiersOf(g,'C_CLASS_FALLBACK')[0],tiersOf(g,'D_CLASS_FALLBACK')[0]);
});

test('C 类月均销量门槛：<8 进入 C 组，≥8 不命中 C 组',()=>{
  const g=examples();
  assert.ok(m.matchAll(g,{abcClassification:'C',demand_month_avg_3m:7,salesPrice:20}).group.groupCode==='C_CLASS_FALLBACK');
  assert.equal(m.matchAll(g,{abcClassification:'C',demand_month_avg_3m:8,salesPrice:20}),null);
  assert.equal(m.matchAll(g,{abcClassification:'C',demand_month_avg_3m:null,salesPrice:20}),null);
});

test('ABC 互斥：各组不会跨类抢占（S0 不被 C 组拦截）',()=>{
  const g=examples();
  const s0=m.matchAll(g,{abcClassification:'S0',demand_month_avg_3m:1,salesPrice:20,potentialUnitDown:'true'});
  assert.ok(s0&&s0.group.groupCode==='S0_CLASS_FALLBACK','S0应命中S0组而非C组');
  assert.equal(s0.rule.fallbackValue,1);
  const se=m.matchAll(g,{abcClassification:'S2',sales_frequency_1y:2});
  assert.ok(se&&se.group.groupCode==='SE_CLASS_FALLBACK','S2应命中S/E组');
});

test('S/E 类按近一年销售频次分档：≥3 取 3、1~2 取 2、频次 0 不命中',()=>{
  const g=examples();
  assert.equal(m.matchAll(g,{abcClassification:'E',sales_frequency_1y:3}).rule.fallbackValue,3);
  assert.equal(m.matchAll(g,{abcClassification:'E',sales_frequency_1y:1}).rule.fallbackValue,2);
  assert.equal(m.matchAll(g,{abcClassification:'E',sales_frequency_1y:0}),null);
});

test('近一年销售频次采用指标宽表权威字段：注册存在且旧自定义字段已移除',()=>{
  const meta=m.fieldMeta('sales_frequency_1y');
  assert.ok(meta,'应注册近一年销售频次字段');
  assert.equal(meta.fieldLabel,'近一年销售频次');
  assert.equal(meta.fieldGroup,'指标-兜底频次');
  for(const old of ['positive_order_line_cnt_12m','positive_order_line_cnt_12m_all']){
    assert.equal(m.fieldMeta(old),undefined,'旧自定义频次字段应移除：'+old);
  }
  const se=groupByCode(examples(),'SE_CLASS_FALLBACK');
  for(const c of [...se.scope.conditions,...se.tiers[0].conditions,...se.tiers[1].conditions]){
    assert.notEqual(c.fieldName,'positive_order_line_cnt_12m_all');
  }
  assert.ok([...se.scope.conditions,...se.tiers[0].conditions].some(c=>c.fieldName==='sales_frequency_1y'));
});

test('未覆盖类别（A/B）不触发兜底',()=>{
  const g=examples();
  assert.equal(m.matchAll(g,{abcClassification:'A',salesPrice:20}),null);
  assert.equal(m.matchAll(g,{abcClassification:'B',salesPrice:20}),null);
});

test('停用规则组/档位不参与匹配',()=>{
  const g=examples();
  const g2=g.map(x=>x.groupCode==='D_CLASS_FALLBACK'?{...x,enabled:false}:x);
  assert.equal(m.matchAll(g2,{abcClassification:'D',salesPrice:20}),null);
  const g3=g.map(x=>x.groupCode==='C_CLASS_FALLBACK'?{...x,tiers:x.tiers.map(t=>({...t,enabled:false}))}:x);
  assert.equal(m.matchAll(g3,{abcClassification:'C',demand_month_avg_3m:5,salesPrice:20}),null);
});

test('配置校验：组缺 ABC 条件、重复序号、负兜底值被拦截',()=>{
  const g=examples()[3];
  assert.deepEqual(m.validateGroup(g),[]);
  const noAbc={...g,scope:{matchMode:'AND',conditions:g.scope.conditions.filter(c=>c.fieldName!=='abcClassification')}};
  assert.ok(m.validateGroup(noAbc).some(s=>s.includes('适用范围')));
  const dup={...g,tiers:[{...g.tiers[0]},{...g.tiers[0],seq:10}]};
  assert.ok(m.validateGroup(dup).some(s=>s.includes('序号不能重复')));
  const neg={...g,tiers:[{...g.tiers[0],fallbackValue:-1}]};
  assert.ok(m.validateGroup(neg).some(s=>s.includes('不能为负')));
  const badName={...g,groupName:''};
  assert.ok(m.validateGroup(badName).some(s=>s.includes('规则组名称')));
});

test('自定义配置：把仓库编码加入档位条件后按仓库命中/不命中',()=>{
  const g=examples();
  const dIdx=g.findIndex(x=>x.groupCode==='D_CLASS_FALLBACK');
  const editedD=JSON.parse(JSON.stringify(g[dIdx]));
  editedD.tiers=editedD.tiers.map(t=>({...t,conditions:m.conds([['warehouseCode','EQ','WH01']]),fallbackValue:7}));
  const g2=g.map((x,i)=>i===dIdx?editedD:x);
  assert.equal(m.matchAll(g2,{abcClassification:'D',warehouseCode:'WH01'}).rule.fallbackValue,7);
  assert.equal(m.matchAll(g2,{abcClassification:'D',warehouseCode:'WH02'}),null);
  assert.equal(m.matchAll(g2,{abcClassification:'D'}),null,'仓库编码缺失不应误命中');
  assert.equal(m.matchAll(g,{abcClassification:'D',warehouseCode:'WH02',salesPrice:20}).rule.fallbackValue,10,'原示例组不受影响');
});

test('自定义配置：在按销售价区间示例档之前插入普通条件档仍可用',()=>{
  const g=examples();
  const dIdx=g.findIndex(x=>x.groupCode==='D_CLASS_FALLBACK');
  const editedD=JSON.parse(JSON.stringify(g[dIdx]));
  editedD.tiers=[
    {id:'D_T0',seq:5,name:'销售价 >10（普通条件示例）',matchMode:'AND',conditions:m.conds([['salesPrice','GT','10']]),fallbackValue:9,reason:'',enabled:true},
    ...editedD.tiers
  ];
  const g2=g.map((x,i)=>i===dIdx?editedD:x);
  assert.equal(m.matchAll(g2,{abcClassification:'D',salesPrice:20}).rule.fallbackValue,9);
  assert.equal(m.matchAll(g2,{abcClassification:'D',salesPrice:2}).rule.fallbackValue,50,'落到 >0.01~2 档');
  assert.equal(m.matchAll(g2,{abcClassification:'D'}).rule.fallbackValue,5,'销售价缺失落到首档（空或≤0.01）');
});

test('字段来源收窄：配件主数据 / 仓库主数据 / 指标宽表三类，仓库编码单独归入仓库主数据',()=>{
  const groups=m.fieldSourceGroups();
  assert.deepEqual(groups.map(k=>k.label),['配件主数据','仓库主数据','指标宽表·历史需求','指标宽表·兜底频次','指标宽表·预测','指标宽表·库存供应']);
  const allowed=new Set();
  groups.forEach(k=>k.fields.forEach(f=>allowed.add(f.fieldName)));
  assert.equal(allowed.size,m.FIELD_REGISTRY.length,'所有注册字段都应出现在来源分组中');
  assert.ok(allowed.has('warehouseCode'),'可配置参数应包含仓库编码');
  assert.ok(allowed.has('salesPrice'),'可配置参数应包含销售价');
  assert.equal(m.fieldMeta('warehouseCode').fieldLabel,'仓库编码');
  assert.equal(m.fieldMeta('warehouseCode').fieldGroup,'仓库主数据','仓库编码应归入仓库主数据而非配件主数据');
  const whGroup=groups.find(k=>k.label==='仓库主数据');
  assert.deepEqual(whGroup.fields.map(f=>f.fieldName),['warehouseCode'],'仓库主数据来源应仅含仓库编码');
  const partGroup=groups.find(k=>k.label==='配件主数据');
  assert.ok(!partGroup.fields.some(f=>f.fieldName==='warehouseCode'),'配件主数据不应再含仓库编码');
  const banned=['target_fill_rate_pct','service_factor_z','extra_stock_days','purchase_lt_effective_days','planning_cycle_days','risk_low_factor','risk_high_factor','interwarehouse_lt_days','stock_allowed_flag'];
  for(const fn of banned){
    assert.ok(!allowed.has(fn),'来源分组不应含参数字段 '+fn);
    assert.equal(m.fieldMeta(fn),undefined,'注册表不应再注册参数字段 '+fn);
  }
  const used=new Set();
  examples().forEach(g=>{
    (g.scope.conditions||[]).forEach(c=>used.add(c.fieldName));
    (g.tiers||[]).forEach(t=>(t.conditions||[]).forEach(c=>used.add(c.fieldName)));
  });
  for(const fn of used) assert.ok(allowed.has(fn),'示例条件字段 '+fn+' 不在允许来源内');
});

test('新建规则组编码由系统自动生成（无需人工填写）',()=>{
  const g=examples()[3];
  assert.deepEqual(m.validateGroup(g),[]);
  const noCode={...g,groupCode:''};
  assert.deepEqual(m.validateGroup(noCode),[]);
  const c1=m.nextGroupCode(),c2=m.nextGroupCode();
  assert.ok(/^FG_\d+$/.test(c1),'自动编码应形如 FG_<序号>：'+c1);
  assert.notEqual(c1,c2,'连续两次自动编码不能重复');
});

test('页面已去掉字段注册表/命中试算/恢复默认三个按钮及对应弹窗',()=>{
  const src=fs.readFileSync(path.join(__dirname,'../前端设计稿/fallback-rule.js'),'utf8');
  for(const word of ['字段注册表','命中试算','恢复默认','registryOpen','testOpen','resetDefaults','clearStore']){
    assert.ok(!src.includes(word),'配置页不应再出现：'+word);
  }
  assert.ok(src.includes('当前 4 组为示例数据'),'页面应标注示例数据');
  assert.ok(src.includes('JLR_FALLBACK_RULE_COND_TIERS_V8'),'数据结构变更后存储键应升级，避免加载旧价档示例');
});

console.log(checks+' meaningful checks passed');
