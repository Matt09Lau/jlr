#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用无头 Edge 渲染 HTML 并 dump DOM，按 hash 深链逐一验证各主数据页面是否正确挂载、渲染表格、含关键字段，
以及拓展属性页是否包含「导入」按钮与操作列「编辑」。
"""
import os, sys, re, time, subprocess, urllib.parse

VENDOR_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(VENDOR_DIR))
HTML = os.path.join(PROJECT_DIR, "前端设计稿", "JLR_主数据前端设计稿.html")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DUMP = os.path.join(VENDOR_DIR, "dump.txt")

# 每个待验证页面: (key, 页面标题关键字, 期望出现的业务字段关键字, 是否拓展属性页)
PAGES = [
    ("wh-abc",       "备货规则",           "备货标识",       False),
    ("mat-master",   "配件主数据",         "计划员",         False),
    ("mat-ext",      "配件扩展属性",       "导入",           True),
    ("wh-master",    "仓库主数据",         "仓库类型",       False),
    ("dealer",       "经销商主数据",       "经销商代码",     False),
    ("dealer-ext",   "经销商扩展属性",     "导入",           True),
    ("supplier",     "供应商主数据",       "供应商名称",     False),
    ("supplier-ext", "供应商扩展属性",     "导入",           True),
    ("part-supplier","配件与供应商关系",   "采购信息记录",   False),
    ("replace",      "替代链",             "替代关系",       False),
    ("fc-long",      "长周期预测报表",     "3年预测",        False),
    ("fc-buyout",    "一次买断预测结果",   "All time buy",  False),
    ("fc-regular",   "常规预测",           "2026-10",        False),
    ("fc-best",      "最佳模型",           "最优模型",       False),
    ("part-group",      "配件组管理",        "分组类型",      False),
    ("po-regular",      "采购计划",          "数据生成日期",  False),
    ("po-history",      "历史采购计划",      "数据生成日期",  False),
    ("po-export",       "采购计划导出",      "导出状态",      False),
    ("sto-week",        "调拨计划",          "计划批次",      False),
    ("sto-export",      "调拨计划导出",      "计划批次",      False),
    ("sto-summary",     "调拨计划汇总",      "数据快照日期",  False),
    ("sto-next",        "给仓库的预计调拨计划", "计划批次",   False),
    ("po-atb",          "All Time Buy 计划", "全生命周期累计需求", False),
    ("po-bridge",       "Bridge Buy 计划",   "属地预期库存",  False),
    ("po-ref",          "参考零件采购计划",  "参考车型",      False),
    ("po-roll",         "给供应商的滚动计划", "同步状态", False),
    ("activity-register", "活动登记表",      "活动名称", False),
]

def file_url(path, fragment=""):
    p = path.replace("\\", "/")
    enc = urllib.parse.quote(p, safe=":/")
    if fragment:
        enc += "#" + urllib.parse.quote(fragment, safe="")
    return "file:///" + enc.lstrip("/")

def dump(page_key, html_path=None, inject=None):
    """渲染指定页面并 dump DOM；html_path/inject 用于在临时副本中注入脚本（如自动点击触发弹窗）。
    无头 Edge 偶发在 Vue 挂载完成前返回空壳，故对未渲染（无水印 / 无 #app）的情况重试至多 3 次。"""
    path = html_path or HTML
    if inject:
        src = open(HTML, encoding="utf-8", errors="replace").read()
        # 注意：文件内联 JS 字符串中也可能出现 "</body>"，必须只替换文档末尾那一个，否则会破坏脚本
        tag = "</body>"
        idx = src.rfind(tag)
        src = src[:idx] + inject + "\n" + tag + src[idx + len(tag):]
        # 必须与正式 HTML 同目录：成品页以相对路径引用 5 个外部 js（warehouse-network 等），
        # 若写到 vendor 目录会导致 C:\...\vendor\warehouse-network.js 不存在 → window.CSPPWarehouseNetwork 未定义 → app 挂载失败
        path = os.path.join(os.path.dirname(HTML), "_tmp_probe.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
    url = file_url(path, page_key)
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--virtual-time-budget=25000", "--dump-dom", url]
    last = ""
    for attempt in range(4):
        with open(DUMP, "w", encoding="utf-8") as f:
            try:
                subprocess.run(cmd, stdout=f, stderr=subprocess.DEVNULL, timeout=120)
            except subprocess.TimeoutExpired:
                # 无头 Edge 偶发在重页面挂起：清理进程后重试，避免整套校验中断
                try:
                    subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
                except Exception:
                    pass
                time.sleep(1)
                continue
        last = open(DUMP, encoding="utf-8", errors="replace").read()
        if "Non-production system" in last and '<div id="app"' in last:
            break
    return last

def rendered(data):
    """提取真实渲染体（#app 与 app.mount 逻辑脚本之间），排除 x-template 脚本文本。"""
    s = data.find('<div id="app"')
    if s < 0:
        return ''
    m = data.find('app.mount')
    if m < 0:
        return data[s:]
    sc = data.rfind('<script', 0, m)
    return data[s:sc] if sc > s else data[s:]

def has_col(html, name):
    """按「独立文本节点/单元格」精确判断是否渲染了名为 name 的字段（列头、标签、描述项）。
    'base' 这类短词若用子串判定会被 align-items:baseline 等样式文本误命中，故统一走本函数。"""
    return re.search(r'>\s*' + re.escape(name) + r'\s*<', html or '') is not None

def bad_hit(r, k):
    """bad 列表命中判定：'base' 走精确列头匹配，其余沿用子串判定。"""
    return has_col(r, k) if k == 'base' else (k in r)

def strip_scripts(s):
    """剔除所有 <script> 块（含 x-template 模板源与内联 JS），
    仅保留 Vue 运行时真正渲染出的 DOM 文本，避免把模板/源码里的静态字符串误判为已渲染。"""
    return re.sub(r'<script\b[^>]*>.*?</script>', '', s, flags=re.S)

def check_one(page_key, title_kw, field_kw, is_ext):
    dump(page_key)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":page_key, "ok":False, "msg":"渲染失败/错误页"}
    r = rendered(data)
    rows = r.count("ant-table-row")
    watermark = r.count("Non-production system")
    title_ok = title_kw in r
    field_ok = field_kw in r
    import_ok = (r.count("导入") > 0) if is_ext else None
    edit_ok = (r.count("编辑") > 0) if is_ext else None
    ok = rows > 0 and title_ok and field_ok and watermark > 0
    if is_ext:
        ok = ok and import_ok and edit_ok
    detail = f"rows={rows} 水印={watermark} 标题={title_ok} 字段={field_ok}"
    if is_ext:
        detail += f" 导入={import_ok} 编辑={edit_ok}"
    return {"key":page_key, "ok":ok, "msg":detail}

def check_po_pages():
    """采购计划页面：正常挂载、渲染表格、包含关键业务字段。
    另做一次源码级断言：常规采购计划的「需求仓库要求到货日期」字段已按用户要求整体删除。"""
    # 源码级：该字段不应存在于 HTML 任一位置（弹窗默认不渲染，dump 级断言测不到）
    src = open(HTML, encoding="utf-8", errors="replace").read()
    field_left = [k for k in ["需求仓库要求到货日期", "wh_required_arrival_date"] if k in src]

    checks = [
        ("po-regular", "采购计划", "数据生成日期"),
    ]
    all_ok = True; details = []
    for key, title, field in checks:
        dump(key)
        data = open(DUMP, encoding="utf-8", errors="replace").read()
        if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
            all_ok = False; details.append(f"{key}=ERR"); continue
        r = rendered(data)
        rows = r.count("ant-table-row")
        title_ok = title in r; field_ok = field in r
        ok = rows > 0 and title_ok and field_ok
        if not ok: all_ok = False
        details.append(f"{key}({'Y' if ok else 'N'}:{rows})")
    if field_left:
        all_ok = False
        details.append("残留字段:" + ",".join(field_left))
    return {"key":"po-4pages","ok":all_ok,"msg":' '.join(details)}

def check_po_regular_activity():
    """采购计划-活动零件拦截弹窗：按需求第8条(历史数据处理-活动登记表)展示该配件登记的活动数量，
    供计划员参考后手动填写调整计划数量（客户调整的计划数量）。
    源码级断言：存在活动登记表主数据(poRegActivityTable)、按配件号查找(poRegActReg/poRegEditActReg)、
    展示面板标识(活动登记信息/活动数量（客户调整量）)，并展示唯一主键字段「活动名称」；
    旧版合并输入框「活动名称 / 编号 / 请输入活动名称或编号 / activity_no」已彻底移除。"""
    src = open(HTML, encoding="utf-8", errors="replace").read()
    need = ["poRegActivityTable", "poRegActReg", "poRegEditActReg", "poRegEditActReg.activity_name",
            "活动登记信息", "活动数量（客户调整量）", "活动状态", "actRegStatusColor"]
    miss = [k for k in need if k not in src]
    bad = [k for k in ["活动名称 / 编号", "请输入活动名称或编号", "activity_no", "row.activity_no",
                       "poRegEditActMonths", "活动销量按月填充（来自活动登记表"] if k in src]
    ok = (not miss) and (not bad)
    detail = f"缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"po-regular-活动零件","ok":ok,"msg":detail}

def check_po_order():
    """采购计划-创建订单弹窗（2026-11-06；2026-11-10 更名为创建计划）：
    ① 按截图去掉「交付提前期」列；该字段仅不再展示，后台仍必须带出 lead_days 用于自动计算
       要求到货日期（eta_date = 下单日期 + 提前期），否则生成的计划行到货日期会失真；
    ② 多供应商（同一配件在「配件与供应商关系」中有多条）时，供应商代码列改为可搜索下拉，
       改选后供应商名称与提前期同步切换；单供应商仍只读自动带出。
    源码级断言：弹窗与 7 列仍在、提前期计算链完整、供应商下拉与联动函数齐备、无旧单条取值残留。"""
    src = open(HTML, encoding="utf-8", errors="replace").read()
    need = ["创建计划 · 采购计划", "poOrderCols", "poOrderRows", "poOrderOnPart", "poOrderEta",
            "poOrderSubmit", "title:'计划数量'", "title:'备注'",
            "eta_date:poOrderEta(issueDate, r.lead_days)",
            "poOrderSupplierOptions", "poOrderOnSupplier", "supplier_options:[]",
            "record.supplier_options.length>1", ':options="record.supplier_options"',
            'option-label-prop="value"', ":dropdown-match-select-width=\"false\"",
            "@change=\"v=>poOrderOnSupplier(record, v)\"",
            "r.lead_days = opts.length ? opts[0].delivery_lead_time"]
    bad = ["title:'交付提前期'", "column.key==='lead_days'",
           "title:'交付提前期', key:'lead_days'",
           "const rel = code ? partSupplierData.find"]
    miss = [k for k in need if k not in src]
    stale = [k for k in bad if k in src]
    # 「订单」字样在采购订单下达（poIssueColumns 的 title:'订单数量'）等页面合法存在，
    # 因此本弹窗的列名断言只在 poOrderCols 区间内判定，禁止全局裸词。
    mcols = re.search(r"const poOrderCols = \[(.*?)\n\s*\];", src, re.S)
    if not mcols:
        miss.append("poOrderCols 区间未定位")
    else:
        seg = mcols.group(1)
        if "title:'计划数量'" not in seg:
            miss.append("poOrderCols 缺「计划数量」列")
        if "title:'订单数量'" in seg:
            stale.append("poOrderCols 残留「订单数量」列")
    ok = (not miss) and (not stale)
    detail = f"缺失={miss if miss else '无'} 残留={stale if stale else '无'}"
    return {"key":"po-regular-创建计划", "ok":ok, "msg":detail}

def check_po_create_plan():
    """采购计划「创建订单」更名「创建计划」+ 备注列联想活动名称（2026-11-10）。
    ① 入口按钮、弹窗标题、明细标题、提交按钮、空表文案、数量列名全部改称「计划」，旧称零残留；
    ② 备注列由 a-input 改为 a-auto-complete：数据源取「活动登记表」actRegData 的活动名称去重，
       既可联想选择，也不限制手工输入（无 :options 强约束、组件仅作建议）；
    ③ 保存后将所选/所输备注回写同配件计划行「备注」列，缺省兜底文案同步为「手工创建计划单独下单」。
    源码级断言：只看弹窗区间内的组件与函数，避免误伤采购订单下达等其它页面的「订单」字样。"""
    src = open(HTML, encoding="utf-8", errors="replace").read()
    need = [">创建计划</a-button>",
            "创建计划 · 采购计划",
            "计划明细（可添加多条，每行一个配件）",
            "暂无计划明细",
            '<a-auto-complete v-model:value="record.remark"',
            'placeholder="选择或输入活动名称"',
            ':options="poOrderActOptions"',
            ':filter-option="poOrderActFilter"',
            "const poOrderActOptions = computed(",
            "function poOrderActFilter(input, option){",
            "actRegData.forEach(function(x){",
            "out.push({ value:n });",
            "poOrderActOptions, poOrderActFilter, poOrderOpenModal",
            "p.remark=(r.remark && r.remark.trim()) ? r.remark.trim() : '手工创建计划单独下单';",
            "已创建 '+n+' 条计划（待审批）"]
    bad = [">创建订单</a-button>", "创建订单 · 采购计划",
           "订单明细（可添加多条，每行一个配件）", "暂无订单明细",
           'placeholder="备注（如：某某活动单独下单）"',
           "手工创建订单单独下单", "创建订单回写"]
    miss = [k for k in need if k not in src]
    stale = [k for k in bad if k in src]
    ok = (not miss) and (not stale)
    detail = f"缺失={miss if miss else '无'} 残留={stale if stale else '无'}"
    return {"key":"po-regular-创建计划/备注联想", "ok":ok, "msg":detail}

def check_po_manual_order():
    """采购计划-手工下单拦截类型（2026-11-07）：
    针对「手工创建计划」产生的行，新增拦截原因＝手工下单（无需计划员处理、编辑弹窗只读），
    备注写明单独下单原因（如某活动单独下单）；手工下单备注不附「不推荐出单」标签。
    源码级断言：枚举/只读集合/不推荐出单集合/筛选分组/编辑提示/保存只读判定/计划提交回写/演示数据齐备。"""
    src = open(HTML, encoding="utf-8", errors="replace").read()
    need = ["'直供件','手工下单']",
            "poNoActionReasons = ['非计划日','库存充足','替代拦截','一次买断件','直供件','手工下单']",
            "poNoIssueReasons = poNoActionReasons.filter(v=>v!=='手工下单')",
            "poNoActionReasons.includes(reason)",
            "无需审核（手工下单）",
            "'手工下单':'该配件已由计划员手工创建计划单独下单",
            "poManualOrderNotes",
            "p.block_reason='手工下单'",
            "p.remark=(r.remark",
            "选择或输入活动名称"]
    bad = ["poNoIssueReasons = ['非计划日','库存充足','替代拦截','一次买断件','直供件','手工下单']",
           "无需审核（不推荐出单）"]
    miss = [k for k in need if k not in src]
    stale = [k for k in bad if k in src]
    ok = (not miss) and (not stale)
    return {"key":"po-regular-手工下单", "ok":ok, "msg":f"缺失={miss if miss else '无'} 残留={stale if stale else '无'}"}

def check_po_detail_layout():
    """采购计划 / 历史采购计划详情弹窗（2026-11-07）：
    取消「调整与拦截信息 + 全量字段」双块，改为单块 a-descriptions，
    字段按列表列定义 poRegColumns / poHistColumns 的顺序依次排列。"""
    src = open(HTML, encoding="utf-8", errors="replace").read()
    need = ["v-for=\"c in poRegColumns.filter(x=>x.key!=='action')\"",
            "v-for=\"c in poHistColumns.filter(x=>x.key!=='action')\"",
            "字段与列表列定义 poRegColumns 同序",
            "字段与列表列定义 poHistColumns 同序"]
    bad = ["调整与拦截信息", "全量字段"]
    miss = [k for k in need if k not in src]
    stale = [k for k in bad if k in src]
    ok = (not miss) and (not stale)
    return {"key":"po-详情弹窗单块", "ok":ok, "msg":f"缺失={miss if miss else '无'} 残留={stale if stale else '无'}"}

def check_po_edit_modal():
    """采购计划「调整 · 采购计划」弹窗（2026-11-07）：
    ① 弹窗内不再提供「备注（人工填写，选填）」文本域，备注只由「创建订单」回写 / 系统派生；
    ② 仅当单据状态＝待提交 且 本行拦截尚未处理过 且 仍有待处理拦截原因时，才按拦截原因
       展示一次性处理内容（选供应商 / 指定计划员 / 确认合同 / 调数量 / 活动登记面板）；
    ③ 处理完成（handled 置位、拦截解除）或单据已流转出待提交后，再次打开仅保留
       「调整计划数量」「调整原因」2 个可编辑字段，不再重复要求选供应商等一次性动作，
       也不再展示「拦截已处理」状态提示条；
    ④ 再次调整保存时写回这 2 个字段并追加「数量调整」变更记录。
    源码级断言：待处理判定 / 两种形态模板 / handled 标记 / 通用保存分支齐备，旧备注输入已清除。"""
    src = open(HTML, encoding="utf-8", errors="replace").read()
    need = ["const poRegEditPending = computed(()=>{",
            "r.bill_status==='待提交' && !r.handled && r.is_blocked==='是'",
            'v-if="poRegEditPending"',
            "poRegEditPending, poRegOpenEdit",
            "Object.keys(poRegEditErr).forEach(k=>{ poRegEditErr[k]=''; });",
            "仅保留 2 个通用调整字段，且不展示任何状态提示条",
            "const isPending = poRegEditPending.value;",
            "const upd = { modifier:'当前用户', update_time:ts, handled:true }",
            "if(!isPending){",
            "upd.adjust_qty = row.adjust_qty; upd.adjust_reason = row.adjust_reason;",
            "pushLog('数量调整','调整计划数量', t.adjust_qty, row.adjust_qty, '人工', row.adjust_reason||'人工调整计划数量')",
            "const needReason = isPending ? !isReadOnly : true;"]
    bad = ["备注（人工填写，选填）", 'v-model:value="poRegEditRow.remark"',
           "const upd = { modifier:'当前用户', update_time:ts, remark: row.remark }",
           "可在下方填写备注说明", "备注由下方统一",
           "拦截已处理（或单据已流转）", "可继续调整计划数量与调整原因"]
    miss = [k for k in need if k not in src]
    stale = [k for k in bad if k in src]
    ok = (not miss) and (not stale)
    return {"key":"po-调整弹窗两形态", "ok":ok, "msg":f"缺失={miss if miss else '无'} 残留={stale if stale else '无'}"}

def check_activity_register():
    """历史需求处理-活动登记表（2026-11-06 迭代口径）：
      ① 取消按月维护活动数量（跨月分摊 / 按月填充表 / 按月销量列 / 查看结果按月汇总页签全部移除）；
      ② 导入（Excel/CSV → 预览 → 按唯一主键「活动名称 + 配件号」upsert）＋ 导出（按筛选结果导出 CSV）；
      ③ 活动截止日期选填；④ 关键字段缺失 → 活动状态「待补充信息」；
      ⑤ 新增弹窗已去掉「活动期间」说明小字、附件描述副标题、底部整段状态说明；
      ⑥ 新增「活动名称」＋配件号构成唯一主键：列表首列/筛选/表单必填/组合判重/详情/导入模板首列/导出列；
         缺主键的导入行标「跳过」且不写回；
      ⑦ 页面内字段统一称「配件号」（原「最新配件号」），按天明细同步称「配件名称」；
         配件主数据详情页的「最新配件号」＝最新可采购件，属另一业务口径，不在本桶判定范围内；
      附件图片仍与配件组管理共用通用交互（picture-card ≤5 张，全站唯一预览弹窗）。
    源码级断言：新功能标识齐备、旧按月变量已清除（草稿副本用 dar* 前缀，不参与判定）。
    说明文案的残留断言只在正本模板区间内做（本地草稿副本保留改造前原文，不能全文判）。
    渲染级断言：菜单组 / 标题 / 导入与导出按钮 / 待补充信息标签 / 表格行，且正本页不再出现按月列与分月样例。"""
    src = open(HTML, encoding="utf-8", errors="replace").read()
    a0 = src.find("<template v-else-if=\"activeMenu==='activity-register'\">")
    a1 = src.find("<!-- 参考系统同组菜单占位", a0)
    act_src = src[a0:a1] if a0 >= 0 and a1 > a0 else src
    need = [">导入</a-button>", ">导出</a-button>", "actRegExportCsv", "导出成功，共",
            "JLRS_活动登记表_", "actRegImportTemplate", "actRegImportFile", "actRegDoImport",
            "actRegFindMatch", "actRegImportHeads", "actRegImportAddCount", "actRegImportSkipCount",
            "activity_name", "活动名称", "请填写活动名称并选择配件号（唯一主键）",
            "该「活动名称 + 配件号」组合已存在", "按唯一主键「活动名称 + 配件号」匹配",
            "'活动名称','配件号','活动类型'", "主键缺失", "actRegDemoName",
            '<span class="f-label">配件号</span>', "title:'配件号', key:'part_code'",
            'label="配件号"', "title:'配件名称', key:'part_name'",
            "待补充信息", "actRegStatusOf", "actRegIsComplete",
            "结束日期（选填）",
            "最多 5 张图片", "actRegImgMax = 5", "actRegBeforeImg", "actRegRemoveImg",
            "images:(f.images||[]).slice()", "按天明细", "actRegDayCols",
            "jlrsImgBefore", "jlrsImgPreviewOpen", "jlrsImgPreview.open",
            'list-type="picture-card"', "pgImgMax = 6"]
    miss = [k for k in need if k not in src]
    stale = [k for k in ["actRegMonthSpans", "actRegAllocate", "actRegMonthCols",
                         "actRegFormMonths", "actRegDetailMonths", "actRegResultMonths",
                         "actRegResultTab", "actRegMonthText", "poRegEditActMonths",
                         'v-model:open="pgPreview.open"',
                         "actRegFindMatch(code, start)", "actRegFindMatch(part_code, start_date)",
                         "actRegFindMatch(x.part_code, x.start_date)",
                         "已导出导入模板（8 列）"] if k in src]
    stale += [k for k in ["活动截止日期可留空，后续补充", "活动方案、海报或现场照片",
                          "如有缺失，保存后活动状态自动标记为", "批量导入变更</a-button>",
                          "按「配件号 + 开始日期」匹配", "模板列：配件号、活动类型",
                          "按「配件号 + 开始日期」upsert",
                          "最新配件号", "最新配件名称"] if k in act_src]
    dump("activity-register")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"activity-register","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    checks = {
        "菜单组": "历史需求处理" in r,
        "页面标题": "活动登记表" in r,
        "活动名称列": has_col(r, "活动名称"),
        "配件号列": has_col(r, "配件号"),
        "无最新配件号": "最新配件号" not in r,
        "导入按钮": has_col(r, "导入"),
        "导出按钮": has_col(r, "导出"),
        "无旧按钮名": "批量导入变更" not in r,
        "待补充信息标签": "待补充信息" in r,
        "无按月销量列": "按月销量（优化）" not in r,
        "无分月填充样例": "2026-02：386 件" not in r,
        "表格行": r.count("ant-table-row") > 0,
    }
    bad = [k for k, v in checks.items() if not v]
    ok = (not miss) and (not bad) and (not stale)
    return {"key":"activity-register", "ok":ok,
            "msg":f"源码缺失={miss if miss else '无'} 残留={stale if stale else '无'} "
                  f"渲染失败项={bad if bad else '无'} rows={r.count('ant-table-row')}"}

def check_fc_buyout_btns():
    """一次买断预测结果：默认展示态，工具栏含「编辑」「生成All time buy计划」；「生成bridge buy计划」已移至长周期预测报表，不应残留；亦不应有「生成采购计划」「保存」（保存仅在编辑态出现）。"""
    dump("fc-buyout")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-buyout-按钮","ok":False,"msg":"渲染失败/错误页"}
    r = strip_scripts(rendered(data))
    need = ["编 辑", "生成All time buy计划", "批量圆整"]
    miss = [k for k in need if k not in r]
    bad = [k for k in ["生成采购计划", "生成bridge buy计划", "系数调整", "保 存"] if k in r]
    ok = (not miss) and (not bad)
    detail = f"缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"fc-buyout-按钮","ok":ok,"msg":detail}

def check_fc_long_btns():
    """长周期预测报表：默认展示态，工具栏含「编辑」「生成bridge buy计划」；不应有「生成采购计划」「生成All time buy计划」「保存」（保存仅在编辑态出现）。"""
    dump("fc-long")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-long-按钮","ok":False,"msg":"渲染失败/错误页"}
    r = strip_scripts(rendered(data))
    need = ["编 辑", "生成bridge buy计划"]
    miss = [k for k in need if k not in r]
    bad = [k for k in ["生成采购计划", "生成All time buy计划", "系数调整", "保 存"] if k in r]
    ok = (not miss) and (not bad)
    detail = f"缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"fc-long-按钮","ok":ok,"msg":detail}

def check_plan_hier3():
    dump("plan-hier-3")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"plan-hier-3","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    watermark = r.count("Non-production system")
    cols = r.count("p3-col")
    items = r.count("p3-item")
    kw = ["① 计划员", "② 计划组", "③ 供应商", "取自底层主数据", "批量导入", "导出", "新建组", "转移到计划员…", "转移到…", "零件"]
    miss = [k for k in kw if k not in r]
    ok = watermark > 0 and cols >= 3 and items > 0 and not miss
    detail = f"水印={watermark} 栏位={cols} 列表项={items} 缺失={miss if miss else '无'}"
    return {"key":"plan-hier-3","ok":ok,"msg":detail}

def check_svc_dash():
    dump("svc-dash")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"svc-dash","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    watermark = r.count("Non-production system")
    cards = r.count('class="svc-card-t"')
    kpi_cards = r.count('svc-kpi2-foot')                        # 每个核心指标卡底部目标行 = 4（整体 + 3 渠道）
    kpi_dots = r.count('svc-kpi2-dot')                          # 每张卡 1 个状态点 = 4（整体 + 3 渠道）
    tabs = r.count('class="svc-tab"') + r.count('svc-tab on')  # 品牌 3 个子 tab（含激活态）
    sorts = r.count('svc-sort')                                # 排行排序切换
    canvas = r.count("<canvas")
    chart_ids = ['svcTrendChart','svcWhChart','svcVehChart','svcBrandChart','svcPartChart','svcPieChart']
    missing_charts = [cid for cid in chart_ids if ('id="'+cid+'"') not in r]
    kw = ["服务水平dashboard", "核心服务水平指标", "整体", "分渠道",
          "服务水平趋势", "仓库服务水平排行", "车型服务 TOP10", "品牌服务排行", "配件服务 TOP10",
          "未满足原因分布", "JRC", "生产供应延迟", "倒序", "正序", "进口捷豹路虎", "奇瑞捷豹路虎"]
    miss = [k for k in kw if k not in r]
    ok = watermark > 0 and cards >= 6 and kpi_cards >= 4 and kpi_dots >= 4 and tabs >= 3 and sorts >= 3 and not missing_charts and not miss
    detail = f"水印={watermark} 卡片={cards} KPI卡={kpi_cards} 状态点={kpi_dots} tab={tabs} 切换={sorts} canvas={canvas} 缺图={missing_charts if missing_charts else '无'} 缺失={miss if miss else '无'}"
    return {"key":"svc-dash","ok":ok,"msg":detail}

def check_fc_new():
    """参考零件需求预测：左侧 7 步流程步骤条 + 右侧步骤1 参考车型库。"""
    dump("fc-new")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-new","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    watermark = r.count("Non-production system")
    steps = r.count("fc-step-no")
    autos = r.count('class="fc-auto"')
    rows = r.count("ant-table-row")
    kw = ["流程步骤", "步骤1: 维护参考车型库", "添加参考车型", "导入参考车型",
          "生成参考车型配件清单", "计算配件月度销量", "计算车型月保有量", "计算订购率",
          "匹配参考订购率", "参考零件需求预测", "配件清单", "配件销量", "整车保有量",
          "订购率", "删除", "上市日期", "断点日期", "车型编号", "L460", "L663", "X761", "纯电"]
    miss = [k for k in kw if k not in r]
    ok = watermark > 0 and steps >= 7 and autos >= 5 and rows > 0 and not miss
    detail = f"水印={watermark} 步骤={steps} 自动标记={autos} 表格行={rows} 缺失={miss if miss else '无'}"
    return {"key":"fc-new","ok":ok,"msg":detail}

def check_fc_new_pred():
    """原始参考零件需求预测：预测结果弹窗含匹配状态筛选、批量维护参考配件号（逐行独立下拉 + 受约束模板导入并校验）；更新预测结果按钮已移除。"""
    inject = ("<script>"
              "setTimeout(function(){"
              "var steps=[].slice.call(document.querySelectorAll('.fc-step'));"
              "if(steps[6]){steps[6].click();}"
              "}, 900);"
              "setTimeout(function(){"
              "var ps=[].slice.call(document.querySelectorAll('.link-btn')).filter(function(x){return x.textContent.trim()==='预测结果';});"
              "if(ps[0]){ps[0].click();}"
              "}, 1900);"
              "setTimeout(function(){"
              "var bb=[].slice.call(document.querySelectorAll('.ant-btn')).filter(function(x){return x.textContent.indexOf('批量维护参考配件号')>=0;});"
              "if(bb[0]){bb[0].click();}"
              "}, 2800);"
              "setTimeout(function(){"
              "var ib=[].slice.call(document.querySelectorAll('.ant-btn')).filter(function(x){return x.textContent.indexOf('导入参考配件号')>=0;});"
              "if(ib[0]){ib[0].click();}"
              "}, 3400);"
              "</script>")
    dump("fc-new", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-new-pred","ok":False,"msg":"渲染失败/错误页"}
    full = data
    r = rendered(data)
    has_filter = "匹配状态" in full
    has_update = "更新预测结果" in r
    has_batch = "批量维护参考配件号" in full
    has_tpl = "下载模板" in full
    has_import = "导入参考配件号" in full
    has_valid_col = "校验状态" in full
    has_note = "参考车型配件清单" in full
    has_invalid = "不在清单" in full
    has_import_msg = "已导入" in full
    has_jlr = ("LR062541" in full) and ("前制动摩擦片" in full)
    # base 为预测结果弹窗内的合法展示列（字段来源口径）；此处只校验查询条件不含 base/配件名称，
    # 该点由 check_fc_adjust 的 fcPredM.base / fcPredM.name 源级断言覆盖，故不再要求渲染文本无 base 列。
    has_base = has_col(full, 'base')
    no_lr = "左右标识" not in full
    no_upc = "UPC/FN号" not in full
    ok = (has_filter and not has_update and has_batch and has_tpl and has_import
          and has_valid_col and has_note and has_invalid and has_import_msg and has_jlr
          and no_lr and no_upc)
    detail = (f"匹配状态={has_filter} 更新按钮已移除={not has_update} 批量按钮={has_batch} 下载模板={has_tpl} "
              f"导入按钮={has_import} 校验列={has_valid_col} 说明={has_note} 越界标红={has_invalid} "
              f"导入提示={has_import_msg} JLR料号={has_jlr} "
              f"base列={has_base}(合法) 无左右标识={no_lr} 无UPC/FN={no_upc}")
    return {"key":"fc-new-pred","ok":ok,"msg":detail}

def check_fc_new_6m():
    """参考零件需求预测：计划生产量应为未来 1~12 个月（列表列），预测结果应为 1~12 个月预测列。"""
    # 探针：进入步骤7 → 统计列表里「未来N个月计划生产量」表头；再打开「预测结果」弹窗统计「N个月预测」列
    inject = ("<script>"
              "var zprod=0, zmax=0, zfc=0;"
              "setTimeout(function(){var st=[].slice.call(document.querySelectorAll('.fc-step'));if(st[6]){st[6].click();}}, 900);"
              "setTimeout(function(){"
              "[].slice.call(document.querySelectorAll('.ant-table-thead th')).forEach(function(h){"
              "var m=h.textContent.match(/未来(\\d+)个月计划生产量/); if(m){zprod++; zmax=Math.max(zmax, parseInt(m[1]));}});"
              "var ps=[].slice.call(document.querySelectorAll('.link-btn')).filter(function(x){return x.textContent.trim()==='预测结果';});"
              "if(ps[0]){ps[0].click();}"
              "}, 1900);"
              "setTimeout(function(){"
              "zfc=[].slice.call(document.querySelectorAll('.ant-modal-content .ant-table-thead th'))"
              ".filter(function(h){return h.textContent.indexOf('个月预测')>=0;}).length;"
              "var d=document.createElement('div'); d.id='zzprobe6m';"
              "d.textContent='ZZPROBE6M prod='+zprod+' max='+zmax+' fc='+zfc; document.body.appendChild(d);"
              "}, 3300);"
              "</script>")
    dump("fc-new", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key": "fc-new-12个月", "ok": False, "msg": "渲染失败/错误页"}
    m = re.search(r"ZZPROBE6M prod=(\d+) max=(\d+) fc=(\d+)", data)
    if not m:
        return {"key": "fc-new-12个月", "ok": False, "msg": "未取得探针"}
    prod, mx, fc = int(m.group(1)), int(m.group(2)), int(m.group(3))
    ok = prod == 12 and mx == 12 and fc == 12
    detail = f"计划生产量列={prod}(最大{mx}月) 预测结果列={fc}"
    return {"key": "fc-new-12个月", "ok": ok, "msg": detail}

def check_fc_new_coef():
    """参考零件需求预测：页面步骤7「系数调整」按钮 → 弹窗内维护 1~12 月系数。"""
    # 探针：进入步骤7 → 点击「系数调整」按钮后，统计弹窗内真实渲染的月份系数输入框
    inject = ("<script>"
              "setTimeout(function(){var steps=[].slice.call(document.querySelectorAll('.fc-step'));if(steps[6]){steps[6].click();}}, 900);"
              "setTimeout(function(){"
              "var bs=[].slice.call(document.querySelectorAll('.ant-btn')).filter(function(x){return x.textContent.indexOf('系数调整')>=0;});"
              "if(bs[0]){bs[0].click();}"
              "setTimeout(function(){"
              "var n=0,txt=0;"
              "[].slice.call(document.querySelectorAll('.ant-modal-content')).forEach(function(c){"
              "if(c.textContent.indexOf('预测系数调整（第 1 ~ 12 月）')>=0){txt++; n+=c.querySelectorAll('.ant-input-number').length;}});"
              "var d=document.createElement('div'); d.id='zzprobe'; d.textContent='ZZPROBE btn='+bs.length+' modalWithTxt='+txt+' inputs='+n; document.body.appendChild(d);"
              "}, 800);"
              "}, 1900);</script>")
    dump("fc-new-draft", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-new-系数","ok":False,"msg":"渲染失败/错误页"}
    # 系数调整弹窗入口仅草稿页(fc-new-draft)提供；git 成品无草稿页时跳过该校验
    if "流程步骤" not in rendered(data):
        return {"key":"fc-new-系数","ok":True,"msg":"草稿页不可用-跳过"}
    m = re.search(r"ZZPROBE btn=(\d+) modalWithTxt=(\d+) inputs=(\d+)", data)
    if not m:
        return {"key":"fc-new-系数","ok":False,"msg":"未取得弹窗探针"}
    btn, mw, inp = int(m.group(1)), int(m.group(2)), int(m.group(3))
    ok = btn >= 1 and mw >= 1 and inp >= 12
    detail = f"页面按钮={btn} 弹窗命中={mw} 弹窗内月份系数输入={inp}"
    return {"key":"fc-new-系数","ok":ok,"msg":detail}

def check_fc_adjust():
    """fc 三项调整：fc-new 去 ABC分类/弹窗查询条件（配件名称、base）；常规预测改月粒度未来12个月；最佳模型用实际模型池。"""
    src = open(HTML, encoding='utf-8', errors='replace').read()
    src_checks = {
        "无fcRegularWeeks": "fcRegularWeeks" not in src,
        "有fcRegMonths(2026-10起)": "const fcRegMonths = ['2026-10'" in src,
        "月列至2027-09": "2027-09" in src,
        "无SARIMA": "SARIMA" not in src,
        "无岭回归": "岭回归" not in src,
        "无旧朴素法": "季节性朴素法" not in src and "一次指数平滑" not in src,
        "有ES": "ES（指数平滑）" in src,
        "有holt-winters": "holt-winters" in src,
        "有WMA": "['ES（指数平滑）','holt-winters','WMA'" in src,
        "有STL": "STL（时序分解）" in src,
        "有Prophet": "Prophet" in src,
        "有ARIMA": "['ARIMA','Transformer','RNN']" in src,
        "回归仅XGBoost": "const fcRegModels = ['XGBoost']" in src,
        "有协变量说明": "协变量" in src,
        "周期性模型列名": "title:'周期性模型'" in src and "title:'非周期性模型'" in src,
        "fc-new无ABC列(宽90模式)": src.count("{ title:'ABC分类', dataIndex:'abc', key:'abc', width:90 }") == 0,
        "fcPartsM无name/base": "fcPartsM.name" not in src and "fcPartsM.base" not in src,
        "fcPredM无name/base": "fcPredM.name" not in src and "fcPredM.base" not in src,
    }
    out = []
    for k, v in src_checks.items():
        out.append(("源:" + k, v, k))
    # 渲染级：fc-best 出现新模型池与协变量说明；fc-regular 出现月列头
    dump("fc-best")
    d = open(DUMP, encoding='utf-8', errors='replace').read()
    ok_best = ("Prophet" in d) and ("XGBoost" in d) and ("周期性模型" in d) and ("协变量" in d)
    out.append(("渲染:fc-best", ok_best, f"模型池/协变量说明={ok_best}"))
    dump("fc-regular")
    d = open(DUMP, encoding='utf-8', errors='replace').read()
    ok_reg = ("2026-10" in d) and ("2027-09" in d) and ("2024-12-30" not in d)
    out.append(("渲染:fc-regular", ok_reg, f"月列头2026-10~2027-09={ok_reg}"))
    ok = all(o[1] for o in out)
    return {"key": "fc-adjust", "ok": ok,
            "msg": "全部满足" if ok else " | ".join(f"{k}✗" for k, v, _ in out if not v)}


def check_fc_fields():
    """需求预测列表/查询字段已对齐基础数据表（配件主数据 S-F-3）：base、交付计划员 呈现；
    采购类别、是否专用件、左右标识、UPC/FN号 均已去除。"""
    out = []
    for key in ['fc-long', 'fc-regular']:
        dump(key)
        d = open(DUMP, encoding='utf-8', errors='replace').read()
        if "ERR_FILE_NOT_FOUND" in d or "<title>file://" in d:
            out.append((key, False, "渲染失败/错误页")); continue
        has_base = has_col(d, 'base')
        has_dpl = "交付计划员" in d
        no_spec = "专用件" not in d       # 注：「采购类别」不能用渲染文本判定——单文件内嵌了基础数据抽屉模板，始终含该词
        no_lr = "左右标识" not in d
        no_upc = "UPC/FN号" not in d
        ok = has_base and has_dpl and no_spec and no_lr and no_upc
        out.append((key, ok, f"base={has_base} 交付计划员={has_dpl} "
                              f"无专用件={no_spec} 无左右标识={no_lr} 无UPC/FN={no_upc}"))
    # 源码级：fc 页面的 采购类别(ptype)/是否专用件 已彻底移除
    src = open(HTML, encoding='utf-8', errors='replace').read()
    src_ok = ("是否专用件" not in src) and ("fcPurchaseTypes" not in src) and ("ptype" not in src) \
             and (src.count("采购类别") == 1)   # 仅保留基础数据详情抽屉中的 1 处（来自配件主数据 purchase_type）
    out.append(("源", src_ok, f"无是否专用件/无fcPurchaseTypes/无ptype/采购类别仅剩基础数据1处={src_ok}"))
    ok = all(o[1] for o in out)
    return {"key": "fc-fields", "ok": ok, "msg": " | ".join(f"{k} {m}" for k, _, m in out)}


def check_fc_regular_trend():
    """常规预测：列表已去掉「预测趋势图」缩略图列；点击「配件号」直接打开趋势图弹窗（过去12月实际 + 未来12月预测）。"""
    inject = ("<script>setTimeout(function(){"
              "var a=document.querySelector('.ant-table-tbody td a');"
              "if(a){ a.dispatchEvent(new MouseEvent('click',{bubbles:true})); }"
              "}, 2500);</script>")
    dump("fc-regular", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-regular-trend","ok":False,"msg":"渲染失败/错误页"}
    full = data
    r = rendered(data)
    sparks = r.count('fc-spark')          # 缩略趋势图应已彻底移除
    modal = 'id="fcTrendChart"' in full
    canvas = full.count("<canvas")
    kw = ["历史实际销量", "预测销量", "预测起点", "2026-09", "2027-08",
          "过去 12 月实际销量", "未来 12 月预测销量"]
    miss = [k for k in kw if k not in full]
    ok = sparks == 0 and modal and canvas > 0 and not miss
    detail = f"缩略图残留={sparks} 弹窗={modal} canvas={canvas} 缺失={miss if miss else '无'}"
    return {"key":"fc-regular-trend","ok":ok,"msg":detail}

BT_MAIN_KW = ["预测模拟", "创建任务", "任务编号", "任务名称", "回测区间",
              "预测维度", "预测粒度", "配件数", "创建人", "搜 索", "重 置", "⬇ 导出"]
    # 注：AntD 对两个汉字的按钮文案会自动插入空格，故写作「搜 索」「重 置」

def check_fc_regular_edit():
    """常规预测：默认展示态（无行内输入、工具栏含「编辑」无「保存」）；点击「编辑」进入编辑态——12 个月预测列行内可编辑 + 「保存」 + 每行「调整原因」必填列。"""
    dump("fc-regular")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-regular-手工调整","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    kw = ["数据日期", "配件号", "调整原因", "编 辑", "2026-10", "2027-09"]
    miss = [k for k in kw if k not in r]
    # 列表内缩略趋势图列已移除；展示态不应出现行内输入与「保存」
    bad = [k for k in ["fc-spark", "预测趋势图", "保 存"] if k in r]
    inputs0 = r.count("ant-input-number")
    rows = r.count("ant-table-row")
    default_ok = rows > 0 and inputs0 == 0 and not miss and not bad
    # 编辑态探针：点击「编辑」后应出现「保存」与行内数字输入框
    inject = ("<script>setTimeout(function(){"
              "var btns=Array.prototype.slice.call(document.querySelectorAll('button'));"
              "var e=btns.find(function(b){var t=(b.textContent||'').replace(/\\s/g,'');return t.indexOf('编辑')>=0;});"
              "if(e){e.dispatchEvent(new MouseEvent('click',{bubbles:true}));}}, 1600);</script>")
    dump("fc-regular", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    r2 = rendered(data)
    inputs = r2.count("ant-input-number")
    has_save = "保 存" in r2
    ok = default_ok and inputs > 0 and has_save
    detail = f"表格行={rows} 展示态输入={inputs0} 编辑态输入={inputs} 保存={has_save} 缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"fc-regular-手工调整","ok":ok,"msg":detail}


def check_fc_regular_model_switch():
    """常规预测 · 预测结果弹窗：切换 / 点击模型后，图表必须重新渲染成功（回归：echarts 复用 DOM 导致曲线全部消失）。"""
    inject = ("<script>setTimeout(function(){"
              "var links=[].slice.call(document.querySelectorAll('.ant-table-tbody a'));"
              "var t=links.find(function(a){return (a.textContent||'').indexOf('查看预测结果')>=0;});"
              "if(t){t.dispatchEvent(new MouseEvent('click',{bubbles:true}));}"
              "setTimeout(function(){"
              "try{"
              "var el=document.getElementById('app');"
              "var st=(el&&el._vnode&&el._vnode.component)?el._vnode.component.setupState:null;"
              "if(!st||!st.fcRegMdl){var d=document.createElement('div');d.id='swprobe';d.setAttribute('data-report','NO_STATE');document.body.appendChild(d);return;}"
              "st.fcRegMdl.dlModel = st.fcRegMdl.rec.dlModels[2].name;"
              "st.fcRegMdl.trModel = st.fcRegMdl.rec.trModels[4].name;"
              "st.refreshRegMdlCharts();"
              "setTimeout(function(){"
              "try{"
              "var c1=echarts.getInstanceByDom(document.getElementById('fcRegMdlDl'));"
              "var c2=echarts.getInstanceByDom(document.getElementById('fcRegMdlTr'));"
              "var s1=c1?c1.getOption().series.length:0;"
              "var s2=c2?c2.getOption().series.length:0;"
              "var cv=document.querySelectorAll('#fcRegMdlDl canvas').length+document.querySelectorAll('#fcRegMdlTr canvas').length;"
              "var rep='seriesDL='+s1+' seriesTR='+s2+' canvas='+cv+' model='+st.fcRegMdl.dlModel;"
              "var d=document.createElement('div');d.id='swprobe';d.setAttribute('data-report',rep);document.body.appendChild(d);"
              "}catch(e){var d2=document.createElement('div');d2.id='swprobe';d2.setAttribute('data-report','ERR1 '+e.message);document.body.appendChild(d2);}"
              "}, 1500);}catch(e){}}"
              ", 2200);}, 2600);</script>")
    dump("fc-regular", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key": "fc-regular-模型切换", "ok": False, "msg": "渲染失败/错误页"}
    m = re.search(r'data-report="([^"]*)"', data)
    if not m:
        return {"key": "fc-regular-模型切换", "ok": False, "msg": "未取得探针"}
    rep = m.group(1)
    ok = ("seriesDL=12" in rep) and ("seriesTR=12" in rep) and ("canvas=2" in rep)
    return {"key": "fc-regular-模型切换", "ok": ok, "msg": rep}


def check_fc_regular_model():
    """常规预测：列表含「模型策略」列与「查看预测结果」操作列；点击后弹窗展示 Dealer/Trader 双面板、各 11 模型预测曲线（legend 含模型名 + canvas）。"""
    inject = ("<script>setTimeout(function(){"
              "var links=[].slice.call(document.querySelectorAll('.ant-table-tbody a'));"
              "var t=links.find(function(a){return (a.textContent||'').indexOf('查看预测结果')>=0;});"
              "if(t){ t.dispatchEvent(new MouseEvent('click',{bubbles:true})); }"
              "}, 2500);</script>")
    dump("fc-regular", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-regular-model","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    has_cols = ("最佳模型" in r) and ("查看预测结果" in r)
    modal = ("Dealer 类型" in data) and ("Trader 类型" in data)
    # 弹窗改版：说明文案已删除；「有效期」为必填项（红星标识）；需有「调整原因」必填输入与「单次生效」有效期选项；双面板固定展示各自最佳模型；图表含历史实际销量曲线
    bad = [k for k in ["每个类型均展示全量", "Dealer / Trader 统一设置"] if k in data]
    need = ["调整原因", "应用预测结果时必填", "单次生效", "设定截止日期", "历史实际销量", "有效期", "当前最佳模型"]
    miss_ui = [k for k in need if k not in data]
    models = ["ES（指数平滑）","Holt-Winters","Prophet","ARIMA","Transformer","集成模型（Stacking）"]
    miss = [m for m in models if m not in data]
    canvas = data.count("<canvas")
    ok = has_cols and modal and canvas > 0 and not miss and not bad and not miss_ui
    detail = f"列={has_cols} 双面板弹窗={modal} canvas={canvas} 缺失模型={miss if miss else '无'} 缺失UI={miss_ui if miss_ui else '无'} 残留文案={bad if bad else '无'}"
    return {"key":"fc-regular-model","ok":ok,"msg":detail}

def check_fc_wh_regular():
    """仓库级常规预测（调拨业务）：配件+仓库维度、预测长度 12 周、功能与常规预测对齐（行内编辑 + 保存 + 调整原因）。"""
    dump("fc-wh-regular")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-wh-regular","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    # 12 周列头为每周起始日（MM-DD）：首周 10-12、末周 12-28
    kw = ["数据日期", "配件号", "仓库编码", "仓库名称", "调整原因", "保 存",
          "10-12", "12-28", "计划员", "ABC分类"]
    miss = [k for k in kw if k not in r]
    if not has_col(r, 'base'):
        miss.append('base')
    # 不应再出现按月粒度的自然月列头，也不应残留缩略趋势图列
    bad = [k for k in ["2026-10", "2027-03", "fc-spark", "预测趋势图"] if k in r]
    inputs = r.count("ant-input-number")
    rows = r.count("ant-table-row")
    ok = rows > 0 and inputs > 0 and not miss and not bad
    detail = f"表格行={rows} 可编辑输入={inputs} 缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"fc-wh-regular","ok":ok,"msg":detail}

def check_fc_long_trend():
    """长周期预测：预测趋势图（过去 10 年实际销量 + 未来 10 年预测值），点击「配件号」打开弹窗。"""
    inject = ("<script>setTimeout(function(){"
              "var a=document.querySelector('.ant-table-tbody td a');"
              "if(a){a.dispatchEvent(new MouseEvent('click',{bubbles:true}));}}, 1600);</script>")
    dump("fc-long", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-long-趋势图","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    clean = strip_scripts(data)
    modal = 'id="fcTrendChart"' in clean
    canvas = clean.count("<canvas")
    list_kw = ["1年预测", "配件号"]
    miss_list = [k for k in list_kw if k not in r]
    bad_list = [k for k in ["fc-spark", "预测趋势图"] if k in r]
    # 弹窗图例：过去 10 年 / 未来 10 年（年粒度）
    drill_kw = ["过去 10 年实际销量", "未来 10 年预测销量", "2026 为历史 / 预测分界"]
    miss_drill = [k for k in drill_kw if k not in clean]
    ok = modal and canvas > 0 and not miss_list and not bad_list and not miss_drill
    detail = (f"列表缺失={miss_list if miss_list else '无'} 列表残留={bad_list if bad_list else '无'} "
              f"弹窗={modal} canvas={canvas} 趋势图缺失={miss_drill if miss_drill else '无'}")
    return {"key":"fc-long-趋势图","ok":ok,"msg":detail}


def check_fc_long_round():
    """长周期预测报表：数值策略（圆整）能力保留——「汇总值」列 + 「批量圆整」按钮；页头圆整规则说明文案已按需求移除。"""
    dump("fc-long")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key": "fc-long-圆整策略", "ok": False, "msg": "渲染失败/错误页"}
    r = rendered(data)
    # 圆整按规则默认生效：保留汇总值列与批量圆整按钮；页头数值策略圆整规则说明（红框提示）已移除
    need = ["汇总值", "批量圆整", "编 辑"]
    miss = [k for k in need if k not in r]
    bad = [k for k in ["圆整视角", "关闭圆整视图"] if k in r]
    rows = r.count("ant-table-row")
    ok = rows > 0 and not miss and not bad
    detail = f"表格行={rows} 缺失={miss if miss else '无'} 残留开关={bad if bad else '无'}"
    return {"key": "fc-long-圆整策略", "ok": ok, "msg": detail}


def check_fc_long_import():
    """长周期批量圆整弹窗：范围固定为当前勾选行，「已勾选行 / 导入配件号」范围选择与导入框已下线；保留策略名称/策略说明/截至日期。"""
    inject = ("<script>setTimeout(function(){"
              "var cb=document.querySelector('.ant-table-tbody .ant-checkbox-input');"
              "if(cb){cb.dispatchEvent(new MouseEvent('click',{bubbles:true}));}"
              "setTimeout(function(){"
              "var btns=[].slice.call(document.querySelectorAll('button'));"
              "var b=btns.find(function(x){var t=(x.textContent||'').replace(/\\s/g,'');return t.indexOf('批量圆整')>=0;});"
              "if(b){b.dispatchEvent(new MouseEvent('click',{bubbles:true}));}"
              "}, 1200);}, 1800);</script>")
    dump("fc-long", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key": "fc-long-批量圆整", "ok": False, "msg": "渲染失败/错误页"}
    need = ["策略名称", "稀疏件圆整策略", "截至日期", "本次共选中"]
    not_want = ["选中的零件号", "导入配件号", "已勾选行"]
    miss = [k for k in need if k not in data]
    bad = [k for k in not_want if k in data]
    ok = not miss and not bad
    detail = f"缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key": "fc-long-批量圆整", "ok": ok, "msg": detail}


def check_po_atb_bridge_integer():
    """All Time Buy / Bridge Buy 计划生成弹窗：计划数量须为整数，生成前须校验来源预测结果（全部配件 10 年）均已圆整。
    源码级断言：两生成函数改为校验全量来源数据（fcBuyoutData / fcLongData），新增全圆整计算属性并用于弹窗警告横幅与生成按钮禁用，
    弹窗提示文案说明整数要求；旧的「仅校验选中行」口径必须已移除。"""
    src = open(HTML, encoding="utf-8", errors="replace").read()
    need = [
        "fcAllTimeAllRounded = computed(()=> fcGenRoundedBad(fcBuyoutData, fcLongKeys).length === 0)",
        "fcBridgeAllRounded = computed(()=> fcGenRoundedBad(fcLongData, fcLongKeys).length === 0)",
        "const bad = fcGenRoundedBad(fcBuyoutData, fcLongKeys);",
        "const bad = fcGenRoundedBad(fcLongData, fcLongKeys);",
        "v-if=\"!fcAllTimeAllRounded\"",
        "v-if=\"!fcBridgeAllRounded\"",
        ":disabled=\"!fcBatchSelIds.length || !fcAllTimeAllRounded\"",
        ":disabled=\"!fcLongSel.length || !fcBridgeAllRounded\"",
        "计划数量须为整数，生成前系统将校验「一次买断预测结果」全部配件（10 年）均已圆整",
        "计划数量须为整数，生成前系统将校验「长周期预测报表」全部配件（10 年）均已圆整",
        "一次买断预测结果仍存在未圆整（含小数）的年份，请先对全部配件执行「圆整」处理后再生成 All Time Buy 计划",
        "长周期预测报表仍存在未圆整（含小数）的年份，请先对全部配件执行「圆整」处理后再生成 bridge buy 计划",
    ]
    stale = [
        "const bad = fcGenRoundedBad(fcAllTimeSelRowsRaw.value, fcLongKeys);",
        "const bad = fcGenRoundedBad(fcBridgeSelRowsRaw.value, fcLongKeys);",
        "所选配件存在未圆整（含小数）的年份，请先对选中的配件执行「圆整」处理后再生成 All Time Buy 计划",
        "所选配件存在未圆整（含小数）的年份，请先对选中的配件执行「圆整」处理后再生成 bridge buy 计划",
    ]
    miss = [k for k in need if k not in src]
    bad = [k for k in stale if k in src]
    ok = (not miss) and (not bad)
    detail = f"缺失={miss if miss else '无'} 残留旧口径={bad if bad else '无'}"
    return {"key": "po-atb-bridge-整数校验", "ok": ok, "msg": detail}


def check_fc_long_editmode():
    """长周期预测报表：默认展示态（仅「编辑」按钮、预测值只读）；点击「编辑」进入编辑态后，工具栏出现「保存」、预测值出现数字输入框（ant-input-number）。"""
    inject = ("<script>setTimeout(function(){"
              "var btns=Array.prototype.slice.call(document.querySelectorAll('button'));"
              "var e=btns.find(function(b){var t=(b.textContent||'').replace(/\\s/g,'');return t.indexOf('编辑')>=0;});"
              "if(e){e.dispatchEvent(new MouseEvent('click',{bubbles:true}));}}, 1600);</script>")
    dump("fc-long", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-long-编辑态","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    has_save = "保 存" in r
    inputs = r.count("ant-input-number")
    ok = has_save and inputs > 0
    detail = f"保存按钮={has_save} 数字输入框={inputs}"
    return {"key":"fc-long-编辑态","ok":ok,"msg":detail}

def check_fc_adjust_reason():
    """预测结果调整：每个可调整的结果页 / 弹窗均有「调整原因」列，且保存时按行校验必填。"""
    src = open(HTML, encoding="utf-8", errors="replace").read()
    src_ok = {
        "有调整原因列定义": "const fcReasonCol" in src,
        "fc-new预测结果含调整原因": "调整原因" in src and "adj_reason" in src,
        "保存统一校验函数": "function fcCheckReason" in src,
        "列表保存走校验": "if(!fcCheckReason(rows, r=> r.part_code)) return;" in src,
        "新车预测保存走校验": "if(!fcCheckReason(rows, r=> r.code)) return;" in src,
        "必填标识": "调整原因 *" in src,
    }
    bad_src = [k for k, v in src_ok.items() if not v]
    miss = []
    for key in ["fc-long", "fc-buyout", "fc-regular", "fc-wh-regular"]:
        dump(key)
        data = open(DUMP, encoding="utf-8", errors="replace").read()
        r = rendered(data)
        if "调整原因" not in r:
            miss.append(key)
    ok = (not bad_src) and (not miss)
    detail = f"源码校验={bad_src if bad_src else '全通过'} 缺列页面={miss if miss else '无'}"
    return {"key":"fc-调整原因","ok":ok,"msg":detail}

def check_fc_new_pred_reason():
    """参考零件需求预测 · 预测结果弹窗：含「调整原因」列（每行、调整后必填）。"""
    inject = ("<script>setTimeout(function(){"
              "var steps=[].slice.call(document.querySelectorAll('.fc-step'));if(steps[6]){steps[6].click();}}, 900);"
              "setTimeout(function(){"
              "var ls=[].slice.call(document.querySelectorAll('.link-btn')).filter(function(x){return x.textContent.trim()==='预测结果';});"
              "if(ls[0]){ls[0].click();}"
              "setTimeout(function(){"
              "var m=null;[].slice.call(document.querySelectorAll('.ant-modal-content')).forEach(function(c){"
              "if(c.textContent.indexOf('匹配状态')>=0){m=c;}});"
              "var rep=m?('modal=Y reason='+(m.textContent.indexOf('调整原因')>=0)+' inputs='+m.querySelectorAll('.ant-input').length):'modal=N';"
              "var d=document.createElement('div'); d.id='reasonprobe'; d.setAttribute('data-report',rep); document.body.appendChild(d);"
              "}, 1200);}, 1900);</script>")
    dump("fc-new", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-new-调整原因","ok":False,"msg":"渲染失败/错误页"}
    m = re.search(r'data-report="([^"]*)"', data)
    if not m:
        return {"key":"fc-new-调整原因","ok":False,"msg":"未取得弹窗探针"}
    rep = m.group(1)
    ok = ("modal=Y" in rep) and ("reason=true" in rep)
    return {"key":"fc-new-调整原因","ok":ok,"msg":rep}

def check_fc_trend_adj():
    """人工调整后趋势图叠加「人工调整预测结果」曲线：点「编辑」进编辑态 → 改一行预测值 → 点配件号 → 弹窗出现绿线图例与提示。"""
    inject = ("<script>setTimeout(function(){"
              "var btns=[].slice.call(document.querySelectorAll('button'));"
              "var eb=btns.find(function(b){var t=(b.textContent||'').replace(/\\s/g,'');return t.indexOf('编辑')>=0;});"
              "if(eb){eb.dispatchEvent(new MouseEvent('click',{bubbles:true}));}"
              "}, 1500);"
              "setTimeout(function(){"
              "var inp=document.querySelector('.ant-table-tbody .ant-input-number-input');"
              "if(inp){"
              "var setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
              "setter.call(inp,'8888');"
              "inp.dispatchEvent(new Event('input',{bubbles:true}));"
              "inp.dispatchEvent(new Event('change',{bubbles:true}));"
              "inp.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',keyCode:13,bubbles:true}));"
              "try{inp.blur();}catch(e){}"
              "}"
              "setTimeout(function(){"
              "var a=document.querySelector('.ant-table-tbody td a');"
              "if(a){a.dispatchEvent(new MouseEvent('click',{bubbles:true}));}"
              "setTimeout(function(){"
              "var mc=null;[].slice.call(document.querySelectorAll('.ant-modal-content')).forEach(function(c){"
              "if(c.textContent.indexOf('为历史 / 预测分界')>=0){mc=c;}});"
              "var rep=mc?('modal=Y legend='+(mc.textContent.indexOf('人工调整预测结果')>=0)"
              "+' hint='+(mc.textContent.indexOf('存在人工调整')>=0)):'modal=N';"
              "var d=document.createElement('div'); d.id='adjprobe'; d.setAttribute('data-report',rep); document.body.appendChild(d);"
              "}, 1500);}, 900);}, 2600);</script>")
    dump("fc-regular", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-趋势图-人工调整曲线","ok":False,"msg":"渲染失败/错误页"}
    m = re.search(r'data-report="([^"]*)"', data)
    if not m:
        return {"key":"fc-趋势图-人工调整曲线","ok":False,"msg":"未取得弹窗探针"}
    rep = m.group(1)
    ok = ("modal=Y" in rep) and ("legend=true" in rep) and ("hint=true" in rep)
    return {"key":"fc-趋势图-人工调整曲线","ok":ok,"msg":rep}

def check_fc_backtest_range():
    """预测模拟 · 回测区间：手动输入开始 / 结束日期，系统自动计算期数；不能完整切割时自动缩短结束日期并提示。"""
    # 先做静态检查：表单含开始 / 结束日期与自动计算口径；再探针验证缩短逻辑
    inject = ("<script>setTimeout(function(){"
              "function mark(rep){var d=document.getElementById('rangeprobe');"
              "if(!d){d=document.createElement('div');d.id='rangeprobe';document.body.appendChild(d);}"
              "d.setAttribute('data-report',rep);}"
              "try{"
              "var bs=[].slice.call(document.querySelectorAll('.ant-btn')).filter(function(x){return x.textContent.indexOf('创建任务')>=0;});"
              "var btn=bs.length;"
              "if(bs[0]){bs[0].click();}"
              "setTimeout(function(){"
              "try{"
              "var el=document.getElementById('app');"
              "var inst=(el._vnode&&el._vnode.component)?el._vnode.component:null;"
              "var st=inst?inst.setupState:null;"
              "if(!st||!st.btCfg){mark('NO_STATE btn='+btn);return;}"
              "var len0=st.btRangeCalc.len;"
              "st.btCfg.rangeEnd='2026-09-15';"
              "st.btOnRangeChange();"
              "setTimeout(function(){"
              "var txt=document.body.textContent;"
              "var rep='btn='+btn+' len0='+len0+' len='+st.btRangeCalc.len+' end='+st.btCfg.rangeEnd"
              "+' hint='+(txt.indexOf('系统已自动将回测区间缩短为')>=0)"
              "+' auto='+(txt.indexOf('系统按起止日期自动计算')>=0)"
              "+' starts='+(txt.indexOf('开始日期')>=0)+' ends='+(txt.indexOf('结束日期')>=0);"
              "mark(rep);"
              "}, 900);"
              "}catch(e){mark('ERR1 '+e.message);}"
              "}, 1500);"
              "}catch(e){mark('ERR0 '+e.message);}"
              "}, 1600);</script>")
    dump("fc-backtest", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-backtest-回测区间","ok":False,"msg":"渲染失败/错误页"}
    m = re.search(r'data-report="([^"]*)"', data)
    if not m:
        return {"key":"fc-backtest-回测区间","ok":False,"msg":"未取得探针"}
    rep = m.group(1)
    ok = ("len0=24" in rep and "len=23" in rep and "end=2026-08-31" in rep
          and "hint=true" in rep and "auto=true" in rep)
    return {"key":"fc-backtest-回测区间","ok":ok,"msg":rep}

def check_fc_backtest():
    """预测回测配置 · 主界面：查询条件 + 创建任务按钮 + 任务列表表格。"""
    dump("fc-backtest")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-backtest","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    watermark = r.count("Non-production system")
    rows = r.count("ant-table-row")
    miss = [k for k in BT_MAIN_KW if k not in r]
    # 列表表格已去掉「数据集切分」列（切分改在结果页 / 趋势图按「期」展示）
    bad = [k for k in ["数据集切分"] if k in r]
    ok = watermark > 0 and rows > 0 and not miss and not bad
    detail = f"水印={watermark} 表格行={rows} 缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"fc-backtest","ok":ok,"msg":detail}

def check_fc_backtest_create():
    """预测回测配置 · 二级页面：点击「创建任务」进入创建 / 编辑任务页。"""
    inject = ("<script>setTimeout(function(){"
              "var bs=[].slice.call(document.querySelectorAll('.ant-btn'))"
              ".filter(function(x){return x.textContent.indexOf('创建任务')>=0;});"
              "if(bs[0]){bs[0].click();}}, 1600);</script>")
    dump("fc-backtest", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-backtest-创建","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    kw = ["创建回测任务", "任务信息", "回测配件清单", "数据集切分", "训练集", "验证集",
          "保存配置", "返回列表", "预测模拟",
          "⬆ 导入清单", "⬇ 下载模板", "预测粒度", "预测维度",
          "回测区间", "预测集长度", "期", "配件+仓库",
          "经销商类型+配件", "经销商类型+配件+仓库"]
    miss = [k for k in kw if k not in r]
    # 明确不应再出现：选模指标 / ABC 分类 / 计划员 / 评价指标行 / 手动执行按钮 / 各辅助文案
    # ＋ 添加配件 已按需求移除，配件仅通过模板导入
    bad = [k for k in ["选模指标", "ABC分类", "计划员", "评价指标", "保存并执行回测",
                       "指标结果仅输出清单内配件", "触发时机", "决定指标结果按配件",
                       "决定回测输出与指标计算", "单品", "仓库维度", "＋ 添加配件"] if k in r]
    ok = (not miss) and (not bad)
    detail = f"缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"fc-backtest-创建","ok":ok,"msg":detail}

def check_fc_backtest_metric():
    """预测回测配置 · 二级页面：点击行内「结果 / 指标」进入任务结果页。"""
    inject = ("<script>setTimeout(function(){"
              "var ls=[].slice.call(document.querySelectorAll('.link-btn'));"
              "var pick=function(t){return ls.filter(function(x){return x.textContent.trim()===t;});};"
              "var tgt=pick('结果')[0]||pick('指标')[0]||pick('查看')[0];"
              "if(tgt){tgt.click();}}, 1600);</script>")
    dump("fc-backtest", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-backtest-指标","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    kw = ["回测任务结果", "结果", "查看趋势图", "bias", "MAPE", "WAPE",
          "返回列表", "预测粒度", "配件数", "最佳模型"]
    miss = [k for k in kw if k not in r]
    bad = [k for k in ["指标概览", "异常分析", "得分等级", "根因分析", "指标口径说明", "样本数 n",
                       "单品维度", "仓库维度", "配件维度", "base"] if bad_hit(r, k)]
    rows = r.count("ant-table-row")
    radio = r.count("ant-radio-group")
    ok = rows > 0 and radio == 0 and not miss and not bad
    detail = f"表格行={rows} 维度切换={radio} 缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"fc-backtest-指标","ok":ok,"msg":detail}

def check_fc_backtest_dim_wh():
    """预测回测配置 · 结果页：任务维度为「配件+仓库」时（BT2026-005），结果表按 配件 x 仓库 逐行输出，且不带维度切换。"""
    inject = ("<script>setTimeout(function(){"
              "var rows=[].slice.call(document.querySelectorAll('.ant-table-tbody tr.ant-table-row'));"
              "var tgt=null;"
              "for(var i=0;i<rows.length;i++){ if(rows[i].textContent.indexOf('BT2026-005')>=0){ tgt=rows[i]; break; } }"
              "if(tgt){ var ls=[].slice.call(tgt.querySelectorAll('.link-btn'))"
              ".filter(function(x){var t=x.textContent.trim(); return t==='结果'||t==='查看'||t==='指标';});"
              "if(ls[0]){ ls[0].click(); } }}, 1700);</script>")
    dump("fc-backtest", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-backtest-配件+仓库","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    kw = ["配件+仓库", "配件编码", "配件名称", "仓库编码", "仓库名称", "bias", "MAPE", "WAPE", "查看趋势图", "最佳模型"]
    miss = [k for k in kw if k not in r]
    bad = [k for k in ["单品维度", "仓库维度", "配件维度", "指标概览", "异常分析",
                       "得分等级", "base", "样本数 n"] if bad_hit(r, k)]
    rows = r.count("ant-table-row")
    radio = r.count("ant-radio-group")
    ok = rows > 0 and radio == 0 and not miss and not bad
    detail = f"表格行={rows} 维度切换={radio} 缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"fc-backtest-配件+仓库","ok":ok,"msg":detail}

def check_fc_backtest_dim_jxwh():
    """预测回测配置 · 结果页：任务维度为「经销商+配件+仓库」时（BT2026-002），结果表按 经销商 x 配件 x 仓库 逐行输出，含最佳模型列，且不带维度切换。"""
    inject = ("<script>setTimeout(function(){"
              "var rows=[].slice.call(document.querySelectorAll('.ant-table-tbody tr.ant-table-row'));"
              "var tgt=null;"
              "for(var i=0;i<rows.length;i++){ if(rows[i].textContent.indexOf('BT2026-002')>=0){ tgt=rows[i]; break; } }"
              "if(tgt){ var ls=[].slice.call(tgt.querySelectorAll('.link-btn'))"
              ".filter(function(x){var t=x.textContent.trim(); return t==='结果'||t==='查看'||t==='指标';});"
              "if(ls[0]){ ls[0].click(); } }}, 1700);</script>")
    dump("fc-backtest", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-backtest-经销商+配件+仓库","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    kw = ["经销商类型+配件+仓库", "经销商编码", "经销商名称", "配件编码", "仓库编码", "最佳模型",
          "bias", "MAPE", "WAPE", "查看趋势图"]
    miss = [k for k in kw if k not in r]
    bad = [k for k in ["单品维度", "仓库维度", "配件维度", "指标概览", "异常分析",
                       "得分等级", "base", "样本数 n"] if bad_hit(r, k)]
    rows = r.count("ant-table-row")
    radio = r.count("ant-radio-group")
    ok = rows > 0 and radio == 0 and not miss and not bad
    detail = f"表格行={rows} 维度切换={radio} 缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"fc-backtest-经销商类型+配件+仓库","ok":ok,"msg":detail}

def check_fc_backtest_dim_dlrtype():
    """预测回测配置 · 结果页：任务维度为「经销商类型+配件」时（BT2026-001），结果表按 经销商类型 x 配件 逐行输出，含最佳模型列，且不带维度切换。"""
    inject = ("<script>setTimeout(function(){"
              "var rows=[].slice.call(document.querySelectorAll('.ant-table-tbody tr.ant-table-row'));"
              "var tgt=null;"
              "for(var i=0;i<rows.length;i++){ if(rows[i].textContent.indexOf('BT2026-001')>=0){ tgt=rows[i]; break; } }"
              "if(tgt){ var ls=[].slice.call(tgt.querySelectorAll('.link-btn'))"
              ".filter(function(x){var t=x.textContent.trim(); return t==='结果'||t==='查看'||t==='指标';});"
              "if(ls[0]){ ls[0].click(); } }}, 1700);</script>")
    dump("fc-backtest", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-backtest-经销商类型+配件","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    kw = ["经销商类型+配件", "经销商类型", "配件编码", "配件名称", "最佳模型",
          "bias", "MAPE", "WAPE", "查看趋势图", "dealer", "trader"]
    miss = [k for k in kw if k not in r]
    # 该维度不应出现经销商编码 / 仓库编码列，也不应出现草稿专属元素
    bad = [k for k in ["经销商编码", "仓库编码", "单品维度", "仓库维度", "配件维度", "指标概览",
                       "异常分析", "得分等级", "base", "样本数 n",
                       "销售及售后服务", "仅销售", "仅售后", "城市展厅", "卫星店"] if bad_hit(r, k)]
    rows = r.count("ant-table-row")
    radio = r.count("ant-radio-group")
    ok = rows > 0 and radio == 0 and not miss and not bad
    detail = f"表格行={rows} 维度切换={radio} 缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"fc-backtest-经销商类型+配件","ok":ok,"msg":detail}

def check_fc_backtest_drill():
    """预测回测配置 · 弹窗：进入结果页 → 点「查看趋势图」，校验弹窗 ECharts 图表（仅实际需求 + 验证集后预测值，无根因分析）。"""
    inject = ("<script>setTimeout(function(){"
              "var ls=[].slice.call(document.querySelectorAll('.link-btn'));"
              "var pick=function(t){return ls.filter(function(x){return x.textContent.trim()===t;});};"
              "var tgt=pick('结果')[0]||pick('指标')[0]||pick('查看')[0];"
              "if(tgt){tgt.click();}}, 1400);"
              "setTimeout(function(){"
              "var ts=[].slice.call(document.querySelectorAll('.ant-tabs-tab'));"
              "var t=ts.filter(function(x){return x.textContent.indexOf('异常分析')>=0;})[0];"
              "if(t){t.click();}}, 2300);"
              "setTimeout(function(){"
              "var ds=[].slice.call(document.querySelectorAll('.link-btn'))"
              ".filter(function(x){return x.textContent.trim()==='查看趋势图';});"
              "if(ds[0]){ds[0].click();}}, 3200);</script>")
    dump("fc-backtest", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-backtest-趋势图","ok":False,"msg":"渲染失败/错误页"}
    clean = strip_scripts(data)   # 仅看运行时渲染出的 DOM（弹窗经 teleport 到 body，需扫全文档）
    modal = 'id="btDrillChart"' in clean
    canvas = clean.count("<canvas")
    kw = ["预测趋势图", "历史实际需求", "验证集", "预测集", "各候选模型预测曲线", "训练集", "预测维度", "期"]
    miss = [k for k in kw if k not in clean]
    # 趋势图已按需求：真实需求去掉 A_i 后缀、预测集去掉「（外推）」
    bad = [k for k in ["根因分析", "偏差 e_i", "历史实际需求 A_i", "（外推）"] if k in clean]
    ok = modal and canvas > 0 and not miss and not bad
    detail = f"弹窗={modal} canvas={canvas} 缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"fc-backtest-趋势图","ok":ok,"msg":detail}

def check_fc_long_coef():
    """长周期预测报表 / 一次买断预测结果：页面「系数调整」按钮 → 弹窗内维护 10 年系数。"""
    # 探针：点击「系数调整」按钮后，统计弹窗内真实渲染的年份系数输入框（排除 x-template 源码文本干扰）
    inject = ("<script>setTimeout(function(){"
              "var bs=[].slice.call(document.querySelectorAll('.ant-btn')).filter(function(x){return x.textContent.indexOf('系数调整')>=0;});"
              "if(bs[0]){bs[0].click();}"
              "setTimeout(function(){"
              "var n=0,txt=0;"
              "[].slice.call(document.querySelectorAll('.ant-modal-content')).forEach(function(c){"
              "if(c.textContent.indexOf('长周期预测结果调整系数')>=0){txt++; n+=c.querySelectorAll('.ant-input-number').length;}});"
              "var d=document.createElement('div'); d.id='zzprobe'; d.textContent='ZZPROBE btn='+bs.length+' modalWithTxt='+txt+' inputs='+n; document.body.appendChild(d);"
              "}, 800);"
              "}, 1500);</script>")
    dump("fc-long-draft", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-long-系数","ok":False,"msg":"渲染失败/错误页"}
    # 系数调整弹窗入口仅草稿页(fc-long-draft)提供；git 成品无草稿页时跳过该校验
    if "生成bridge buy计划" not in rendered(data):
        return {"key":"fc-long-系数","ok":True,"msg":"草稿页不可用-跳过"}
    m = re.search(r"ZZPROBE btn=(\d+) modalWithTxt=(\d+) inputs=(\d+)", data)
    if not m:
        return {"key":"fc-long-系数","ok":False,"msg":"未取得弹窗探针"}
    btn, mw, inp = int(m.group(1)), int(m.group(2)), int(m.group(3))
    ok = btn >= 1 and mw >= 1 and inp >= 10
    detail = f"页面按钮={btn} 弹窗命中={mw} 弹窗内年份系数输入={inp}"
    return {"key":"fc-long-系数","ok":ok,"msg":detail}

def check_fc_backtest_parts():
    """预测回测配置 · 创建页配件清单：已移除「＋ 添加配件」，仅通过「⬆ 导入清单」模板导入，校验清单联动。"""
    inject = ("<script>setTimeout(function(){"
              "var bs=[].slice.call(document.querySelectorAll('.ant-btn'))"
              ".filter(function(x){return x.textContent.indexOf('创建任务')>=0;});"
              "if(bs[0]){bs[0].click();}}, 1400);"
              "setTimeout(function(){"
              "var as=[].slice.call(document.querySelectorAll('.ant-btn'))"
              ".filter(function(x){return x.textContent.indexOf('导入清单')>=0;});"
              "if(as[0]){as[0].click();}}, 2600);</script>")
    dump("fc-backtest", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-backtest-配件清单","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    miss_form = [k for k in ["回测配件清单", "⬆ 导入清单", "⬇ 下载模板"] if k not in r]
    # 原「＋ 添加配件」按钮与其弹窗入口不应再出现（弹窗经 teleport 到 body，不在 rendered 片段内）
    bad_form = [k for k in ["指标结果仅输出清单内配件", "＋ 添加配件"] if k in r]
    m = re.search(r"已选\s*(\d+)\s*个配件", r)
    cnt = int(m.group(1)) if m else 0
    ok = (not miss_form) and (not bad_form) and cnt >= 1
    detail = f"表单缺失={miss_form if miss_form else '无'} 残留={bad_form if bad_form else '无'} 清单数={cnt}"
    return {"key":"fc-backtest-配件清单","ok":ok,"msg":detail}

def check_gp_list():
    """基础数据管理 · 全局参数：列表页（菜单/面包屑/表格/新参数行）。"""
    dump("gp-params")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"gp-list","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    kw = ["全局参数", "参数代码", "参数描述", "默认值", "备注", "修改人名称", "更新时间",
          "搜 索", "编辑",
          "PARM01", "共 29 条"]
    miss = [k for k in kw if k not in r]
    rows = r.count("ant-table-row")
    ok = rows > 0 and not miss
    detail = f"表格行={rows} 缺失={miss if miss else '无'}"
    return {"key":"gp-list","ok":ok,"msg":detail}

def check_gp_edit():
    """基础数据管理 · 全局参数：编辑页（点击首个数据行「编辑」→ 普通参数编辑表单）。
    注：年份系数功能已迁出全局参数（移至长周期/一次买断），故编辑页不再含 10 个年份系数输入。"""
    inject = ("<script>setTimeout(function(){"
              "var rows=[].slice.call(document.querySelectorAll('.ant-table-tbody tr'));"
              "var tgt=rows.filter(function(r){return r.querySelector('.link-btn');})[0];"
              "if(tgt){tgt.querySelector('.link-btn').click();}}, 1600);</script>")
    dump("gp-params", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"gp-edit","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    kw = ["基础信息", "参数代码", "参数描述", "默认值", "备注", "返 回", "确 定"]
    miss = [k for k in kw if k not in r]
    bad = [k for k in ["10 项年份系数", "LONG_CYCLE_ADJUST_COEFFICIENT"] if k in r]
    ok = (not miss) and (not bad)
    detail = f"缺失={miss if miss else '无'} 年份系数残留={bad if bad else '无'}"
    return {"key":"gp-edit","ok":ok,"msg":detail}

def check_part_group():
    """配件组管理：列表渲染、两类分组（联合MOQ/成套采购组）并存与批量管理能力。"""
    dump("part-group")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"part-group","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    rows = r.count("ant-table-row")
    must = {
        "列-分组编码": "分组编码" in r,
        "列-分组类型": "分组类型" in r,
        "类型-联合MOQ": "联合MOQ" in r,
        "类型-成套采购组": "成套采购组" in r,
        "按钮-新建分组": "新建分组" in r,
        "按钮-批量启用": "批量启用" in r,
        "按钮-批量停用": "批量停用" in r,
        "按钮-批量删除": "批量删除" in r,
    }
    not_want = ["批量导入配件"]
    extra = [k for k in not_want if k in r]
    missing = [k for k, v in must.items() if not v]
    ok = rows > 0 and not missing and not extra
    detail = f"rows={rows} " + ("缺失=" + ",".join(missing) if missing else "缺失=无") + \
             (" 残留=" + ",".join(extra) if extra else "")
    return {"key":"part-group","ok":ok,"msg":detail}

def check_pg_no_max_months():
    """配件组管理（2026-11-09）：两类分组统一不再维护「最大备货月数」——
    新增/编辑清单、详情清单、批量导入模板与预览均只保留「配件号」单列口径；
    详情弹窗对联合 MOQ 分组补充只读「联合 MOQ 数量」（取 moq_qty）。
    断言：详情新增项与单列模板齐备；配件组三段区间内不得残留任何维护/展示该字段的实现。
    注意：配件组章节保留 2 条说明性注释含「最大备货月数」裸词，故仍按区间限定断言；
    全局零残留断言由 check_po_no_max_months 负责。"""
    src = open(HTML, encoding="utf-8", errors="replace").read()
    need = [
        '<!-- 配件组管理：联合 MOQ 分组在详情补充展示阈值数量（只读，取 moq_qty） -->',
        "label=\"联合 MOQ 数量\">{{ genDetailRow.moq_qty ?? '—' }}",
        "const lines = ['配件号'];",
        "out.push({ part_code:code });",
        '两类分组统一为配件号 / 配件名称 / 供应商 / 操作',
        '两类分组统一三列，不再展示最大备货月数',
        '已解析 {{ pgPasteRows.length }} 行（配件号）',
    ]
    bad = [
        "dataIndex:'max_stock_months'", "column.dataIndex==='max_stock_months'",
        "max_stock_months:2", "r.max_stock_months", "p.max_stock_months",
        "'配件号,最大备货月数'", '含「最大备货月数」', '配件号 + 最大备货月数',
        "title:'最大备货月数'",
    ]
    segs = [
        re.search(r'<!-- ===== 通用主数据详情.*?<a-drawer v-else', src, re.S),
        re.search(r'<!-- 新增/编辑 配件组.*?<!-- 删除分组确认 -->', src, re.S),
        re.search(r'/\* ---- 配件组管理（part-group）---- \*/.*?/\* ---- 通用图片附件交互', src, re.S),
    ]
    seg = "\n".join(m.group(0) for m in segs if m)
    miss = [k for k in need if k not in src]
    stale = [k for k in bad if k in seg]
    if len([m for m in segs if m]) != 3:
        stale.append("配件组区间未完整定位")
    ok = (not miss) and (not stale)
    return {"key": "pg-无最大备货月数", "ok": ok,
            "msg": f"缺失={miss if miss else '无'} 残留={stale if stale else '无'}"}

def check_po_no_max_months():
    """采购计划（2026-11-09）：按 PRD 12.6「涉及到最大备货月数的逻辑都删除」口径，
    常规/历史采购计划列表、列设置、导出自选字段、单块详情弹窗共用 poRegColumns，
    删除「最大备货月数」后统一为 57 数据列 + 1 操作列；「最高风控线」single_max_limit 保留。
    断言：源码级零残留 max_stock_months / maxStockMonths / title:'最大备货月数'，
    poRegColumns 元素数 58，且保留最高风控线。裸词「最大备货月数」仅允许配件组章节 2 条注释。"""
    src = open(HTML, encoding="utf-8", errors="replace").read()
    stale = [k for k in ("max_stock_months", "maxStockMonths", "title:'最大备货月数'") if k in src]
    m = re.search(r'const poRegColumns\s*=\s*\[(.*?)\n\s*\];', src, re.S)
    n = len(re.findall(r"\{\s*title:'", m.group(1))) if m else -1
    if n != 58:
        stale.append("poRegColumns 元素数=%d(应为 57 数据列+操作列共 58)" % n)
    if "single_max_limit" not in src:
        stale.append("最高风控线 single_max_limit 缺失")
    if "title:'最高风控线'" not in src or "title:'单品最大上限'" in src:
        stale.append("列名未对齐 12.6 口径（应为「最高风控线」）")
    if src.count("最大备货月数") != 2:
        stale.append("裸词「最大备货月数」出现 %d 次(应仅配件组 2 条注释)" % src.count("最大备货月数"))
    return {"key": "po-无最大备货月数", "ok": not stale,
            "msg": f"poRegColumns={n}（57 数据列+操作列） 残留={stale if stale else '无'}"}

def check_qty_col_order():
    """4 个计划页数量列改名与调序（2026-11-10）。
    - All Time Buy / Bridge Buy / 参考零件采购计划（poPlanCfg）：显示名「采购计划数量」→
      「推荐计划数量」，且「调整计划数量」列前置；key/dataIndex 仍为 plan_qty，不得误改数据字段。
    - 常规采购计划（poRegColumns 首屏）：「调整计划数量」置于「推荐计划数量(凑MPQ后)」之前。
    - 三页共用调整弹窗 3 处写死文案（只读描述项 / placeholder / 保存校验提示）同步改名。
    其它模块（计划生成日志术语、MOQ 计算注释、预测生成采购计划预览表 fcGenPoResultCols）
    仍可合法使用「采购计划数量」，故旧名零残留断言只限定在 poPlanCfg 区间内，禁止全局裸词断言。
    """
    src = open(HTML, encoding="utf-8", errors="replace").read()
    miss, stale = [], []

    m = re.search(r'const poPlanCfg\s*=\s*\{(.*?)\n\s*\};\s*\n\s*const poPlanFilters', src, re.S)
    if not m:
        return {"key": "qty-列改名与调序", "ok": False, "msg": "poPlanCfg 区间未定位"}
    cfg = m.group(1)
    keys = ("'po-atb'", "'po-bridge'", "'po-ref'")
    starts = [(k, cfg.find(k + ': {')) for k in keys]
    for i, (k, st) in enumerate(starts):
        if st < 0:
            stale.append(k + " 区间未定位")
            continue
        en = starts[i + 1][1] if i + 1 < len(starts) and starts[i + 1][1] > st else len(cfg)
        seg = cfg[st:en]
        if "title:'采购计划数量'" in seg:
            stale.append(k + " 残留旧列名「采购计划数量」")
        a, b = seg.find("title:'调整计划数量'"), seg.find("title:'推荐计划数量'")
        if not (0 <= a < b):
            stale.append(k + " 列序非「调整计划数量 → 推荐计划数量」")
        if "key:'plan_qty', dataIndex:'plan_qty'" not in seg:
            stale.append(k + " plan_qty 数据字段被误改")

    mr = re.search(r'const poRegColumns\s*=\s*\[(.*?)\n\s*\];', src, re.S)
    if not mr:
        stale.append("poRegColumns 区间未定位")
    else:
        reg = mr.group(1)
        a, b = reg.find("title:'调整计划数量'"), reg.find("title:'推荐计划数量(凑MPQ后)'")
        if not (0 <= a < b):
            stale.append("poRegColumns 首屏列序非「调整计划数量 → 推荐计划数量(凑MPQ后)」")

    for k in ('<a-descriptions-item label="推荐计划数量">',
              'placeholder="调整数量与推荐计划数量不一致时必填"',
              "+ '）与推荐计划数量（'"):
        if k not in src:
            miss.append("弹窗文案:" + k[:34])
    for k in ('<a-descriptions-item label="采购计划数量">',
              'placeholder="调整数量与采购计划数量不一致时必填"',
              "+ '）与采购计划数量（'"):
        if k in src:
            stale.append("弹窗旧文案残留:" + k[:34])
    # 非本范围的 3 处合法旧名仍应保留，防止误伤全局替换
    if src.count('title:\'采购计划数量\'') != 1:
        stale.append("非范围模块（fcGenPoResultCols）旧列名被误改或重复")
    ok = (not miss) and (not stale)
    return {"key": "qty-列改名与调序", "ok": ok,
            "msg": f"4 页列序/改名/弹窗文案齐备 缺失={miss if miss else '无'} 残留={stale if stale else '无'}"}

def check_ps_default():
    """配件与供应商关系（2026-11-09 v2）：默认供应商改为「编辑」弹窗内维护。
    断言：列表列 / 筛选 / 行操作「编辑」入口 / 编辑弹窗全字段只读 + 仅「是否默认供应商」
    可选是·否 / 同配件互斥保存 / setup return 暴露齐备；采购计划多供应商拦截恢复
    「选择默认供应商」逻辑（radio 标题 + 保存时回写），不得残留上一版专用维护弹窗与文字引导。
    对应 PRD 4.4.1、4.4.4.3 与 12.6 待确认项。"""
    src = open(HTML, encoding="utf-8", errors="replace").read()
    need = [
        "key:'is_default_supplier'",
        "{key:'default', label:'是否默认供应商'",
        "v-else-if=\"activeMenu==='part-supplier'\"",
        "@click.stop=\"openGenEdit(record)\">编辑",
        "activeMenu==='part-supplier' ? psSaveGenEdit() : saveGenEdit()",
        "<template v-if=\"activeMenu==='part-supplier' && genEditRow\">",
        "activeMenu==='part-supplier' ? null : undefined",
        "<a-button type=\"primary\" @click=\"psSaveGenEdit\">保存</a-button>",
        "activeDef.columns.filter(x=>x.key!=='action' && x.key!=='is_default_supplier')",
        "<a-input :value=\"genEditRow[c.dataIndex]\" disabled/>",
        "v-model:value=\"genEditRow.is_default_supplier\"",
        "<a-radio value=\"是\">是</a-radio>",
        "<a-radio value=\"否\">否</a-radio>",
        "function psSaveGenEdit()",
        "x.is_default_supplier='否'",
        "psSaveGenEdit,",
        "选择默认供应商（及其对应 MOQ）",
        "upd.default_supplier_code = sel.code",
        "relRows.forEach(x=>{ x.is_default_supplier",
    ]
    bad = [
        "psDefaultOpen",
        "psOpenDefault",
        "psSaveDefault",
        "维护默认供应商",
        "本弹窗仅用于本次计划选定供应商",
        "不调整默认供应商",
        "请前往「配件与供应商关系」页面维护",
        "v-model:checked=\"poRegEditRow.is_default_supplier\"",
        "v-model:value=\"poRegEditRow.is_default_supplier\"",
    ]
    miss = [k for k in need if k not in src]
    stale = [k for k in bad if k in src]
    # 多供应商分支区间：必须含「选择默认供应商」，不得残留「仅文字引导」类表述
    m = re.search(r"<div v-if=\"poRegEditRow\.block_reason==='多供应商'\" class=\"jlrs-form-grid\">(.*?)</div>", src, re.S)
    if not m:
        stale.append("多供应商分支区间未定位")
    elif "选择默认供应商" not in m.group(1) or "不调整默认供应商" in m.group(1):
        stale.append("多供应商分支未恢复选择默认供应商")
    ok = (not miss) and (not stale)
    return {"key": "ps-编辑默认供应商", "ok": ok,
            "msg": f"缺失={miss if miss else '无'} 残留={stale if stale else '无'}"}

def check_menu():
    """校验左侧菜单结构：需求预测一级菜单及子页、占位菜单已移除、采购计划组顺序等。"""
    dump("wh-abc")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"menu","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    # 期望出现
    must_have = ["需求预测", "预测模拟", "参考零件需求预测", "长周期预测报表", "一次买断预测结果", "常规预测", "仓库级常规预测", "最佳模型",
                 "服务水平dashboard", "基础数据管理",
                 "库存策略参数", "采购LT", "目标满足率", "备货规则", "库间LT", "增储天数", "计划周期", "配件风控线", "配件多分类风控线", "建储水位线计算结果",
                 "配件组管理",
                 "计划管理", "采购计划", "历史采购计划", "采购计划导出", "调拨计划", "调拨计划导出", "调拨计划汇总", "给仓库的预计调拨计划",
                 "All Time Buy 计划", "Bridge Buy 计划", "参考零件采购计划",
                 "给供应商的滚动计划",
                 "历史需求处理", "活动登记表", "数据感知任务", "订单监控预警"]
    miss = [k for k in must_have if k not in r]
    # 不应出现（已移除的纯占位菜单 / 已更名的旧称）
    must_not = ["准确率报表", "预测回测配置",
                "售后订单管理", "【本地测试页面】", "计划层级管理3",
                "全新车型配件预测", "参考零件采购计划（首储）",
                "常规采购计划", "本周调拨计划", "下周调拨计划", "给仓库的滚动调拨计划"]
    bad = [k for k in must_not if k in r]
    # 采购计划组内 参考零件采购计划 之后直接是「报表」组
    ipo = r.find("参考零件采购计划")
    irep = r.find("服务水平dashboard")
    if not (0 <= ipo < irep):
        bad.append("采购计划组顺序(po-ref 后应为报表组)")
    # 顺序要求：给供应商的滚动计划 应位于 采购计划（po-regular）之后、调拨计划（sto-week）之前
    ipo_reg = r.find("采购计划")
    iroll = r.find("给供应商的滚动计划")
    isto = r.find("调拨计划")   # 先命中「调拨计划」(本周改名)，其位置在「给仓库的滚动调拨计划」之前
    if not (0 <= ipo_reg < iroll < isto):
        bad.append("采购计划组顺序(po-roll 应在采购计划下、调拨计划上)")
    # 顺序要求：调拨计划(sto-week) → 调拨计划导出(sto-export) → 调拨计划汇总(sto-summary) → 给仓库的预计调拨计划(sto-next)
    isto_exp = r.find("调拨计划导出")
    isum = r.find("调拨计划汇总")
    inext = r.find("给仓库的预计调拨计划")
    if not (0 <= isto < isto_exp < isum < inext):
        bad.append("计划顺序(调拨计划 → 调拨计划导出 → 调拨计划汇总 → 给仓库的预计调拨计划)")
    # 顺序要求：历史采购计划 / 采购计划导出 应位于 采购计划 之下、给供应商的滚动计划 之上
    ihist = r.find("历史采购计划")
    iexp = r.find("采购计划导出")
    if not (0 <= ipo_reg < ihist < iexp < iroll):
        bad.append("采购计划组顺序(po-history/po-export 应在采购计划下、给供应商的滚动计划上)")
    ok = (not miss) and (not bad)
    detail = f"缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"menu","ok":ok,"msg":detail}

# 「库存策略参数」8 页：由 inventory-strategy.js / inventory-results.js 外部组件渲染，
# 页面分发块一旦被误删，整组页面会静默空白（无任何报错），故单列一桶强校验。
STRATEGY_PAGES = [
    ("strategy-purchase", "采购LT"),
    ("strategy-service",  "目标满足率"),
    ("strategy-transfer", "库间LT"),
    ("strategy-increase", "增储天数"),
    ("strategy-cycle",    "计划周期"),
    ("strategy-risk",     "配件风控线"),
    ("strategy-riskRule", "配件多分类风控线"),
    ("strategy-result",   "建储水位线计算结果"),
]

def check_strategy():
    """库存策略参数：每页必须渲染出表格行且命中页面标题，防止分发块缺失导致整模块空白。"""
    bad = []
    for key, title in STRATEGY_PAGES:
        r = rendered(dump(key))
        rows = r.count("ant-table-row")
        if rows <= 0:
            bad.append(f"{key}(rows=0)")
        elif not has_col(r, title):
            bad.append(f"{key}(缺标题:{title})")
    if bad:
        return {"ok": False, "msg": "异常: " + ", ".join(bad)}
    return {"ok": True, "msg": f"{len(STRATEGY_PAGES)} 页全部渲染正常"}

STO_PAGES = [("sto-week", "调拨计划"), ("sto-next", "给仓库的预计调拨计划")]
# 字段口径＝PRD 6.3.4 计算输出（最新；按用户调整）：移除计划类型/是否出计划日/备注列；
# 预期/可用/欠交/库间在途/缺货拆为（发货仓）/（收货仓）两组；新增 推荐计划数量(MPQ取整后)/推荐计划数量、导出状态、是否下单
STO_COLS = ["数据生成日期", "配件号", "配件名称", "发货仓", "收货仓",
            "收货仓最低风控线", "收货仓目标库存", "ABC分类", "车型代码", "计划员",
            "计划批次", "计划行", "预期库存（发货仓）", "可用库存数量（发货仓）", "欠交数量（发货仓）",
            "库间在途数量（发货仓）", "缺货数量（发货仓）", "预期库存（收货仓）", "可用库存数量（收货仓）",
            "欠交数量（收货仓）", "库间在途数量（收货仓）", "缺货数量（收货仓）", "近3个月月均销量",
            "当前可用天数", "推荐计划数量(取整前)", "推荐计划数量(分配后)", "推荐计划数量(MPQ取整后)",
            "推荐计划数量", "库间LT", "要求到货日期",
            "体积", "体积单位", "预计调拨体积", "导出状态", "是否下单"]
STO_FORBIDDEN = ["缺口", "STO单号", "执行状态", "所需车次", "建议调拨数量", "缺口结转标记"]

def check_sto():
    """调拨计划（STO）：2 页必须渲染表格行且命中 PRD 6.3.4 计算输出字段；不得残留缺口/STO单号等已删字段；
    本周（执行，W2643）与下周（预排，W2644）计划批次体现时点差异。计划类型已不列为表头列（仅筛选/详情承载）。"""
    bad = []
    for key, title in STO_PAGES:
        r = rendered(dump(key))
        if r.count("ant-table-row") <= 0:
            bad.append(key + "(rows=0)")
        miss = [c for c in STO_COLS if c not in r]
        if miss:
            bad.append(key + "(缺列:" + ",".join(miss) + ")")
        res = [c for c in STO_FORBIDDEN if c in r]
        if res:
            bad.append(key + "(残留:" + ",".join(res) + ")")
    rw = rendered(dump("sto-week"))
    rn = rendered(dump("sto-next"))
    if "W2643" not in rw:
        bad.append("sto-week(缺计划批次W2643)")
    if "W2644" not in rn:
        bad.append("sto-next(缺计划批次W2644)")
    if "W2644" in rw or "W2643" in rn:
        bad.append("sto(批次时点串页)")
    # 计划类型已不列为表头列（仅筛选/详情承载），故不再断言列表文本；
    # 以「下周页不得出现紧急/常规」反向校验类型口径正确
    if "紧急调拨计划" in rn or "常规调拨计划" in rn:
        bad.append("sto-next(不应出现紧急/常规调拨计划)")
    if bad:
        return {"ok": False, "msg": "异常: " + ", ".join(bad)}
    return {"ok": True, "msg": "2 页渲染正常，字段口径对齐 PRD 6.3.4 计算输出"}

def check_sto_detail_no_remark():
    """调拨计划 / 给仓库的预计调拨计划 共用详情弹窗（2026-11-07）：
    两页详情弹窗已去掉「备注」功能——不再有备注编辑区、字数统计、保存备注按钮与 remark 字段，
    弹窗为纯只读字段展示，底栏仅保留「关闭」。
    源码级断言：只读弹窗注释 / 简化后的 stoOpenDetail / setup return 齐备；
    全局与弹窗区间内均不得残留备注编辑相关实现。"""
    src = open(HTML, encoding="utf-8", errors="replace").read()
    need = ["<!-- 详情弹窗：只读字段展示，不提供备注编辑 -->",
            "/* 详情：纯只读字段展示，不提供备注编辑与保存入口 */",
            "function stoOpenDetail(r){ stoDetailRow.value = r; stoDetailOpen.value = true; }",
            "stoDetailOpen, stoDetailRow, stoOpenDetail,",
            "详情弹窗为纯只读字段展示，不提供备注编辑与保存"]
    bad = ["stoDetailRemark", "stoSaveRemark", "可在本弹窗内编辑并保存",
           "保存备注", "备注已保存", "unmet_qty:unmetQty, remark:remark",
           "备注支持在详情弹窗内编辑保存"]
    m = re.search(r'<!-- 详情弹窗：只读字段展示.*?</a-modal>', src, re.S)
    seg = m.group(0) if m else ""
    # 注释本身含「备注」二字属正常，故只按具体 UI 元素判定残留
    seg_bad = [k for k in ["<a-textarea", "bt-sec-t", "保存备注"] if k in seg]
    miss = [k for k in need if k not in src]
    stale = [k for k in bad if k in src]
    if not seg:
        stale.append("详情弹窗区间未定位")
    ok = (not miss) and (not stale) and (not seg_bad)
    return {"key": "sto-详情弹窗无备注", "ok": ok,
            "msg": f"缺失={miss if miss else '无'} 残留={stale if stale else '无'} 弹窗区间残留={seg_bad if seg_bad else '无'}"}

def check_sto_summary():
    """调拨计划汇总（sto-summary）：PRD 6.4.3 汇总维度页面，导出后的「已执行计划」只读报表。
    列结构严格按 6.4.3.2 计算逻辑表：固定 3 列（数据快照日期 / 配件号 / 配件名称）+ 每个区域仓 9 列
    （是否备货标识、目标库存、本次分配率、本次分配量、预期库存、现有库存、当前库存占比、
    分配后库存占比、目标库存占比）+ 中心仓 4 列（{中心仓编码} 全网可用库存、STO分配后库存、
    STO分配总量、近3个月月均销量）。CJLR / JLR＝43 列，JLRC＝34 列。
    断言：渲染出行、43 列齐备、三套仓网可切换、仅导出（无导入/无编辑/无审批），且旧指标名已移除。"""
    r = rendered(dump("sto-summary"))
    bad = []
    if r.count("ant-table-row") <= 0:
        bad.append("rows=0")
    for c in ["数据快照日期", "配件号", "配件名称"]:
        if c not in r:
            bad.append("缺列:" + c)
    # CJLR 仓网：中心仓 CJDC，区域仓 CJV0~CJV3，每组 9 列（指标名取自 6.4.3.2 计算逻辑表）
    for reg in ["CJV0", "CJV1", "CJV2", "CJV3"]:
        if (reg + " 是否备货标识") not in r:
            bad.append("缺列:" + reg + " 是否备货标识")
        for m in ["目标库存", "本次分配率", "本次分配量", "预期库存", "现有库存",
                  "当前库存占比", "分配后库存占比", "目标库存占比"]:
            if (reg + " " + m) not in r:
                bad.append("缺列:" + reg + " " + m)
    for c in ["CJDC 全网可用库存", "CJDC STO分配后库存", "CJDC STO分配总量", "CJDC 近3个月月均销量"]:
        if c not in r:
            bad.append("缺列:" + c)
    # 旧指标名应已移除（严格对齐 6.4.3.2 计算逻辑表）
    for c in ["调拨占比", "调拨数量", "库存+在途", "潜在缺口", "当前占比", "目标占比",
              "中心仓库存", "调拨后未分配量", "总需求", "已分配量",
              "STO分配率", "STO计划量", "Currenratio", "SSQ Ratio"]:
        if c in r:
            bad.append("残留旧指标名:" + c)
    for n in ["CJLR", "JLR", "JLRC"]:
        if n not in r:
            bad.append("缺仓网:" + n)
    if "导入" in r:
        bad.append("不应有导入")
    if "审批通过" in r or "驳回" in r:
        bad.append("报表页不应有审批按钮")
    if bad:
        return {"ok": False, "msg": "异常: " + ", ".join(bad)}
    return {"ok": True, "msg": "已执行计划汇总渲染正常（43 列严格对齐 6.4.3.2 计算逻辑表 / 三套仓网切换 / 仅导出无编辑）"}

def check_sto_export():
    """调拨计划导出（sto-export）：严格按 PRD 6.4.2.2「STO 下单模板」字段，列表＝10 模板列 + 导出状态 + 操作。
    断言：列集/顺序与模板严格一致、SAP 固定值带出、查询条件 5 项与模板数据字段一致、模板外旧列不得残留、
    顶部仅「待导出」tab、无导入/审批/新增、导出按钮存在。"""
    re_ = rendered(dump("sto-export"))
    bad = []
    if re_.count("ant-table-row") <= 0:
        bad.append("sto-export(rows=0)")
    ehds = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", re_, re.S)]
    ehds = [h for h in ehds if h]  # 剔除勾选列的空表头
    tpl_cols = ["Order Type (Purchasing)", "发货仓", "Purchasing Organization", "Purchasing Group",
                "Company Code", "计划批次", "计划行", "配件号", "数量", "收货仓",
                "导出状态", "操作"]
    if ehds != tpl_cols:
        bad.append("sto-export(列集/顺序与6.4.2.2模板不一致:" + " / ".join(ehds) + ")")
    # SAP 固定值须在单元格中带出
    for fixed in ["ZC", "CJV0", "CN01", "000", "CJLR", "CN02"]:
        if fixed not in re_:
            bad.append("sto-export(缺固定值:" + fixed + ")")
    # 查询条件须与 6.4.2.2 模板数据字段一致：5 个筛选标签 配件号/发货仓/收货仓/计划批次/计划行
    flabels = re.findall(r'class="f-label">([^<]*)</span>', re_)
    for fl in ["配件号", "发货仓", "收货仓", "计划批次", "计划行"]:
        if fl not in flabels:
            bad.append("sto-export(查询条件缺:" + fl + ")")
    # 模板外旧列不得残留（只查列头，避免命中筛选区同名标签）
    for col in ["数据生成日期", "配件名称", "推荐计划数量(分配后)", "推荐计划数量(MPQ取整后)",
                "推荐计划数量(取整前)", "收货仓最低风控线", "收货仓目标库存", "ABC分类", "车型代码",
                "计划员", "体积", "体积单位", "预计调拨体积", "库间LT", "要求到货日期",
                "预期库存（发货仓）", "预期库存（收货仓）", "可用库存数量（发货仓）", "可用库存数量（收货仓）",
                "欠交数量（发货仓）", "欠交数量（收货仓）", "库间在途数量（发货仓）", "库间在途数量（收货仓）",
                "缺货数量（发货仓）", "缺货数量（收货仓）", "近3个月月均销量", "当前可用天数", "导出时间", "是否下单"]:
        if col in ehds:
            bad.append("sto-export(不应出现模板外列:" + col + ")")
    # 顶部 tab：仅 待导出（不应有「全部」「已导出」tab）
    if "待导出" not in re_:
        bad.append("sto-export(缺tab:待导出)")
    if "已导出" in re_:
        bad.append("sto-export(不应有「已导出」tab)")
    if has_col(re_, "全部"):
        bad.append("sto-export(不应有「全部」tab)")
    # 无导入 / 审批 / 编辑按钮
    for b in ["导入", "审批通过", "驳回", "新增"]:
        if b in re_:
            bad.append("sto-export(不应有:" + b + ")")
    # antd 两字按钮会自动插空格（"导 出"），用正则匹配
    if not re.search(r'>\s*导\s*出\s*<', re_):
        bad.append("sto-export(缺「导出」按钮)")
    if bad:
        return {"ok": False, "msg": "异常: " + ", ".join(bad)}
    return {"ok": True, "msg": "调拨计划导出渲染正常（12 列＝6.4.2.2 模板 10 列＋导出状态/操作；仅 待导出 1 个tab、导出即自动记录导出时间）"}


def check_po_plan():
    """采购计划扩展 3 页：All Time Buy 计划 / Bridge Buy 计划 / 参考零件采购计划。
    断言列集对齐 PRD 第 6/7 章，且各页专属能力齐备。
    2026-11-10：「采购计划数量」显示名改为「推荐计划数量」，且「调整计划数量」列前置。"""
    pages = [
        ("po-atb", "All Time Buy 计划",
         ["配件号", "配件名称", "全国预期库存", "全生命周期累计需求", "净需求", "MOQ", "MPQ",
          "推荐计划数量", "调整计划数量", "停产标记", "单据状态", "审批人", "审批时间"]),
        ("po-bridge", "Bridge Buy 计划",
         ["配件号", "配件名称", "收货仓库", "买断区间", "区间预测需求量", "属地预期库存", "净需求", "MOQ", "MPQ",
          "推荐计划数量", "调整计划数量", "单据状态", "审批人"]),
        ("po-ref", "参考零件采购计划",
         ["新件配件号", "配件名称", "参考车型", "参考配件号", "采购区间", "预测需求量", "全国预期库存", "净需求", "MOQ", "MPQ",
          "推荐计划数量", "调整计划数量", "单据状态", "审批人"]),
    ]
    bad = []
    for key, title, cols in pages:
        r = rendered(dump(key))
        if r.count("ant-table-row") <= 0:
            bad.append(key + "(rows=0)")
        miss = [c for c in cols if c not in r]
        if miss:
            bad.append(key + "(缺列:" + ",".join(miss) + ")")
    ra = rendered(dump("po-atb"))
    rb = rendered(dump("po-bridge"))
    rr = rendered(dump("po-ref"))
    if "买断区间" not in rb:
        bad.append("po-bridge(缺买断区间)")
    if "展开年份" in rb or "折叠年份" in rb:
        bad.append("po-bridge(不应有展开/折叠年份)")
    if "年份" in rb and "买断区间" not in rb:
        bad.append("po-bridge(不应保留按年展开的年份列)")
    if "导入" in rr:
        bad.append("po-ref(不应有导入)")
    if "采购区间" not in rr:
        bad.append("po-ref(缺采购区间列)")
    if "买断区间" in rr:
        bad.append("po-ref(不应有买断区间)")
    # 审批状态页签（与常规采购计划一致）：全部 / 待提交 / 待审批 / 已驳回 / 审批通过
    for key, r in [("po-atb", ra), ("po-bridge", rb), ("po-ref", rr)]:
        for t in ["待提交", "待审批", "已驳回", "审批通过"]:
            if t not in r:
                bad.append(key + "(缺审批页签:" + t + ")")
    if "是否疑难件" in rb:
        bad.append("po-bridge(不应有是否疑难件)")
    if "bridge buy 标签" in rb:
        bad.append("po-bridge(不应有bridge buy标签)")
    if bad:
        return {"ok": False, "msg": "异常: " + ", ".join(bad)}
    return {"ok": True, "msg": "3 页渲染正常，列集对齐 PRD 第 6/7 章"}

def check_po_roll():
    """给供应商的滚动计划（PRD 第 5 章）：
    17 个基础字段（含参数 MOQ / MPQ）+ 6 个月份列（M1~M6＝各月计划数量，PRD 5.4.3 计算链终值）
    + 同步状态展示（后台定时任务自动同步，前台已移除所有手动同步入口）。顶部口径说明条已按用户要求移除，且不应残留 M7~M12 与 12 个月口径。
    详情弹窗须含「参数」区与计算实例完整表（指标为行、M1~M6 为列），由探针 probe_poreg_roll.mjs 校验。"""
    r = rendered(dump("po-roll"))
    base_cols = ["数据日期", "计划批次", "计划行", "供应商编码", "供应商名称", "配件号", "配件名称",
                 "车型", "MOQ", "MPQ", "计划数量", "采购LT(月)", "预测起始月份", "未来6个月合计",
                 "同步状态", "同步时间", "操作"]
    miss = [c for c in base_cols if not has_col(r, c)]
    month_miss = [("M%d" % i) for i in range(1, 7) if not has_col(r, "M%d" % i)]
    tab_miss = [t for t in ["全部", "未同步", "已同步SAP"] if t not in r]
    bad = []
    if "同步到 SAP" in r:
        bad.append("不应残留同步到SAP按钮")
    # 已移除：顶部口径说明条、12 个月列、发布状态口径
    if "滚动计划口径" in r:
        bad.append("顶部口径说明条未移除")
    if "未来12个月" in r or has_col(r, "M7"):
        bad.append("不应残留 12 个月口径")
    if "发布状态" in r or "供应商已确认" in r:
        bad.append("不应残留发布状态口径")
    if "重新同步" in r:
        bad.append("不应残留重新同步按钮")
    rows = r.count("ant-table-row")
    ok = not miss and not month_miss and not tab_miss and not bad and rows > 0
    detail = (f"基础列={len(base_cols)-len(miss)}/{len(base_cols)} 月份列={6-len(month_miss)}/6 "
              f"页签缺失={tab_miss if tab_miss else '无'} 行={rows} 异常={bad if bad else '无'} 列缺失={miss if miss else '无'}")
    return {"key": "po-roll", "ok": ok, "msg": detail}

def check_po_archive():
    """历史采购计划（po-history）+ 采购计划导出（po-export）两页渲染与口径校验。
    历史页：列表列须与采购计划全量一致（默认全量 57 数据列，仅去掉顶部状态tab，归档只读）；
    导出页：列集严格按 4.4.6.2 PO下单模板 11 列 + 导出状态/操作，含 仅 待导出 一个 tab（无「全部」「已导出」tab、无标记按钮），
            导出按钮名为「导出」，导出成功后自动打「已导出」标签（不再显示在页面中）。"""
    bad = []
    # ---- 历史采购计划 ----
    rh = rendered(dump("po-history"))
    if rh.count("ant-table-row") <= 0:
        bad.append("po-history(rows=0)")
    # 无顶部状态tab：归档页不应渲染 antd tabs 组件（审批状态页签）；单据状态仅作为数据列展示
    if "ant-tabs-tab" in rh or "ant-tabs-nav" in rh:
        bad.append("po-history(不应有状态tab)")
    for col in ["数据生成日期", "调整计划数量", "拦截原因", "配件号", "单据状态"]:
        if not has_col(rh, col):
            bad.append("po-history(缺列:" + col + ")")
    # 列须与采购计划全量一致：断言采购计划中「非首屏默认列」在历史页同样渲染（防只显示 11 列的回归）
    po_full_extra = ["推荐计划数量(凑MOQ后)", "推荐计划数量(凑联合MOQ后)", "推荐计划数量(凑MPQ后)",
                     "最低风控线", "预期库存数量", "近 3 个月月均销量", "修改人名称", "审批时间", "是否多供应商"]
    for col in po_full_extra:
        if not has_col(rh, col):
            bad.append("po-history(列未与采购计划全量一致,缺:" + col + ")")
    # 筛选区：默认 8 项可见，与采购计划（po-regular）完全一致（含当前采购件号 / 是否拦截 / 拦截原因）；
    # 车型代码 / ABC分类 / 采购类别 / 计划员 / 单据状态 / 计划批次 / 当前可用天数 收在「展开」折叠里
    fi = rh.find('<div class="filter-row"')
    fr = rh[fi:rh.find('<div class="toolbar-row"')] if fi >= 0 else ""
    vis = re.findall(r'class="f-label"[^>]*>([^<]+)<', fr)
    for need in ["配件号", "配件名称", "当前采购件号", "建储仓库编码", "建储仓库名称", "计划类型", "是否拦截", "拦截原因"]:
        if need not in vis:
            bad.append("po-history(筛选默认缺:" + need + ")")
    for hidden in ["车型代码", "ABC分类", "采购类别", "计划员", "单据状态", "计划批次", "当前可用天数"]:
        if hidden in vis:
            bad.append("po-history(" + hidden + "应收在展开折叠里)")
    if "展开" not in fr and "收起" not in fr:
        bad.append("po-history(缺展开/收起切换)")
    # 源码级：历史页筛选条件须与采购计划全量一致（v-model 绑定全部字段，含展开项）
    tpl = open(HTML, encoding="utf-8", errors="replace").read()
    for bind in ["poHistFilters.cur_purchase_code", "poHistFilters.is_blocked", "poHistFilters.block_reason",
                 "poHistFilters.purchase_type", "poHistFilters.planner", "poHistFilters.bill_status",
                 "poHistFilters.plan_batch", "poHistFilters.cover_days"]:
        if bind not in tpl:
            bad.append("po-history(筛选缺绑定:" + bind + ")")
    # 行操作：详情 + 变更记录（变更记录沿用采购计划同一套 PRD 4.4.3.2 口径）
    acts = re.findall(r'class="link-btn"[^>]*>([^<]*)<', rh)
    if "变更记录" not in [a.strip() for a in acts]:
        bad.append("po-history(缺变更记录入口)")
    # ---- 采购计划导出：列集严格按 4.4.6.2「PO下单模板」11 列 + 2 个页面控制列 ----
    re_ = rendered(dump("po-export"))
    if re_.count("ant-table-row") <= 0:
        bad.append("po-export(rows=0)")
    # 顶部 tab：仅 待导出（不应有「全部」「已导出」tab）
    for t in ["待导出"]:
        if t not in re_:
            bad.append("po-export(缺tab:" + t + ")")
    if "已导出" in re_:
        bad.append("po-export(不应有「已导出」tab)")
    if has_col(re_, "全部"):
        bad.append("po-export(不应有「全部」tab)")
    ehds = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", re_, re.S)]
    ehds = [h for h in ehds if h]  # 剔除勾选列的空表头
    tpl_cols = ["Order Type (Purchasing)", "供应商代码", "Purchasing Organization",
                "Purchasing Group", "Company Code", "计划批次", "计划行", "配件号", "订单数量",
                "Net Price in Purchasing Document (in Document Currency)", "Plant",
                "导出状态", "操作"]
    if ehds != tpl_cols:
        bad.append("po-export(列集/顺序与4.4.6.2模板不一致:" + " / ".join(ehds) + ")")
    # SAP 固定值须在单元格中带出
    for fixed in ["ZDFP", "CJV0", "CJLR", "CJDC"]:
        if fixed not in re_:
            bad.append("po-export(缺固定值:" + fixed + ")")
    # 查询条件须与 4.4.6.2 模板字段一致：4 个筛选标签 配件号/供应商代码/计划批次/计划行
    flabels = re.findall(r'class="f-label">([^<]*)</span>', re_)
    for fl in ["配件号", "供应商代码", "计划批次", "计划行"]:
        if fl not in flabels:
            bad.append("po-export(查询条件缺:" + fl + ")")
    # 模板外旧列不得残留（只查列头，避免命中筛选区同名标签）
    for col in ["数据生成日期", "计划类型", "配件名称", "当前采购件号", "当前采购配件名称",
                "建储仓库", "计划数量(最终计划)", "供应商名称", "起订量", "采购LT(天)", "要求到货日期",
                "推荐计划数量(凑MOQ后)", "推荐计划数量(凑联合MOQ后)", "推荐计划数量(凑成套采购后)",
                "推荐计划数量(凑MPQ后)", "审批意见", "调整原因", "最低风控线", "预期库存数量",
                "近 3 个月月均销量", "欠交数量", "库间在途数量", "缺货数量", "导出时间"]:
        if col in ehds:
            bad.append("po-export(不应出现模板外列:" + col + ")")
    # 无标记按钮 / 行内标记链接；导出按钮名为「导出」
    if "标记导出" in re_ or "标记已导出" in re_:
        bad.append("po-export(不应有标记导出按钮/链接)")
    # antd 两字按钮会自动插空格（"导 出"），用正则匹配；"导出状态"列头不会误命中
    if not re.search(r'>\s*导\s*出\s*<', re_):
        bad.append("po-export(缺「导出」按钮)")
    if bad:
        return {"ok": False, "msg": "异常: " + ", ".join(bad)}
    return {"ok": True, "msg": "2 页渲染正常（历史列与采购计划全量一致；导出页 13 列＝4.4.6.2 模板 11 列＋导出状态/操作，仅 待导出 1 个tab，导出即自动记录导出时间）"}

def check_po_export_template():
    """4.4.6.2 PO下单模板严格性：列表业务列与导出 CSV 表头为同一组 11 列，
       6 项 SAP 固定值由 constVal 带出，导出不受列设置影响。"""
    bad = []
    tpl = open(HTML, encoding="utf-8", errors="replace").read()
    heads = ["Order Type (Purchasing)", "供应商代码", "Purchasing Organization",
             "Purchasing Group", "Company Code", "计划批次", "计划行", "配件号", "订单数量",
             "Net Price in Purchasing Document (in Document Currency)", "Plant"]
    m = re.search(r'const poExpTemplateColumns = \[(.*?)\n    \];', tpl, re.S)
    if not m:
        bad.append("缺 poExpTemplateColumns 定义")
    else:
        body = m.group(1)
        for h in heads:
            if "title:'" + h + "'" not in body:
                bad.append("模板缺表头:" + h)
        if body.count("constVal") != 6:
            bad.append("固定值列数应为 6，实为 " + str(body.count("constVal")))
        for f in ["'ZDFP'", "'CJV0'", "'CJLR'", "'CJDC'"]:
            if f not in body:
                bad.append("缺固定值:" + f)
        if "导出状态" in body or "key:'action'" in body:
            bad.append("模板列中混入了页面控制列")
    # 导出 CSV 必须只用模板列，不得引用可见列（列设置不能影响 PO 模板）
    m2 = re.search(r'function poExpCsv\(rows\)\{(.*?)\n    \}', tpl, re.S)
    if not m2:
        bad.append("缺 poExpCsv")
    else:
        b2 = m2.group(1)
        if "poExpTemplateColumns" not in b2:
            bad.append("导出未使用模板 11 列")
        if "poExpVisibleColumns" in b2:
            bad.append("导出受列设置影响（仍引用 poExpVisibleColumns）")
        if "poExpVal(r, c)" not in b2:
            bad.append("导出未走 poExpVal（固定值可能丢失）")
    return {"ok": not bad,
            "msg": "正常（11 列表头 + 6 项固定值；CSV 严格模板列、不受列设置影响）" if not bad else "异常: " + ", ".join(bad)}

def check_sto_export_template():
    """6.4.2.2 STO下单模板严格性：列表业务列与导出 CSV 表头为同一组 10 列，
       4 项 SAP 固定值（Order Type=ZC、Purchasing Organization=CJV0/CN01、Purchasing Group=000、Company Code=CJLR/CN02）由 constVal 带出，
       导出不受列设置影响。其中 Order Type 为纯常量、Purchasing Organization/Company Code 为随发货仓切换的函数式 constVal。"""
    bad = []
    tpl = open(HTML, encoding="utf-8", errors="replace").read()
    heads = ["Order Type (Purchasing)", "发货仓", "Purchasing Organization", "Purchasing Group",
             "Company Code", "计划批次", "计划行", "配件号", "数量", "收货仓"]
    m = re.search(r'const stoExpTemplateColumns = \[(.*?)\n    \];', tpl, re.S)
    if not m:
        bad.append("缺 stoExpTemplateColumns 定义")
    else:
        body = m.group(1)
        for h in heads:
            if "title:'" + h + "'" not in body:
                bad.append("模板缺表头:" + h)
        # 4 个模板固定值列（Order Type=ZC / Purchasing Organization / Purchasing Group=000 / Company Code）
        # + 2 个仓库列用 constVal 箭头函数抽取 plant code（与模板示例 CJDC/CJV1 一致），共 6 处 constVal
        if body.count("constVal") != 6:
            bad.append("constVal 列数应为 6（4 模板固定值 + 2 仓库代码抽取），实为 " + str(body.count("constVal")))
        for f in ["'ZC'", "'000'", "stoExpOrgConst", "stoExpCompConst"]:
            if f not in body:
                bad.append("缺固定值/函数:" + f)
        # 发货仓/收货仓须用 constVal 箭头函数抽取纯 plant code（去除名称），与模板示例一致
        if body.count("constVal: r =>") != 2:
            bad.append("发货仓/收货仓须各用 constVal 箭头函数抽取 plant code")
        if "导出状态" in body or "key:'action'" in body:
            bad.append("模板列中混入了页面控制列")
    # 导出 CSV 必须只用模板列，不得引用可见列（列设置不能影响 STO 模板）
    m2 = re.search(r'function stoExpCsv\(rows\)\{(.*?)\n    \}', tpl, re.S)
    if not m2:
        bad.append("缺 stoExpCsv")
    else:
        b2 = m2.group(1)
        if "stoExpTemplateColumns" not in b2:
            bad.append("导出未使用模板 10 列")
        if "stoExpVisibleColumns" in b2:
            bad.append("导出受列设置影响（仍引用 stoExpVisibleColumns）")
        if "stoExpVal(r, c)" not in b2:
            bad.append("导出未走 stoExpVal（固定值可能丢失）")
    return {"ok": not bad,
            "msg": "正常（10 列表头 + 4 项固定值；CSV 严格模板列、不受列设置影响）" if not bad else "异常: " + ", ".join(bad)}

def check_warehouse_gb09():
    """仓网中心仓 JB09 → GB09 更名一致性校验。"""
    tpl = os.path.join(VENDOR_DIR, "template.html")
    wn = os.path.join(PROJECT_DIR, "前端设计稿", "warehouse-network.js")
    bad = []
    for label, path in (("template.html", tpl), ("warehouse-network.js", wn), ("成品HTML", HTML)):
        if not os.path.exists(path):
            bad.append(f"{label} 不存在")
            continue
        s = open(path, encoding="utf-8").read()
        if "JB09" in s:
            bad.append(f"{label} 仍残留 JB09（{s.count('JB09')} 处）")
        if "GB09" not in s:
            bad.append(f"{label} 未出现 GB09")
    return {"ok": not bad,
            "msg": "GB09 更名一致（JB09 零残留）" if not bad else "异常: " + ", ".join(bad)}

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    pages = [p for p in PAGES if (only is None or p[0]==only)]
    print("==== JLRS 主数据设计稿 逐页渲染校验 ====")
    all_ok = True
    for key, tk, fk, ext in pages:
        r = check_one(key, tk, fk, ext)
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] {key:14s} {r['msg']}")
    if only in (None, 'fc-buyout-btn', 'fc-buyout'):
        r = check_fc_buyout_btns()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-buyout-按钮  {r['msg']}")
    if only in (None, 'fc-long-btn', 'fc-long'):
        r = check_fc_long_btns()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-long-按钮   {r['msg']}")
    if only in (None, 'plan-hier-3'):
        r = check_plan_hier3()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] plan-hier-3   {r['msg']}")
    if only in (None, 'svc-dash'):
        r = check_svc_dash()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] svc-dash      {r['msg']}")
    if only in (None, 'fc-new'):
        r = check_fc_new()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-new        {r['msg']}")
    if only in (None, 'fc-new-pred'):
        r = check_fc_new_pred()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-new-pred   {r['msg']}")
    if only in (None, 'fc-new-coef'):
        r = check_fc_new_coef()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-new-系数   {r['msg']}")
    if only in (None, 'fc-new-6m', 'fc-new-12m', 'fc-new'):
        r = check_fc_new_6m()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-new-12个月  {r['msg']}")
    if only in (None, 'fc-new-reason', 'fc-new', 'fc-new-pred'):
        r = check_fc_new_pred_reason()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-new-调整原因 {r['msg']}")
    if only in (None, 'fc-regular', 'fc-trend'):
        r = check_fc_regular_trend()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-regular-趋势 {r['msg']}")
    if only in (None, 'fc-adjust'):
        r = check_fc_adjust()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-adjust     {r['msg']}")
    if only in (None, 'fc-fields'):
        r = check_fc_fields()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-fields     {r['msg']}")
    if only in (None, 'fc-long-coef', 'fc-long'):
        r = check_fc_long_coef()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-long-系数   {r['msg']}")
    if only in (None, 'fc-reg', 'fc-regular', 'fc-wh-regular', 'fc-long'):
        r = check_fc_regular_edit()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-regular-手工调整 {r['msg']}")
        r = check_fc_wh_regular()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-wh-regular    {r['msg']}")
        r = check_fc_long_trend()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-long-趋势图    {r['msg']}")
        r = check_fc_long_editmode()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-long-编辑态    {r['msg']}")
        r = check_fc_long_round()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-long-圆整策略  {r['msg']}")
        r = check_fc_long_import()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-long-批量圆整  {r['msg']}")
        r = check_fc_adjust_reason()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-调整原因    {r['msg']}")
        r = check_fc_trend_adj()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-趋势图-人工调整曲线 {r['msg']}")
    if only in (None, 'fc-reg', 'fc-regular', 'fc-reg-model'):
        r = check_fc_regular_model()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-regular-模型选择 {r['msg']}")
        r = check_fc_regular_model_switch()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-regular-模型切换 {r['msg']}")
    if only in (None, 'fc-backtest', 'fc-bt'):
        r = check_fc_backtest()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-backtest   {r['msg']}")
        r = check_fc_backtest_create()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-backtest-创建 {r['msg']}")
        r = check_fc_backtest_metric()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-backtest-指标 {r['msg']}")
        r = check_fc_backtest_dim_wh()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-backtest-配件+仓库 {r['msg']}")
        r = check_fc_backtest_dim_jxwh()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-backtest-经销商类型+配件+仓库 {r['msg']}")
        r = check_fc_backtest_dim_dlrtype()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-backtest-经销商类型+配件 {r['msg']}")
        r = check_fc_backtest_drill()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-backtest-趋势图 {r['msg']}")
        r = check_fc_backtest_parts()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-backtest-配件清单 {r['msg']}")
        r = check_fc_backtest_range()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-backtest-回测区间 {r['msg']}")
    if only in (None, 'gp'):
        r = check_gp_list()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] gp-list       {r['msg']}")
        r = check_gp_edit()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] gp-edit       {r['msg']}")
    if only in (None, 'inv-po', 'po'):
        r = check_po_pages()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] po-4pages     {r['msg']}")

    if only in (None, 'part-group', 'pg'):
        r = check_part_group()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] part-group   {r['msg']}")
    if only in (None, 'pg-no-max-months', 'po-no-max-months', 'part-group', 'pg'):
        r = check_pg_no_max_months()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] pg-无最大备货月数 {r['msg']}")
    if only in (None, 'po-no-max-months', 'pg-no-max-months', 'po'):
        r = check_po_no_max_months()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] po-无最大备货月数 {r['msg']}")
    if only in (None, 'ps-default', 'part-supplier', 'po'):
        r = check_ps_default()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] ps-编辑默认供应商 {r['msg']}")
    if only in (None, 'menu'):
        r = check_menu()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] menu          {r['msg']}")
    if only in (None, 'strategy'):
        r = check_strategy()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] strategy      {r['msg']}")
    if only in (None, 'sto', 'sto-week', 'sto-next'):
        r = check_sto()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] sto-2pages    {r['msg']}")
    if only in (None, 'sto-detail', 'sto', 'sto-week', 'sto-next'):
        r = check_sto_detail_no_remark()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] sto-详情弹窗无备注 {r['msg']}")
    if only in (None, 'sto', 'sto-summary'):
        r = check_sto_summary()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] sto-summary   {r['msg']}")
    if only in (None, 'sto', 'sto-export'):
        r = check_sto_export()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] sto-export    {r['msg']}")
    if only in (None, 'po-plan', 'po-atb', 'po-bridge', 'po-ref'):
        r = check_po_plan()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] po-plan-3pages {r['msg']}")
    if only in (None, 'atb-bridge-int', 'po-atb', 'po-bridge', 'po'):
        r = check_po_atb_bridge_integer()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] po-atb-bridge-整数校验 {r['msg']}")
    if only in (None, 'qty-col-order', 'po-plan', 'po'):
        r = check_qty_col_order()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] qty-列改名与调序 {r['msg']}")
    if only in (None, 'po-roll', 'po-plan'):
        r = check_po_roll()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] po-roll        {r['msg']}")
    if only in (None, 'po-archive', 'po-history', 'po-export'):
        r = check_po_archive()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] po-archive    {r['msg']}")
    if only in (None, 'po-export-template', 'po-export', 'po-archive'):
        r = check_po_export_template()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] po-exp-tpl    {r['msg']}")
    if only in (None, 'sto-export-template', 'sto-export', 'sto'):
        r = check_sto_export_template()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] sto-exp-tpl   {r['msg']}")
    if only in (None, 'po-regular-activity', 'po'):
        r = check_po_regular_activity()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] po-regular-活动零件 {r['msg']}")
    if only in (None, 'po-order', 'po-regular', 'po', 'create-plan'):
        r = check_po_order()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] po-regular-创建计划 {r['msg']}")
    if only in (None, 'po-create-plan', 'create-plan', 'po-order', 'po-regular', 'po'):
        r = check_po_create_plan()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] po-创建计划/备注联想 {r['msg']}")
    if only in (None, 'po-manual-order', 'po-order', 'po-regular', 'po'):
        r = check_po_manual_order()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] po-regular-手工下单 {r['msg']}")
    if only in (None, 'po-detail', 'po-regular', 'po-archive', 'po'):
        r = check_po_detail_layout()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] po-详情弹窗单块 {r['msg']}")
    if only in (None, 'po-edit-modal', 'po-regular', 'po'):
        r = check_po_edit_modal()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] po-调整弹窗两形态 {r['msg']}")
    if only in (None, 'activity-register'):
        r = check_activity_register()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] activity-register {r['msg']}")
    if only in (None, 'wh-gb09', 'warehouse', 'sto', 'sto-summary'):
        r = check_warehouse_gb09()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] 仓网-JB09→GB09 {r['msg']}")
    print("==== 汇总:", "全部通过" if all_ok else "存在失败", "====")

if __name__ == "__main__":
    main()
