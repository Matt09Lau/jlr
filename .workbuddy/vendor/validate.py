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
    ("plan-hier-2",  "计划层级管理2",      "管理计划组",     False),
    ("fc-long",      "长周期预测报表",     "3年预测",        False),
    ("fc-buyout",    "一次买断预测结果",   "All time buy",  False),
    ("fc-regular",   "常规预测",           "2026-10",        False),
    ("fc-best",      "最佳模型",           "最优模型",       False),
    ("part-group",      "配件组管理",        "分组类型",      False),
    ("po-regular",      "常规采购计划",      "计划单号",      False),
    ("po-eop",          "停产最后采购量",    "末采数量",      False),
    ("po-approval",     "采购计划审批",      "审批状态",      False),
    ("po-issue",        "采购订单下达",      "PO单号",        False),
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
        path = os.path.join(VENDOR_DIR, "_tmp_probe.html")
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
    """采购计划 4 个页面：每个页面都能正常挂载、渲染表格、包含关键业务字段。"""
    checks = [
        ("po-regular", "常规采购计划", "计划单号"),
        ("po-eop", "停产最后采购量", "末采数量"),
        ("po-approval", "采购计划审批", "审批状态"),
        ("po-issue", "采购订单下达", "PO单号"),
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
    return {"key":"po-4pages","ok":all_ok,"msg":' '.join(details)}

def check_fc_buyout_btns():
    """一次买断预测结果：默认展示态，工具栏含「编辑」「生成All time buy计划」；「生成bridge buy计划」已移至长周期预测报表，不应残留；亦不应有「生成采购计划」「保存」（保存仅在编辑态出现）。"""
    dump("fc-buyout")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-buyout-按钮","ok":False,"msg":"渲染失败/错误页"}
    r = strip_scripts(rendered(data))
    need = ["编 辑", "生成All time buy计划"]
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

def check_fc_buyout_draft_btns():
    """一次买断预测结果(草稿)：保留旧版「系数调整」「生成All time buy计划」，不应含「保存」。"""
    dump("fc-buyout-draft")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-buyout-draft-按钮","ok":False,"msg":"渲染失败/错误页"}
    r = strip_scripts(rendered(data))
    need = ["系数调整", "生成All time buy计划"]
    miss = [k for k in need if k not in r]
    bad = [k for k in ["保存", "生成采购计划", "生成bridge buy计划"] if k in r]
    ok = (not miss) and (not bad)
    detail = f"缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"fc-buyout-draft-按钮","ok":ok,"msg":detail}

def check_fc_long_draft_btns():
    """长周期预测报表(草稿)：保留旧版「系数调整」「生成bridge buy计划」，不应含「保存」。"""
    dump("fc-long-draft")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-long-draft-按钮","ok":False,"msg":"渲染失败/错误页"}
    r = strip_scripts(rendered(data))
    need = ["系数调整", "生成bridge buy计划"]
    miss = [k for k in need if k not in r]
    bad = [k for k in ["保存", "生成采购计划", "生成All time buy计划"] if k in r]
    ok = (not miss) and (not bad)
    detail = f"缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"fc-long-draft-按钮","ok":ok,"msg":detail}

def check_plan_hier():
    dump("plan-hier")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"plan-hier","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    watermark = r.count("Non-production system")
    tnodes = r.count('class="tnode"')
    kw = ["层级结构（计划员", "新增计划员", "新增计划组", "请选择左侧节点查看", "收起全部"]
    miss = [k for k in kw if k not in r]
    ok = watermark > 0 and tnodes > 0 and not miss
    detail = f"水印={watermark} tnode={tnodes} 缺失={miss if miss else '无'}"
    return {"key":"plan-hier","ok":ok,"msg":detail}

def check_plan_hier2():
    dump("plan-hier-2")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"plan-hier-2","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    watermark = r.count("Non-production system")
    rows = r.count("ant-table-row")
    kw = ["计划层级管理2", "计划员列表", "管理计划组"]
    miss = [k for k in kw if k not in r]
    ok = watermark > 0 and rows > 0 and not miss
    detail = f"水印={watermark} 表格行={rows} 缺失={miss if miss else '无'}"
    return {"key":"plan-hier-2","ok":ok,"msg":detail}

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
    """全新车型配件预测：左侧 7 步流程步骤条 + 右侧步骤1 参考车型库。"""
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
          "匹配参考订购率", "全新车型配件预测", "配件清单", "配件销量", "整车保有量",
          "订购率", "删除", "上市日期", "断点日期", "车型编号", "L460", "L663", "X761", "纯电"]
    miss = [k for k in kw if k not in r]
    ok = watermark > 0 and steps >= 7 and autos >= 5 and rows > 0 and not miss
    detail = f"水印={watermark} 步骤={steps} 自动标记={autos} 表格行={rows} 缺失={miss if miss else '无'}"
    return {"key":"fc-new","ok":ok,"msg":detail}

def check_fc_new_draft():
    """草稿副本：全新车型配件预测(草稿) 应正常渲染、且与原始一致（不应含新增的匹配状态/更新预测结果等控件）。"""
    dump("fc-new-draft")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-new-draft","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    watermark = r.count("Non-production system")
    steps = r.count("fc-step-no")
    rows = r.count("ant-table-row")
    has_new = ("匹配状态" in r) or ("更新预测结果" in r)
    kw = ["流程步骤", "添加参考车型", "导入参考车型", "维护参考车型库"]
    miss = [k for k in kw if k not in r]
    ok = watermark > 0 and steps >= 7 and rows > 0 and not has_new and not miss
    detail = f"水印={watermark} 步骤={steps} 表格行={rows} 含新控件={has_new} 缺失={miss if miss else '无'}"
    return {"key":"fc-new-draft","ok":ok,"msg":detail}

def check_fc_new_pred():
    """原始全新车型配件预测：预测结果弹窗含匹配状态筛选、批量维护参考配件号（逐行独立下拉 + 受约束模板导入并校验）；更新预测结果按钮已移除。"""
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
    has_base = has_col(full, 'base')
    no_lr = "左右标识" not in full
    no_upc = "UPC/FN号" not in full
    ok = (has_filter and not has_update and has_batch and has_tpl and has_import
          and has_valid_col and has_note and has_invalid and has_import_msg and has_jlr
          and has_base and no_lr and no_upc)
    detail = (f"匹配状态={has_filter} 更新按钮已移除={not has_update} 批量按钮={has_batch} 下载模板={has_tpl} "
              f"导入按钮={has_import} 校验列={has_valid_col} 说明={has_note} 越界标红={has_invalid} "
              f"导入提示={has_import_msg} JLR料号={has_jlr} "
              f"base={has_base} 无左右标识={no_lr} 无UPC/FN={no_upc}")
    return {"key":"fc-new-pred","ok":ok,"msg":detail}

def check_fc_new_6m():
    """全新车型配件预测：计划生产量应为未来 1~6 个月（列表列），预测结果应为 1~6 个月预测列。"""
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
        return {"key": "fc-new-6个月", "ok": False, "msg": "渲染失败/错误页"}
    m = re.search(r"ZZPROBE6M prod=(\d+) max=(\d+) fc=(\d+)", data)
    if not m:
        return {"key": "fc-new-6个月", "ok": False, "msg": "未取得探针"}
    prod, mx, fc = int(m.group(1)), int(m.group(2)), int(m.group(3))
    ok = prod == 6 and mx == 6 and fc == 6
    detail = f"计划生产量列={prod}(最大{mx}月) 预测结果列={fc}"
    return {"key": "fc-new-6个月", "ok": ok, "msg": detail}

def check_fc_new_coef():
    """全新车型预测：页面步骤7「系数调整」按钮 → 弹窗内维护 1~6 月系数。"""
    # 探针：进入步骤7 → 点击「系数调整」按钮后，统计弹窗内真实渲染的月份系数输入框
    inject = ("<script>"
              "setTimeout(function(){var steps=[].slice.call(document.querySelectorAll('.fc-step'));if(steps[6]){steps[6].click();}}, 900);"
              "setTimeout(function(){"
              "var bs=[].slice.call(document.querySelectorAll('.ant-btn')).filter(function(x){return x.textContent.indexOf('系数调整')>=0;});"
              "if(bs[0]){bs[0].click();}"
              "setTimeout(function(){"
              "var n=0,txt=0;"
              "[].slice.call(document.querySelectorAll('.ant-modal-content')).forEach(function(c){"
              "if(c.textContent.indexOf('预测系数调整（第 1 ~ 6 月）')>=0){txt++; n+=c.querySelectorAll('.ant-input-number').length;}});"
              "var d=document.createElement('div'); d.id='zzprobe'; d.textContent='ZZPROBE btn='+bs.length+' modalWithTxt='+txt+' inputs='+n; document.body.appendChild(d);"
              "}, 800);"
              "}, 1900);</script>")
    dump("fc-new-draft", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-new-系数","ok":False,"msg":"渲染失败/错误页"}
    m = re.search(r"ZZPROBE btn=(\d+) modalWithTxt=(\d+) inputs=(\d+)", data)
    if not m:
        return {"key":"fc-new-系数","ok":False,"msg":"未取得弹窗探针"}
    btn, mw, inp = int(m.group(1)), int(m.group(2)), int(m.group(3))
    ok = btn >= 1 and mw >= 1 and inp >= 6
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


def check_fc_regular_draft():
    """常规预测(草稿)：冻结变更前版本——含原布局（数据日期/配件号/调整原因），但不含新增的「模型策略」「查看预测结果」列。"""
    dump("fc-regular-draft")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-regular-draft","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    rows = r.count("ant-table-row")
    has_old = ("数据日期" in r) and ("配件号" in r) and ("调整原因" in r)
    bad = [k for k in ["模型策略", "查看预测结果"] if k in r]
    ok = rows > 0 and has_old and not bad
    detail = f"表格行={rows} 原布局={has_old} 新增列残留={bad if bad else '无'}"
    return {"key":"fc-regular-draft","ok":ok,"msg":detail}

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
    """长周期预测报表：数值策略（圆整）能力保留——页头圆整规则说明 + 「圆整视角」开关 + 「汇总值」列 + 「批量调整」按钮。"""
    dump("fc-long")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key": "fc-long-圆整策略", "ok": False, "msg": "渲染失败/错误页"}
    r = rendered(data)
    # 圆整按规则默认生效：保留说明文案与汇总值列，但不再需要「圆整视角」开关
    need = ["数值策略（长周期预测圆整规则）", "汇总值", "批量调整", "编 辑"]
    miss = [k for k in need if k not in r]
    bad = [k for k in ["圆整视角", "关闭圆整视图"] if k in r]
    rows = r.count("ant-table-row")
    ok = rows > 0 and not miss and not bad
    detail = f"表格行={rows} 缺失={miss if miss else '无'} 残留开关={bad if bad else '无'}"
    return {"key": "fc-long-圆整策略", "ok": ok, "msg": detail}


def check_fc_long_import():
    """长周期批量调整：勾选行后打开弹窗，应支持「已勾选行 / 导入配件号」两种调整范围（含粘贴框与导入文件按钮）。"""
    inject = ("<script>setTimeout(function(){"
              "var cb=document.querySelector('.ant-table-tbody .ant-checkbox-input');"
              "if(cb){cb.dispatchEvent(new MouseEvent('click',{bubbles:true}));}"
              "setTimeout(function(){"
              "var btns=[].slice.call(document.querySelectorAll('button'));"
              "var b=btns.find(function(x){var t=(x.textContent||'').replace(/\\s/g,'');return t.indexOf('批量调整')>=0;});"
              "if(b){b.dispatchEvent(new MouseEvent('click',{bubbles:true}));}"
              "}, 1200);}, 1800);</script>")
    dump("fc-long", inject=inject)
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key": "fc-long-批量导入", "ok": False, "msg": "渲染失败/错误页"}
    need = ["调整范围", "已勾选行（", "导入配件号", "导入文件", "策略名称", "稀疏件圆整策略"]
    miss = [k for k in need if k not in data]
    ok = not miss
    detail = f"缺失={miss if miss else '无'}"
    return {"key": "fc-long-批量导入", "ok": ok, "msg": detail}


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
    """全新车型预测 · 预测结果弹窗：含「调整原因」列（每行、调整后必填）。"""
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

def check_fc_backtest_draft():
    """预测回测配置（草稿）：保留修改前完整旧版。
    列表页（执行 / 指标 / 指标结果入口 + 草稿说明）→ 详情页（指标概览 / 异常分析 / 得分等级 / base / 执行回测）
    → 趋势图弹窗（偏差 e_i / 根因分析）。逐项进入对应视图后再断言，避免把详情/弹窗专属元素误判为缺失。"""
    # 1) 列表页
    dump("fc-backtest-draft")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"fc-backtest-草稿","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    list_kw = ["预测模拟(草稿)", "预测模拟（Backtest）", "执行", "指标", "执行 / 编辑 / 指标 / 删除"]
    list_miss = [k for k in list_kw if k not in r]
    # 2) 详情页：点行内「指标」进入结果页
    inject_detail = ("<script>setTimeout(function(){"
                     "var ls=[].slice.call(document.querySelectorAll('.link-btn'));"
                     "var pick=function(t){return ls.filter(function(x){return x.textContent.trim()===t;});};"
                     "var tgt=pick('指标')[0];"
                     "if(tgt){tgt.click();}}, 1500);</script>")
    dump("fc-backtest-draft", inject=inject_detail)
    d2 = open(DUMP, encoding="utf-8", errors="replace").read()
    rd = rendered(d2)
    detail_kw = ["回测任务指标结果", "指标概览", "异常分析", "得分等级",
                 "执行回测", "指标结果", "查看趋势图"]
    detail_miss = [k for k in detail_kw if k not in rd]
    if not has_col(rd, 'base'):
        detail_miss.append('base')
    # 3) 趋势图弹窗：详情页点「查看趋势图」
    inject_drill = ("<script>setTimeout(function(){"
                    "var ls=[].slice.call(document.querySelectorAll('.link-btn'));"
                    "var pick=function(t){return ls.filter(function(x){return x.textContent.trim()===t;});};"
                    "var tgt=pick('指标')[0];"
                    "if(tgt){tgt.click();}}, 1400);"
                    "setTimeout(function(){"
                    "var ds=[].slice.call(document.querySelectorAll('.link-btn')).filter(function(x){return x.textContent.trim()==='查看趋势图';});"
                    "if(ds[0]){ds[0].click();}}, 2600);</script>")
    dump("fc-backtest-draft", inject=inject_drill)
    d3 = open(DUMP, encoding="utf-8", errors="replace").read()
    clean3 = strip_scripts(d3)
    modal = 'id="btDrillChart"' in clean3
    drill_kw = ["偏差 e_i", "根因分析"]
    drill_miss = [k for k in drill_kw if k not in clean3]
    # 草稿不应出现「原页面」专属标题
    bad = [k for k in ["回测任务结果"] if k in r or k in rd]
    ok = (not list_miss) and (not detail_miss) and modal and (not drill_miss) and (not bad)
    detail = (f"列表缺失={list_miss if list_miss else '无'} "
              f"详情缺失={detail_miss if detail_miss else '无'} "
              f"弹窗={modal} 趋势图缺失={drill_miss if drill_miss else '无'} "
              f"新版残留={bad if bad else '无'}")
    return {"key":"fc-backtest-草稿","ok":ok,"msg":detail}

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
          "WAREHOUSE_WARNING_COEFFICIENT", "共 11 条"]
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
        "按钮-批量导入配件": "批量导入配件" in r,
    }
    missing = [k for k, v in must.items() if not v]
    ok = rows > 0 and not missing
    detail = f"rows={rows} " + ("缺失=" + ",".join(missing) if missing else "缺失=无")
    return {"key":"part-group","ok":ok,"msg":detail}

def check_menu():
    """校验左侧菜单结构：需求预测一级菜单及 5 个子页、草稿分组、计划层级管理更名与归组、占位菜单已移除。"""
    dump("wh-abc")
    data = open(DUMP, encoding="utf-8", errors="replace").read()
    if "ERR_FILE_NOT_FOUND" in data or "<title>file://" in data:
        return {"key":"menu","ok":False,"msg":"渲染失败/错误页"}
    r = rendered(data)
    # 期望出现
    must_have = ["需求预测", "预测模拟", "全新车型配件预测", "长周期预测报表", "一次买断预测结果", "常规预测", "仓库级常规预测", "最佳模型",
                 "草稿", "计划层级管理", "计划层级管理2", "服务水平dashboard", "基础数据管理",
                 "库存策略参数", "采购LT", "目标满足率", "备货规则", "库间LT", "增储天数", "计划周期", "配件风控线", "配件多分类风控线", "建储水位线计算结果",
                 "配件组管理",
                 "采购计划", "常规采购计划", "停产最后采购量", "采购计划审批", "采购订单下达"]
    miss = [k for k in must_have if k not in r]
    # 不应出现（已移除的纯占位菜单）
    must_not = ["历史需求处理", "准确率报表", "预测回测配置",
                "售后订单管理", "【本地测试页面】", "计划层级管理3"]
    bad = [k for k in must_not if k in r]
    ok = (not miss) and (not bad)
    detail = f"缺失={miss if miss else '无'} 残留={bad if bad else '无'}"
    return {"key":"menu","ok":ok,"msg":detail}

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    pages = [p for p in PAGES if (only is None or p[0]==only)]
    print("==== JLRS 主数据设计稿 逐页渲染校验 ====")
    all_ok = True
    for key, tk, fk, ext in pages:
        r = check_one(key, tk, fk, ext)
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] {key:14s} {r['msg']}")
    if only in (None, 'fc-buyout-btn', 'fc-buyout', 'fc-buyout-draft'):
        r = check_fc_buyout_btns()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-buyout-按钮  {r['msg']}")
    if only in (None, 'fc-buyout-draft', 'fc-buyout'):
        r = check_fc_buyout_draft_btns()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-buyout-draft-按钮  {r['msg']}")
    if only in (None, 'fc-long-btn', 'fc-long', 'fc-long-draft'):
        r = check_fc_long_btns()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-long-按钮   {r['msg']}")
    if only in (None, 'fc-long-draft', 'fc-long'):
        r = check_fc_long_draft_btns()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-long-draft-按钮   {r['msg']}")
    if only in (None, 'plan-hier'):
        r = check_plan_hier()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] plan-hier     {r['msg']}")
    if only in (None, 'plan-hier-2'):
        r = check_plan_hier2()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] plan-hier-2   {r['msg']}")
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
    if only in (None, 'fc-new-draft'):
        r = check_fc_new_draft()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-new-draft  {r['msg']}")
    if only in (None, 'fc-new-pred'):
        r = check_fc_new_pred()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-new-pred   {r['msg']}")
    if only in (None, 'fc-new-coef', 'fc-new-draft'):
        r = check_fc_new_coef()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-new-系数   {r['msg']}")
    if only in (None, 'fc-new-6m', 'fc-new'):
        r = check_fc_new_6m()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-new-6个月  {r['msg']}")
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
    if only in (None, 'fc-long-coef', 'fc-long-draft', 'fc-long'):
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
        print(f"[{'✓' if r['ok'] else '✗'}] fc-long-批量导入  {r['msg']}")
        r = check_fc_adjust_reason()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-调整原因    {r['msg']}")
        r = check_fc_trend_adj()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-趋势图-人工调整曲线 {r['msg']}")
    if only in (None, 'fc-reg', 'fc-regular', 'fc-regular-draft', 'fc-reg-model'):
        r = check_fc_regular_model()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-regular-模型选择 {r['msg']}")
        r = check_fc_regular_model_switch()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-regular-模型切换 {r['msg']}")
        r = check_fc_regular_draft()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-regular-草稿   {r['msg']}")
    if only in (None, 'fc-backtest', 'fc-bt'):
        r = check_fc_backtest()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-backtest   {r['msg']}")
        r = check_fc_backtest_draft()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-backtest-草稿 {r['msg']}")
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
    if only == 'fc-backtest-draft':
        r = check_fc_backtest_draft()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] fc-backtest-草稿 {r['msg']}")

    if only in (None, 'part-group', 'pg'):
        r = check_part_group()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] part-group   {r['msg']}")
    if only in (None, 'menu'):
        r = check_menu()
        all_ok = all_ok and r["ok"]
        print(f"[{'✓' if r['ok'] else '✗'}] menu          {r['msg']}")
    print("==== 汇总:", "全部通过" if all_ok else "存在失败", "====")

if __name__ == "__main__":
    main()
