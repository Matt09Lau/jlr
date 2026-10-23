(function(root){
'use strict';
const definitions={
  "PO": [
    {
      "key": "buildType",
      "label": "建储类型",
      "sourceOrder": 1,
      "sourceLabel": "建储类型",
      "logic": "",
      "type": "text"
    },
    {
      "key": "buildVersion",
      "label": "版本号",
      "sourceOrder": 2,
      "sourceLabel": "版本号",
      "logic": "年度加两位周数，格式YYYYWW，如202643；当前演示按ISO周历。",
      "type": "text"
    },
    {
      "key": "useDate",
      "label": "建储日期",
      "sourceOrder": 3,
      "sourceLabel": "建储日期",
      "logic": "PO：下个月1日。",
      "type": "date"
    },
    {
      "key": "part",
      "label": "配件号",
      "sourceOrder": 4,
      "sourceLabel": "配件号",
      "logic": "",
      "type": "text"
    },
    {
      "key": "partName",
      "label": "配件名称",
      "sourceOrder": 5,
      "sourceLabel": "配件名称",
      "logic": "",
      "type": "text"
    },
    {
      "key": "wh",
      "label": "建储仓库编码",
      "sourceOrder": 6,
      "sourceLabel": "建储仓库编码",
      "logic": "",
      "type": "text"
    },
    {
      "key": "whName",
      "label": "建储仓库名称",
      "sourceOrder": 7,
      "sourceLabel": "建储仓库名称",
      "logic": "",
      "type": "text"
    },
    {
      "key": "target",
      "label": "目标库存",
      "sourceOrder": 8,
      "sourceLabel": "目标库存",
      "logic": "",
      "type": "text"
    },
    {
      "key": "targetBreak",
      "label": "目标库存突破风控线",
      "sourceOrder": 9,
      "sourceLabel": "目标库存突破风控线",
      "logic": "目标库存>原最高风控线：突破最高风控线；目标库存<原最低风控线：突破最低风控线；其他：否，等于边界不突破。",
      "type": "flag"
    },
    {
      "key": "reorder",
      "label": "再订购点",
      "sourceOrder": 10,
      "sourceLabel": "再订购点",
      "logic": "",
      "type": "text"
    },
    {
      "key": "reorderBreak",
      "label": "再订购点突破风控线",
      "sourceOrder": 11,
      "sourceLabel": "再订购点突破风控线",
      "logic": "是：再订购点>最高风控线或再订购点＜最低风控线\n否：其他",
      "type": "flag"
    },
    {
      "key": "min",
      "label": "最低风控线",
      "sourceOrder": 12,
      "sourceLabel": "最低风控线",
      "logic": "",
      "type": "text"
    },
    {
      "key": "max",
      "label": "最高风控线",
      "sourceOrder": 13,
      "sourceLabel": "最高风控线",
      "logic": "",
      "type": "text"
    },
    {
      "key": "riskTarget",
      "label": "风控后目标库存",
      "sourceOrder": 14,
      "sourceLabel": "风控后目标库存",
      "logic": "",
      "type": "text"
    },
    {
      "key": "riskReorder",
      "label": "风控后再订购点",
      "sourceOrder": 15,
      "sourceLabel": "风控后再订购点",
      "logic": "",
      "type": "text"
    },
    {
      "key": "floor",
      "label": "兜底值",
      "sourceOrder": 16,
      "sourceLabel": "兜底值",
      "logic": "",
      "type": "text"
    },
    {
      "key": "floorApplied",
      "label": "是否应用兜底值",
      "sourceOrder": 17,
      "sourceLabel": "是否应用兜底值",
      "logic": "是：风控后目标库存＜兜底值\n否：其他",
      "type": "flag"
    },
    {
      "key": "floorReason",
      "label": "兜底原因",
      "sourceOrder": 18,
      "sourceLabel": "兜底原因",
      "logic": "",
      "type": "text"
    },
    {
      "key": "floorTarget",
      "label": "兜底后目标库存",
      "sourceOrder": 19,
      "sourceLabel": "兜底后目标库存",
      "logic": "",
      "type": "text"
    },
    {
      "key": "floorReorder",
      "label": "兜底后再订购点",
      "sourceOrder": 20,
      "sourceLabel": "兜底后再订购点",
      "logic": "",
      "type": "text"
    },
    {
      "key": "floorMin",
      "label": "兜底后最低风控线",
      "sourceOrder": 21,
      "sourceLabel": "兜底后最低风控线",
      "logic": "",
      "type": "text"
    },
    {
      "key": "floorMax",
      "label": "兜底后最高风控线",
      "sourceOrder": 22,
      "sourceLabel": "兜底后最高风控线",
      "logic": "",
      "type": "text"
    },
    {
      "key": "noStockReason",
      "label": "不建储原因",
      "sourceOrder": 23,
      "sourceLabel": "不建储原因",
      "logic": "配件主数据.采购类别=D 直供供应商，显示为直供供应商，无需建储",
      "type": "text"
    },
    {
      "key": "adjustTarget",
      "label": "调整后目标库存",
      "sourceOrder": 24,
      "sourceLabel": "调整后目标库存",
      "logic": "",
      "type": "text"
    },
    {
      "key": "adjustReorder",
      "label": "调整后再订购点",
      "sourceOrder": 25,
      "sourceLabel": "调整后再订购点",
      "logic": "",
      "type": "text"
    },
    {
      "key": "adjustMin",
      "label": "调整后最低风控线",
      "sourceOrder": 26,
      "sourceLabel": "调整后最低风控线",
      "logic": "",
      "type": "text"
    },
    {
      "key": "adjustMax",
      "label": "调整后最高风控线",
      "sourceOrder": 27,
      "sourceLabel": "调整后最高风控线",
      "logic": "",
      "type": "text"
    },
    {
      "key": "adjustReason",
      "label": "调整原因",
      "sourceOrder": 28,
      "sourceLabel": "调整原因",
      "logic": "人工录入",
      "type": "text"
    },
    {
      "key": "abc",
      "label": "ABC 分类",
      "sourceOrder": 29,
      "sourceLabel": "ABC 分类",
      "logic": "",
      "type": "text"
    },
    {
      "key": "xyz",
      "label": "XYZ 分类",
      "sourceOrder": 30,
      "sourceLabel": "XYZ 分类",
      "logic": "",
      "type": "text"
    },
    {
      "key": "volume",
      "label": "体积分类",
      "sourceOrder": 31,
      "sourceLabel": "体积分类",
      "logic": "",
      "type": "text"
    },
    {
      "key": "planner",
      "label": "计划员",
      "sourceOrder": 32,
      "sourceLabel": "计划员",
      "logic": "",
      "type": "text"
    },
    {
      "key": "monthly",
      "label": "月度预测数量",
      "sourceOrder": 33,
      "sourceLabel": "月度预测数量",
      "logic": "",
      "type": "text"
    },
    {
      "key": "monthlyDate",
      "label": "月度预测数据日期",
      "sourceOrder": 34,
      "sourceLabel": "月度预测数据日期",
      "logic": "",
      "type": "text"
    },
    {
      "key": "monthlySales",
      "label": "近 3 个月月均销量",
      "sourceOrder": 35,
      "sourceLabel": "近 3 个月月均销量",
      "logic": "",
      "type": "text"
    },
    {
      "key": "volatility",
      "label": "近 6 个月需求波动标准差",
      "sourceOrder": 36,
      "sourceLabel": "近 6 个月需求波动标准差",
      "logic": "",
      "type": "text"
    },
    {
      "key": "purchaseDays",
      "label": "采购 LT（天）",
      "sourceOrder": 37,
      "sourceLabel": "采购 LT（天）",
      "logic": "",
      "type": "text"
    },
    {
      "key": "purchaseSource",
      "label": "采购 LT取值来源",
      "sourceOrder": 38,
      "sourceLabel": "采购 LT取值来源",
      "logic": "",
      "type": "source"
    },
    {
      "key": "cycle",
      "label": "计划周期（天）",
      "sourceOrder": 39,
      "sourceLabel": "计划周期（天）",
      "logic": "",
      "type": "text"
    },
    {
      "key": "cycleSource",
      "label": "计划周期取值来源",
      "sourceOrder": 40,
      "sourceLabel": "计划周期取值来源",
      "logic": "",
      "type": "source"
    },
    {
      "key": "days",
      "label": "增储天数",
      "sourceOrder": 41,
      "sourceLabel": "增储天数",
      "logic": "",
      "type": "text"
    },
    {
      "key": "daysSource",
      "label": "增储天数取值来源",
      "sourceOrder": 42,
      "sourceLabel": "增储天数取值来源",
      "logic": "",
      "type": "source"
    },
    {
      "key": "start",
      "label": "增储生效日期",
      "sourceOrder": 43,
      "sourceLabel": "增储生效日期",
      "logic": "",
      "type": "date"
    },
    {
      "key": "end",
      "label": "增储失效日期",
      "sourceOrder": 44,
      "sourceLabel": "增储失效日期",
      "logic": "",
      "type": "date"
    },
    {
      "key": "rate",
      "label": "目标满足率",
      "sourceOrder": 45,
      "sourceLabel": "目标满足率",
      "logic": "",
      "type": "text"
    },
    {
      "key": "rateSource",
      "label": "目标满足率取值来源",
      "sourceOrder": 46,
      "sourceLabel": "目标满足率取值来源",
      "logic": "",
      "type": "source"
    },
    {
      "key": "service",
      "label": "服务水平",
      "sourceOrder": 47,
      "sourceLabel": "服务水平",
      "logic": "",
      "type": "text"
    },
    {
      "key": "serviceSource",
      "label": "服务水平取值来源",
      "sourceOrder": 48,
      "sourceLabel": "服务水平取值来源",
      "logic": "",
      "type": "source"
    },
    {
      "key": "maxCoef",
      "label": "最高风控线系数",
      "sourceOrder": 49,
      "sourceLabel": "最高风控线系数",
      "logic": "",
      "type": "text"
    },
    {
      "key": "maxCoefSource",
      "label": "最高风控线系数取值来源",
      "sourceOrder": 50,
      "sourceLabel": "最高风控线系数取值来源",
      "logic": "",
      "type": "source"
    },
    {
      "key": "maxDays",
      "label": "最高风控线调整天数",
      "sourceOrder": 51,
      "sourceLabel": "最高风控线调整天数",
      "logic": "",
      "type": "text"
    },
    {
      "key": "maxDaysSource",
      "label": "最高风控线调整天数取值来源",
      "sourceOrder": 52,
      "sourceLabel": "最高风控线调整天数取值来源",
      "logic": "",
      "type": "source"
    },
    {
      "key": "minCoef",
      "label": "最低风控线系数",
      "sourceOrder": 53,
      "sourceLabel": "最高风控线系数",
      "logic": "",
      "type": "text"
    },
    {
      "key": "minCoefSource",
      "label": "最低风控线系数取值来源",
      "sourceOrder": 54,
      "sourceLabel": "最高风控线系数取值来源",
      "logic": "",
      "type": "source"
    },
    {
      "key": "minDays",
      "label": "最低风控线调整天数",
      "sourceOrder": 55,
      "sourceLabel": "最高风控线调整天数",
      "logic": "",
      "type": "text"
    },
    {
      "key": "minDaysSource",
      "label": "最低风控线调整天数取值来源",
      "sourceOrder": 56,
      "sourceLabel": "最高风控线系数取值来源",
      "logic": "",
      "type": "source"
    },
    {
      "key": "updated",
      "label": "更新时间",
      "sourceOrder": 57,
      "sourceLabel": "更新时间",
      "logic": "",
      "type": "text"
    }
  ],
  "STO": [
    {
      "key": "buildType",
      "label": "建储类型",
      "sourceOrder": 1,
      "sourceLabel": "建储类型",
      "logic": "",
      "type": "text"
    },
    {
      "key": "buildVersion",
      "label": "版本号",
      "sourceOrder": 2,
      "sourceLabel": "版本号",
      "logic": "年度加两位周数，格式YYYYWW，如202643；当前演示按ISO周历。",
      "type": "text"
    },
    {
      "key": "useDate",
      "label": "建储日期",
      "sourceOrder": 3,
      "sourceLabel": "建储日期",
      "logic": "本周建储使用下周一；下周建储使用下下周一。",
      "type": "date"
    },
    {
      "key": "part",
      "label": "配件号",
      "sourceOrder": 4,
      "sourceLabel": "配件号",
      "logic": "",
      "type": "text"
    },
    {
      "key": "partName",
      "label": "配件名称",
      "sourceOrder": 5,
      "sourceLabel": "配件名称",
      "logic": "",
      "type": "text"
    },
    {
      "key": "wh",
      "label": "建储仓库编码",
      "sourceOrder": 6,
      "sourceLabel": "建储仓库编码",
      "logic": "",
      "type": "text"
    },
    {
      "key": "whName",
      "label": "建储仓库名称",
      "sourceOrder": 7,
      "sourceLabel": "建储仓库名称",
      "logic": "",
      "type": "text"
    },
    {
      "key": "shipWh",
      "label": "发货仓库编码",
      "sourceOrder": 8,
      "sourceLabel": "发货仓库编码",
      "logic": "",
      "type": "text"
    },
    {
      "key": "shipName",
      "label": "发货仓库名称",
      "sourceOrder": 9,
      "sourceLabel": "发货仓库名称",
      "logic": "",
      "type": "text"
    },
    {
      "key": "target",
      "label": "目标库存",
      "sourceOrder": 10,
      "sourceLabel": "目标库存",
      "logic": "",
      "type": "text"
    },
    {
      "key": "targetBreak",
      "label": "目标库存突破风控线",
      "sourceOrder": 11,
      "sourceLabel": "目标库存突破风控线",
      "logic": "目标库存>原最高风控线：突破最高风控线；目标库存<原最低风控线：突破最低风控线；其他：否，等于边界不突破。",
      "type": "flag"
    },
    {
      "key": "min",
      "label": "最低风控线",
      "sourceOrder": 14,
      "sourceLabel": "最低风控线",
      "logic": "",
      "type": "text"
    },
    {
      "key": "max",
      "label": "最高风控线",
      "sourceOrder": 15,
      "sourceLabel": "最高风控线",
      "logic": "",
      "type": "text"
    },
    {
      "key": "riskTarget",
      "label": "风控后目标库存",
      "sourceOrder": 16,
      "sourceLabel": "风控后目标库存",
      "logic": "",
      "type": "text"
    },
    {
      "key": "noStockReason",
      "label": "不建储原因",
      "sourceOrder": 18,
      "sourceLabel": "不建储原因",
      "logic": "备货规则.配货表示=禁止备货，显示对应的不建储原因",
      "type": "text"
    },
    {
      "key": "adjustTarget",
      "label": "调整后目标库存",
      "sourceOrder": 19,
      "sourceLabel": "调整后目标库存",
      "logic": "",
      "type": "text"
    },
    {
      "key": "adjustMin",
      "label": "调整后最低风控线",
      "sourceOrder": 21,
      "sourceLabel": "调整后最低风控线",
      "logic": "",
      "type": "text"
    },
    {
      "key": "adjustMax",
      "label": "调整后最高风控线",
      "sourceOrder": 22,
      "sourceLabel": "调整后最高风控线",
      "logic": "",
      "type": "text"
    },
    {
      "key": "adjustReason",
      "label": "调整原因",
      "sourceOrder": 23,
      "sourceLabel": "调整原因",
      "logic": "人工录入",
      "type": "text"
    },
    {
      "key": "abc",
      "label": "ABC 分类",
      "sourceOrder": 24,
      "sourceLabel": "ABC 分类",
      "logic": "",
      "type": "text"
    },
    {
      "key": "xyz",
      "label": "XYZ 分类",
      "sourceOrder": 25,
      "sourceLabel": "XYZ 分类",
      "logic": "",
      "type": "text"
    },
    {
      "key": "volume",
      "label": "体积分类",
      "sourceOrder": 26,
      "sourceLabel": "体积分类",
      "logic": "",
      "type": "text"
    },
    {
      "key": "planner",
      "label": "计划员",
      "sourceOrder": 27,
      "sourceLabel": "计划员",
      "logic": "",
      "type": "text"
    },
    {
      "key": "weekly",
      "label": "周度预测数量",
      "sourceOrder": 28,
      "sourceLabel": "周度预测数量",
      "logic": "",
      "type": "text"
    },
    {
      "key": "weeklyDate",
      "label": "周度预测数据日期",
      "sourceOrder": 29,
      "sourceLabel": "月度预测数据日期",
      "logic": "",
      "type": "text"
    },
    {
      "key": "weeklySales",
      "label": "近 12 周周均销量",
      "sourceOrder": 30,
      "sourceLabel": "近 3 个月月均销量",
      "logic": "",
      "type": "text"
    },
    {
      "key": "weeklyRiskSales",
      "label": "近 8 周周均销量",
      "sourceOrder": null,
      "sourceLabel": "正文补充",
      "logic": "STO风控公式使用的近8周周均销量，独立于初始输入的近12周周均销量。",
      "type": "text"
    },
    {
      "key": "volatility",
      "label": "近 8 周需求波动标准差",
      "sourceOrder": 31,
      "sourceLabel": "近 6 个月需求波动标准差",
      "logic": "",
      "type": "text"
    },
    {
      "key": "transferDays",
      "label": "库间 LT（天）",
      "sourceOrder": 32,
      "sourceLabel": "采购 LT（天）",
      "logic": "",
      "type": "text"
    },
    {
      "key": "transferSource",
      "label": "库间 LT取值来源",
      "sourceOrder": 33,
      "sourceLabel": "采购 LT取值来源",
      "logic": "1.配置表\n2.全局参数",
      "type": "source"
    },
    {
      "key": "transferCycle",
      "label": "调拨周期（天）",
      "sourceOrder": 34,
      "sourceLabel": "计划周期（天）",
      "logic": "",
      "type": "text"
    },
    {
      "key": "transferCycleSource",
      "label": "调拨周期取值来源",
      "sourceOrder": 35,
      "sourceLabel": "计划周期取值来源",
      "logic": "1.配置表\n2.全局参数",
      "type": "source"
    },
    {
      "key": "days",
      "label": "增储天数",
      "sourceOrder": 36,
      "sourceLabel": "增储天数",
      "logic": "",
      "type": "text"
    },
    {
      "key": "daysSource",
      "label": "增储天数取值来源",
      "sourceOrder": 37,
      "sourceLabel": "增储天数取值来源",
      "logic": "1.配置表\n2.全局参数",
      "type": "source"
    },
    {
      "key": "start",
      "label": "增储生效日期",
      "sourceOrder": 38,
      "sourceLabel": "增储生效日期",
      "logic": "",
      "type": "date"
    },
    {
      "key": "end",
      "label": "增储失效日期",
      "sourceOrder": 39,
      "sourceLabel": "增储失效日期",
      "logic": "",
      "type": "date"
    },
    {
      "key": "rate",
      "label": "目标满足率",
      "sourceOrder": 40,
      "sourceLabel": "目标满足率",
      "logic": "",
      "type": "text"
    },
    {
      "key": "rateSource",
      "label": "目标满足率取值来源",
      "sourceOrder": 41,
      "sourceLabel": "目标满足率取值来源",
      "logic": "1.配置表\n2.全局参数",
      "type": "source"
    },
    {
      "key": "service",
      "label": "服务水平",
      "sourceOrder": 42,
      "sourceLabel": "服务水平",
      "logic": "",
      "type": "text"
    },
    {
      "key": "serviceSource",
      "label": "服务水平取值来源",
      "sourceOrder": 43,
      "sourceLabel": "服务水平取值来源",
      "logic": "1.配置表\n2.全局参数",
      "type": "source"
    },
    {
      "key": "maxCoef",
      "label": "最高风控线系数",
      "sourceOrder": 44,
      "sourceLabel": "最高风控线系数",
      "logic": "",
      "type": "text"
    },
    {
      "key": "maxCoefSource",
      "label": "最高风控线系数取值来源",
      "sourceOrder": 45,
      "sourceLabel": "最高风控线系数取值来源",
      "logic": "1.配置表\n2.全局参数",
      "type": "source"
    },
    {
      "key": "maxDays",
      "label": "最高风控线调整天数",
      "sourceOrder": 46,
      "sourceLabel": "最高风控线调整天数",
      "logic": "",
      "type": "text"
    },
    {
      "key": "maxDaysSource",
      "label": "最高风控线调整天数取值来源",
      "sourceOrder": 47,
      "sourceLabel": "最高风控线调整天数取值来源",
      "logic": "1.配置表\n2.全局参数",
      "type": "source"
    },
    {
      "key": "minCoef",
      "label": "最低风控线系数",
      "sourceOrder": 48,
      "sourceLabel": "最高风控线系数",
      "logic": "",
      "type": "text"
    },
    {
      "key": "minCoefSource",
      "label": "最低风控线系数取值来源",
      "sourceOrder": 49,
      "sourceLabel": "最高风控线系数取值来源",
      "logic": "1.配置表\n2.全局参数",
      "type": "source"
    },
    {
      "key": "minDays",
      "label": "最低风控线调整天数",
      "sourceOrder": 50,
      "sourceLabel": "最高风控线调整天数",
      "logic": "",
      "type": "text"
    },
    {
      "key": "minDaysSource",
      "label": "最低风控线调整天数取值来源",
      "sourceOrder": 51,
      "sourceLabel": "最高风控线系数取值来源",
      "logic": "1.配置表\n2.全局参数",
      "type": "source"
    },
    {
      "key": "updated",
      "label": "更新时间",
      "sourceOrder": 52,
      "sourceLabel": "更新时间",
      "logic": "",
      "type": "text"
    }
  ]
};
definitions.STO.splice(definitions.STO.findIndex(f=>f.key==='adjustTarget')+1,0,{key:'adjustReorder',label:'调整后再订购点',sourceOrder:null,sourceLabel:'用户确认新增',logic:'STO支持人工维护再订购点；未维护时为空，不代表新增系统计算公式。',type:'text'});
const warehouses={SH01:'上海中心仓',BJ01:'北京区域仓',GZ01:'广州区域仓',CD01:'成都区域仓'};
const partNames=['机油滤清器','空气滤清器','前制动片','燃油泵','冷却液管','点火线圈','车门锁','转向机'];
for(const [key,after] of [['reorder','targetBreak'],['reorderBreak','reorder'],['riskReorder','riskTarget']]){const f=definitions.PO.find(f=>f.key===key);definitions.STO.splice(definitions.STO.findIndex(f=>f.key===after)+1,0,{...f,sourceOrder:null,logic:'STO结果展示字段；当前使用演示快照，生产计算口径待确认。'});}
definitions.STO=definitions.STO.filter(f=>f.key!=='weeklyRiskSales');
const sourcePairs={purchaseDays:'purchaseSource',transferDays:'transferSource',cycle:'cycleSource',transferCycle:'transferCycleSource',days:'daysSource',rate:'rateSource',service:'serviceSource',maxCoef:'maxCoefSource',maxDays:'maxDaysSource',minCoef:'minCoefSource',minDays:'minDaysSource'};
const present=v=>v!==''&&v!==null&&v!==undefined;
const dateNow=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const stamp=()=>new Date().toLocaleString('sv-SE',{timeZone:'Asia/Shanghai'});
function period(kind,index=0,reference=dateNow()){
 const now=new Date(reference+'T00:00:00Z'),week=new Date(now);week.setUTCDate(week.getUTCDate()+4-(week.getUTCDay()||7));
 const y=week.getUTCFullYear(),num=Math.ceil(((week-Date.UTC(y,0,1))/86400000+1)/7);let use;
 if(kind==='PO')use=new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth()+1,1));
 else{use=new Date(now);use.setUTCDate(use.getUTCDate()-((use.getUTCDay()+6)%7)+7+(index%2)*7);}
 return{buildVersion:''+y+String(num).padStart(2,'0'),useDate:use.toISOString().slice(0,10)};
}
function isBreak(row,key){
 if(!present(row[key]))return false;let lo='min',hi='max';
 if(key.startsWith('floor')){lo='floorMin';hi='floorMax';}if(key.startsWith('adjust')){lo='adjustMin';hi='adjustMax';}
 return ['target','reorder','riskTarget','riskReorder','floorTarget','floorReorder','adjustTarget','adjustReorder'].includes(key)&&present(row[lo])&&present(row[hi])&&(Number(row[key])<Number(row[lo])||Number(row[key])>Number(row[hi]));
}
function hasGlobal(row,key){return Boolean(sourcePairs[key]&&row[sourcePairs[key]]==='全局参数');}
function breachDirection(row,key){
 if(!isBreak(row,key))return '否';
 return Number(row[key])>Number(row.max)?'突破最高风控线':'突破最低风控线';
}
function finalize(input){
 const r={...input};const po=r.buildType==='PO 建储';if(!po){if(!present(r.reorder))r.reorder=200;if(!present(r.riskReorder))r.riskReorder=Math.max(Number(r.min),Math.min(Number(r.max),Number(r.reorder)));}
 r.targetBreak=breachDirection(r,'target');
 r.reorderBreak=breachDirection(r,'reorder');if(po){r.floorApplied=present(r.floor)&&Number(r.riskTarget)<Number(r.floor)?'是':'否';}
 const sysTarget=po?r.floorTarget:r.riskTarget;
 r.adjustTarget=present(r.manualTarget)?Number(r.manualTarget):sysTarget;
 r.adjustMin=present(r.manualMin)?Number(r.manualMin):(po?r.floorMin:r.min);
 r.adjustMax=present(r.manualMax)?Number(r.manualMax):(po?r.floorMax:r.max);
 r.adjustReorder=present(r.manualReorder)?Number(r.manualReorder):(po?r.floorReorder:r.riskReorder);
 r.adjustReason=r.manualReason||'';
 if(r.noStockReason){r.adjustTarget=0;r.adjustMin=0;r.adjustMax=0;r.adjustReorder=0;}
 return r;
}
function seed(kind,reference=dateNow()){
 return Array.from({length:16},(_,i)=>{
 const po=kind==='PO',fallback=po&&i%4===0,direct=po&&i%7===6,forbidden=!po&&i%7===6;
 const low=100,high=450,target=i%3===0?500:i%3===1?80:300,reorder=i%5===0?500:i%5===4?80:200;
 const riskReorder=Math.max(low,Math.min(high,reorder)),riskTarget=po?Math.min(riskReorder+150,high):Math.max(low,Math.min(high,target));
 const floor=po?(fallback?550:50):null,apply=fallback&&riskTarget<floor;
 const r={id:'result-v5-'+kind+'-'+i,buildType:po?'PO 建储':'STO 建储',...period(kind,i,reference),part:'LR'+String(i%8+1).padStart(6,'0'),partName:partNames[i%8],wh:Object.keys(warehouses)[Math.floor(i/8)],whName:warehouses[Object.keys(warehouses)[Math.floor(i/8)]],shipWh:po?'':'GZ01',shipName:po?'':'广州区域仓',target,reorder,min:low,max:high,riskTarget,riskReorder,floor,floorReason:apply?'低频配件兜底规则':'',floorTarget:po?(apply?floor:riskTarget):null,floorReorder:po?(apply?Math.ceil(.75*floor):riskReorder):null,floorMin:po?(apply?Math.ceil(.5*floor):low):null,floorMax:po?(apply?floor:high):null,noStockReason:direct?'直供供应商，无需建储':forbidden?'备货规则禁止备货':'',abc:['A','B','C','D'][i%4],xyz:['X','Y','Z'][i%3],volume:['大','中','小'][i%3],planner:['张计划','李计划'][i%2],monthly:po?80+i*10:null,monthlyDate:po?reference+' 08:00:00':null,monthlySales:po?75+i*5:null,weekly:po?null:35+i,weeklyDate:po?null:reference+' 08:00:00',weeklySales:po?null:30+i,weeklyRiskSales:po?null:28+i,volatility:po?45+i:7+i*.2,purchaseDays:po?45:null,transferDays:po?null:3,cycle:po?7:null,transferCycle:po?null:7,days:i%3?5:0,start:i%3?'2026-01-01':'',end:i%3?'2030-01-01':'',rate:98,service:2.05,maxCoef:1.2,maxDays:3,minCoef:.8,minDays:-2,manualTarget:null,manualReorder:null,manualMin:null,manualMax:null,manualReason:'',updated:stamp(),history:[],calcStatus:'成功',formulaVersion:'待生产定版'};
 for(const k of Object.keys(sourcePairs))if(present(r[k]))r[sourcePairs[k]]=i%3===0||k==='transferCycle'?'全局参数':'配置表';
 if(i===2){r.manualTarget=po?350:320;r.manualReason='季节活动备货';}
 return finalize(r);
 });
}
function validateManual(row,input){
 const po=row.buildType==='PO 建储',keys=['manualTarget','manualReorder','manualMin','manualMax'];let errors=[];
 for(const k of keys)if(!present(input[k]))errors.push('四项调整值均为必填');
 for(const k of keys)if(present(input[k])&&(!Number.isFinite(Number(input[k]))||Number(input[k])<0||!/^\d+(\.\d{1,2})?$/.test(String(input[k]))))errors.push('人工调整值须为非负数，最多两位小数');
 if(!String(input.manualReason||'').trim())errors.push('人工调整原因必填');
 const r=finalize({...row,...input});
 if(r.noStockReason)errors.push('不建储记录不允许人工覆盖');
 if(r.adjustMin>r.adjustMax)errors.push('调整后最低风控线不能大于最高风控线');
 if(po&&!(r.adjustMax>=r.adjustTarget&&r.adjustTarget>r.adjustReorder&&r.adjustReorder>=r.adjustMin))errors.push('须满足：最高风控线 ≥ 目标库存 > 再订购点 ≥ 最低风控线');
 if(!po&&!(r.adjustMax>=r.adjustTarget&&r.adjustTarget>=r.adjustMin))errors.push('须满足：最高风控线 ≥ 目标库存 ≥ 最低风控线');
 if(!po&&present(r.adjustReorder)&&!(r.adjustReorder>=0&&r.adjustReorder<=r.adjustTarget))errors.push('STO人工再订购点须在0和调整后目标库存之间');
 return [...new Set(errors)];
}
function filterRows(rows,q){return rows.filter(r=>{
 for(const k of ['part','partName','wh','planner','buildVersion','noStockReason'])if(q[k]&&!String(r[k]||'').toLowerCase().includes(q[k].toLowerCase()))return false;
 if(q.abc&&r.abc!==q.abc)return false;
 if(q.dateStart&&r.useDate<q.dateStart||q.dateEnd&&r.useDate>q.dateEnd)return false;
 for(const source of Object.values(sourcePairs))if(q[source]&&r[source]!==q[source])return false;
 for(const [key,values] of Object.entries(q.columnFilters||{}))if(values&&values.length&&!values.includes(r[key]))return false;
 return true;
});}
function sortResults(rows,kind){return kind==='STO'?[...rows].sort((a,b)=>String(b.buildVersion||'').localeCompare(String(a.buildVersion||''))||String(a.useDate||'').localeCompare(String(b.useDate||''))||String(a.part||'').localeCompare(String(b.part||''))||String(a.wh||'').localeCompare(String(b.wh||''))):[...rows];}
function csv(rows,fields){return '\ufeff'+[fields.map(f=>f.label),...rows.map(r=>fields.map(f=>r[f.key]??''))].map(v=>v.map(x=>'"'+String(x).replace(/"/g,'""')+'"').join(',')).join('\r\n');}
const api={definitions,sourcePairs,period,isBreak,hasGlobal,finalize,seed,validateManual,filterRows,sortResults,csv};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
root.CsppStorageResults=api;if(!root.Vue)return;
const {ref,reactive,computed,watch}=root.Vue;
root.CsppStorageResultsComponent={setup(){
 const columnFilters=ref({});
 const kind=ref('PO'),expanded=ref(false),q=reactive({}),applied=ref({}),page=ref(1),message=ref(''),error=ref(''),modal=ref(false),mode=ref('detail'),current=ref(null),manual=reactive({}),saveErrors=ref([]);
 let initial;try{initial=JSON.parse(localStorage.getItem('cspp-storage-results-v5'));}catch{}
 const records=ref(Array.isArray(initial)&&initial.length?initial.map(r=>finalize(r)):[...seed('PO'),...seed('STO')]);
 const persist=()=>localStorage.setItem('cspp-storage-results-v5',JSON.stringify(records.value));persist();
 const fields=computed(()=>definitions[kind.value]);const allRows=computed(()=>sortResults(records.value.filter(r=>r.buildType===kind.value+' 建储'),kind.value));
 const rows=computed(()=>filterRows(allRows.value,{...applied.value,columnFilters:columnFilters.value}));
 const sourceFields=computed(()=>fields.value.filter(f=>f.type==='source'));
 const metricOptions=computed(()=>fields.value.filter(f=>sourcePairs[f.key]).map(f=>({value:f.key,label:f.label})));
 const columns=computed(()=>[...fields.value.map((f,i)=>({title:f.label,key:f.key,dataIndex:f.key,width:f.label.length>8?195:145,fixed:i===0?'left':undefined,filters:f.type==='source'?['配置表','全局参数'].map(v=>({text:v,value:v})):f.type==='flag'?(['targetBreak','reorderBreak'].includes(f.key)?['突破最高风控线','突破最低风控线','否']:['是','否']).map(v=>({text:v,value:v})):undefined,filteredValue:columnFilters.value[f.key]||null,sorter:(a,b)=>typeof a[f.key]==='number'?a[f.key]-b[f.key]:String(a[f.key]??'').localeCompare(String(b[f.key]??''),'zh-CN')})),{title:'操作',key:'action',width:120,fixed:'right'}]);
 watch(kind,()=>{reset();message.value='';error.value='';modal.value=false;});
 function search(){applied.value={...q};page.value=1;}
 function tableChange(p,filters){page.value=p.current||1;columnFilters.value=filters;}
 function reset(){columnFilters.value={};for(const k in q)delete q[k];search();}
 function open(r,edit=false){current.value=JSON.parse(JSON.stringify(r));mode.value=edit?'edit':'detail';saveErrors.value=[];for(const k in manual)delete manual[k];Object.assign(manual,{manualTarget:r.adjustTarget,manualReorder:r.adjustReorder,manualMin:r.adjustMin,manualMax:r.adjustMax,manualReason:r.manualReason});modal.value=true;}
 function save(){saveErrors.value=validateManual(current.value,manual);if(saveErrors.value.length)return;const index=records.value.findIndex(r=>r.id===current.value.id);const old=records.value[index],next=finalize({...old,...manual,updated:stamp()});next.history=[...(old.history||[]),{at:stamp(),by:'当前用户',reason:manual.manualReason,before:{target:old.adjustTarget,reorder:old.adjustReorder,min:old.adjustMin,max:old.adjustMax},after:{target:next.adjustTarget,reorder:next.adjustReorder,min:next.adjustMin,max:next.adjustMax}}];records.value.splice(index,1,next);persist();modal.value=false;message.value='人工调整已保存，原始及阶段计算值保持不变';}
 function exportData(all){const data=all?allRows.value:rows.value;const content=csv(data,fields.value);const a=document.createElement('a'),url=URL.createObjectURL(new Blob([content],{type:'text/csv;charset=utf-8'}));a.href=url;a.download=kind.value+'建储结果-'+(all?'全量':'查询')+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);message.value='已导出 '+data.length+' 条'+kind.value+'建储结果';}
 const display=v=>present(v)?v:'—';
 const valueClass=(r,k)=>isBreak(r,k)?'result-value-limit':hasGlobal(r,k)?'result-value-global':'';
 const groups=computed(()=>{if(!current.value)return[];const r=current.value;return[{title:'基础信息',keys:fields.value.slice(0,kind.value==='PO'?7:9).map(f=>f.key)},{title:'初始与风控结果',keys:['target','targetBreak','reorder','reorderBreak','min','max','riskTarget','riskReorder']},{title:'采购兜底',keys:['floor','floorApplied','floorReason','floorTarget','floorReorder','floorMin','floorMax']},{title:'不建储与最终结果',keys:['noStockReason','adjustTarget','adjustReorder','adjustMin','adjustMax','adjustReason']},{title:'预测输入与参数来源',keys:fields.value.filter(f=>['abc','xyz','volume','planner','monthly','monthlyDate','monthlySales','weekly','weeklyDate','weeklySales','weeklyRiskSales','volatility',...Object.keys(sourcePairs),...Object.values(sourcePairs),'start','end','updated'].includes(f.key)).map(f=>f.key)}].map(g=>({...g,fields:g.keys.map(k=>fields.value.find(f=>f.key===k)).filter(Boolean)})).filter(g=>g.fields.length);});
 const editFields=computed(()=>[{key:'manualTarget',label:'调整后目标库存'},{key:'manualReorder',label:'调整后再订购点'},{key:'manualMax',label:'调整后最高风控线'},{key:'manualMin',label:'调整后最低风控线'}]);
 return{kind,expanded,q,page,message,error,modal,mode,current,manual,saveErrors,fields,rows,allRows,sourceFields,metricOptions,columns,search,reset,tableChange,open,save,exportData,display,valueClass,groups,editFields,isBreak,hasGlobal,sourcePairs};
},template:`<section class="strategy-page result-page">
<div class="strategy-heading"><h2>建储水位线计算结果</h2></div>
<a-radio-group v-model:value="kind" button-style="solid" class="result-types"><a-radio-button value="PO">PO 建储</a-radio-button><a-radio-button value="STO">STO 建储</a-radio-button></a-radio-group>
<a-alert v-if="message" :message="message" type="success" closable @close="message=''" style="margin:12px 0"/>
<div class="card"><div class="result-query-grid">
<label><span>版本号</span><a-input v-model:value="q.buildVersion" placeholder="如 202643" allow-clear @pressEnter="search"/></label>
<label><span>配件号</span><a-input v-model:value="q.part" placeholder="请输入配件号" allow-clear @pressEnter="search"/></label>
<label><span>建储仓库编码</span><a-input v-model:value="q.wh" placeholder="请输入仓库编码" allow-clear @pressEnter="search"/></label>
<template v-if="expanded"><label v-for="f in sourceFields" :key="f.key"><span>{{f.label}}</span><a-select v-model:value="q[f.key]" allow-clear placeholder="全部" :options="[{value:'配置表',label:'配置表'},{value:'全局参数',label:'全局参数'}]"/></label><label><span>配件名称</span><a-input v-model:value="q.partName" allow-clear placeholder="请输入配件名称"/></label><label><span>ABC 分类</span><a-select v-model:value="q.abc" allow-clear placeholder="全部" :options="['A','B','C','D','E'].map(x=>({value:x,label:x}))"/></label><label><span>计划员</span><a-input v-model:value="q.planner" allow-clear placeholder="请输入计划员"/></label><label><span>建储日期开始</span><a-input v-model:value="q.dateStart" type="date"/></label><label><span>建储日期结束</span><a-input v-model:value="q.dateEnd" type="date"/></label><label><span>不建储原因</span><a-input v-model:value="q.noStockReason" allow-clear placeholder="请输入原因"/></label></template>
</div><div class="strategy-query-actions" style="margin-top:16px"><a-button type="primary" @click="search">查询</a-button><a-button @click="reset">重置</a-button><a-button type="link" @click="expanded=!expanded">{{expanded?'收起':'展开'}}条件</a-button></div></div>
<div class="card"><div class="strategy-toolbar"><a-button @click="exportData(false)">导出</a-button><a-button @click="exportData(true)">全量导出</a-button><span style="margin-left:auto;color:#8290a4">共 {{rows.length}} 条 · {{fields.length}} 个字段</span></div>
<a-table :key="kind" :columns="columns" :data-source="rows" row-key="id" size="middle" :scroll="{x:'max-content'}" @change="tableChange" :pagination="{current:page,pageSize:10,onChange:p=>page=p,showTotal:n=>'共 '+n+' 条'}"><template #bodyCell="{column,record}"><template v-if="column.key==='action'"><a @click="open(record)">详情</a><a v-if="!record.noStockReason" @click="open(record,true)" style="margin-left:12px">调整</a></template><a-tag v-else-if="column.key.endsWith('Source')" :color="record[column.key]==='全局参数'?'gold':'blue'">{{display(record[column.key])}}</a-tag><a-tag v-else-if="['targetBreak','reorderBreak','floorApplied'].includes(column.key)" :color="(record[column.key]==='是'||['突破最高风控线','突破最低风控线'].includes(record[column.key]))?(column.key==='floorApplied'?'green':'red'):'default'">{{display(record[column.key])}}</a-tag><span v-else :class="valueClass(record,column.key)" :title="isBreak(record,column.key)?'该值突破所属阶段的风控上下限':hasGlobal(record,column.key)?'实际取值来源：全局参数':''">{{display(record[column.key])}}</span></template></a-table></div>
<a-modal v-model:open="modal" :title="(mode==='detail'?'详情':'人工调整')+' · '+kind+' 建储结果'" :width="1000" :footer="null" :mask-closable="false"><a-alert v-if="saveErrors.length" type="error" :message="saveErrors.join('；')" show-icon style="margin-bottom:16px"/>
<template v-if="mode==='detail'"><section v-for="group in groups" :key="group.title" class="result-detail-group"><h3>{{group.title}}</h3><a-descriptions bordered :column="2" size="small"><a-descriptions-item v-for="f in group.fields" :key="f.key" :label="f.label"><a-tag v-if="f.type==='source'" :color="current[f.key]==='全局参数'?'gold':'blue'">{{display(current[f.key])}}</a-tag><span v-else :class="valueClass(current,f.key)">{{display(current[f.key])}}</span></a-descriptions-item></a-descriptions></section><section v-if="current.history?.length"><h3>人工调整记录</h3><div v-for="(h,i) in current.history" :key="i" class="strategy-history">{{h.at}} {{h.by}} · {{h.reason}}<div>目标库存：{{h.before.target}} → {{h.after.target}}；最低/最高线：{{h.before.min}} / {{h.before.max}} → {{h.after.min}} / {{h.after.max}}</div></div></section></template>
<template v-else><div class="strategy-grid"><label v-for="f in editFields" :key="f.key"><span><b style="color:#ff4d4f">* </b>{{f.label}}</span><a-input-number v-model:value="manual[f.key]" :min="0" style="width:100%"/></label></div><label class="result-reason"><span><b style="color:#ff4d4f">* </b>人工调整原因</span><a-textarea v-model:value="manual.manualReason" :rows="3" placeholder="请填写人工调整原因"/></label></template>
<div class="strategy-modal-footer"><a-button @click="modal=false">{{mode==='detail'?'关闭':'取消'}}</a-button><a-button v-if="mode==='edit'" type="primary" @click="save">保存调整</a-button></div></a-modal>
</section>`};
})(typeof window!=='undefined'?window:{});
