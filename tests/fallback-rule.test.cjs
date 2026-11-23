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
  assert.equal(meta.fieldGroup,'指标宽表');
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

test('字段来源收窄：配件主数据 / 仓库主数据 / 指标宽表三类（指标宽表不再细分），仓库编码单独归入仓库主数据',()=>{
  const groups=m.fieldSourceGroups();
  assert.deepEqual(groups.map(k=>k.label),['配件主数据','仓库主数据','指标宽表']);
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
  assert.ok(src.includes('示例数据'),'页面应标注示例数据');
  assert.ok(src.includes('JLR_FALLBACK_RULE_COND_TIERS_V8'),'数据结构变更后存储键应升级，避免加载旧价档示例');
});

// ===== 2026-11-21 体验优化新增断言 =====
test('库存供应 5 字段从可配置参数移除，但旧配置仍能识别（兼容映射）',()=>{
  const groups=m.fieldSourceGroups();
  const allowed=new Set();
  groups.forEach(k=>k.fields.forEach(f=>allowed.add(f.fieldName)));
  const removed=['on_hand_qty','available_qty','purchase_inbound_qty','transfer_inbound_qty','backorder_qty'];
  for(const fn of removed){
    assert.ok(!allowed.has(fn),'字段下拉不应再出现已移除字段：'+fn);
    assert.ok(!m.FIELD_REGISTRY.some(f=>f.fieldName===fn),'FIELD_REGISTRY 不应再注册：'+fn);
  }
  // 兼容：旧配置引用这些字段时仍可显示中文名、值类型并参与匹配
  assert.equal(m.fieldLabel('on_hand_qty'),'账面库存');
  assert.equal(m.fieldType('on_hand_qty'),'NUMBER');
  const legacy=m.conds([['on_hand_qty','GT','10']]);
  assert.equal(m.evalRule({matchMode:'AND',conditions:legacy},{on_hand_qty:20}),true,'旧配置条件仍应能参与匹配');
  assert.equal(m.evalRule({matchMode:'AND',conditions:legacy},{on_hand_qty:5}),false);
});

test('指标宽表为单一类：不再有历史需求/兜底频次/预测/库存供应细分',()=>{
  const labels=m.fieldSourceGroups().map(k=>k.label);
  assert.deepEqual(labels,['配件主数据','仓库主数据','指标宽表']);
  assert.ok(!labels.some(l=>l.includes('·')),'来源标签不应再包含细分点号');
  const metric=m.fieldSourceGroups().find(k=>k.label==='指标宽表');
  assert.ok(metric.fields.length>0,'指标宽表应仍含字段');
  assert.ok(metric.fields.some(f=>f.fieldName==='sales_frequency_1y'),'近一年销售频次应归入指标宽表');
  // 所有指标类字段的 fieldGroup 统一为「指标宽表」
  for(const f of m.FIELD_REGISTRY.filter(f=>f.fieldGroup!=='配件主数据'&&f.fieldGroup!=='仓库主数据')){
    assert.equal(f.fieldGroup,'指标宽表','指标字段分组应统一：'+f.fieldName);
  }
});

test('取消档位名称：示例档位不再含 name 字段，卡片以兜底原因展示',()=>{
  for(const g of examples()){
    for(const t of g.tiers){
      assert.ok(!('name' in t),'档位不应再有 name 字段：'+t.id);
      assert.ok(t.reason&&String(t.reason).trim(),'档位兜底原因不应为空：'+t.id);
    }
  }
  const src=fs.readFileSync(path.join(__dirname,'../前端设计稿/fallback-rule.js'),'utf8');
  assert.ok(!src.includes('>档位名称<')&&!src.includes('jlrs-req">*</span>档位名称'),'页面不应再出现「档位名称」表单项');
  assert.ok(!src.includes('请填写档位名称'),'校验不应再要求档位名称');
  assert.ok(!src.includes('v-model:value="tierState.name"'),'档位编辑弹窗不应再绑定 name');
  assert.ok(src.includes('t.reason||\'未填写兜底原因\''),'分档卡片应以兜底原因作为展示标题');
});

test('兜底原因改为必填：validateTier 拦截空原因、放行已填原因，不再校验名称',()=>{
  const ok=m.validateTier({seq:10,fallbackValue:5,reason:'价格2~20兜底'});
  assert.deepEqual(ok,[]);
  const noReason=m.validateTier({seq:10,fallbackValue:5,reason:''});
  assert.ok(noReason.some(s=>s.includes('兜底原因')),'空兜底原因应被拦截');
  const blankReason=m.validateTier({seq:10,fallbackValue:5,reason:'   '});
  assert.ok(blankReason.some(s=>s.includes('兜底原因')),'纯空格兜底原因应被拦截');
  const noName=m.validateTier({seq:10,fallbackValue:5,reason:'有原因',name:''});
  assert.deepEqual(noName,[],'缺少 name 不应再导致校验失败');
  const neg=m.validateTier({seq:10,fallbackValue:-1,reason:'有原因'});
  assert.ok(neg.some(s=>s.includes('不能为负')));
});

test('精简页面：去除顶部冗长说明 alert 与冗余层级文案',()=>{
  const src=fs.readFileSync(path.join(__dirname,'../前端设计稿/fallback-rule.js'),'utf8');
  assert.ok(!src.includes('系统不预置生产规则'),'不应再展示冗长的预置规则说明');
  assert.ok(!src.includes('第二层 · 本组分档'),'不应再展示第二层层级文案');
  assert.ok(!src.includes('档位条件字段仅取自'),'不应再展示冗余的来源说明');
});

// ===== 2026-11-23 分档拖拽排序 =====
test('拖拽排序：移动到目标位置与连续点击上移/下移效果一致，其他档位不受影响',()=>{
  const ts=JSON.parse(JSON.stringify(tiersOf(examples(),'C_CLASS_FALLBACK')));
  const originalIds=ts.map(t=>t.id);
  const moved=m.moveTierTo(ts,'C_T1','C_T3');
  assert.deepEqual(moved.map(t=>t.id),['C_T2','C_T3','C_T1','C_T4','C_T5','C_T6','C_T7','C_T8']);
  assert.deepEqual(moved.map(t=>t.seq),[10,20,30,40,50,60,70,80],'档位序号应随展示顺序连续，不出现重复');
  assert.deepEqual(moved.slice(3).map(t=>t.id),originalIds.slice(3),'目标之后的分档顺序应保持不变');
  // 将 C_T1 连续下移两次，结果应与直接拖到 C_T3 一致
  let twice=JSON.parse(JSON.stringify(tiersOf(examples(),'C_CLASS_FALLBACK')));
  twice=m.moveTierTo(twice,'C_T1','C_T2');
  twice=m.moveTierTo(twice,'C_T1','C_T3');
  assert.deepEqual(twice.map(t=>t.id),moved.map(t=>t.id));
});

test('拖拽排序：同档位/无效 id 不改变顺序，匹配结果按新序号取首个命中',()=>{
  const g=examples();
  const cIdx=g.findIndex(x=>x.groupCode==='C_CLASS_FALLBACK');
  const ts=JSON.parse(JSON.stringify(g[cIdx].tiers));
  assert.deepEqual(m.moveTierTo(ts,'C_T1','C_T1').map(t=>t.id),ts.map(t=>t.id));
  assert.deepEqual(m.moveTierTo(ts,'C_T1','NOT_EXIST').map(t=>t.id),ts.map(t=>t.id));
  // 把 >2000 档拖到最前：同一物料应命中新首位（V=3）而非原首位（V=5）
  const reordered=m.moveTierTo(JSON.parse(JSON.stringify(tiersOf(examples(),'C_CLASS_FALLBACK'))),'C_T8','C_T1');
  const g2=g.map((x,i)=>i===cIdx?{...x,tiers:reordered}:x);
  assert.equal(m.matchAll(g2,{abcClassification:'C',demand_month_avg_3m:5,salesPrice:3000}).rule.fallbackValue,3);
  assert.equal(m.matchAll(g2,{abcClassification:'C',demand_month_avg_3m:5,salesPrice:0.01}).rule.fallbackValue,5,'新首位不满足时应继续按后续档位条件匹配');
});

test('分档卡片已接入拖拽事件与视觉反馈，且不影响原有操作按钮',()=>{
  const src=fs.readFileSync(path.join(__dirname,'../前端设计稿/fallback-rule.js'),'utf8');
  for(const token of ['draggable="true"','@dragstart="onTierDragStart($event,t)"','@dragover="onTierDragOver($event,t)"','@drop="onTierDrop($event,t)"','@dragend="onTierDragEnd"','fb-dragging','fb-drop-target','fb-drag-handle','拖动卡片可调整优先级']){
    assert.ok(src.includes(token),'分档卡片缺少拖拽支持：'+token);
  }
  assert.ok(src.includes('moveTier(t.id,-1)')&&src.includes('moveTier(t.id,1)'),'上移/下移入口应保留');
  assert.ok(src.includes('duplicateTier(t)')&&src.includes('openTierEditor(t)')&&src.includes('deleteTier(t.id)'),'复制/编辑/删除入口应保留');
  const css=fs.readFileSync(path.join(__dirname,'../前端设计稿/inventory-strategy.css'),'utf8');
  for(const token of ['.fb-rule-card.fb-dragging','.fb-rule-card.fb-drop-target','.fb-drag-handle']){
    assert.ok(css.includes(token),'拖拽样式缺失：'+token);
  }
});

console.log(checks+' meaningful checks passed');
