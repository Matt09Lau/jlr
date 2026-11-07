#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 template.html 中的 __VENDOR_*__ 占位符替换为本地 vendor 库，
生成可直接双击打开的离线单文件 HTML 到 前端设计稿/ 目录。
"""
import os
import sys

VENDOR_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(VENDOR_DIR))  # D:\数策\捷豹路虎项目
TEMPLATE = os.path.join(VENDOR_DIR, "template.html")
OUT_DIR = os.path.join(PROJECT_DIR, "前端设计稿")
OUT_FILE = os.path.join(OUT_DIR, "JLR_主数据前端设计稿.html")

PLACEHOLDERS = {
    "__VENDOR_RESET__": "reset.css",
    "__VENDOR_DAYJS__": "dayjs.min.js",
    "__VENDOR_P_CPF__": "p-cpf.js",
    "__VENDOR_P_WEEKDAY__": "p-weekday.js",
    "__VENDOR_P_LOCALE__": "p-locale.js",
    "__VENDOR_P_WOY__": "p-woy.js",
    "__VENDOR_P_WY__": "p-wy.js",
    "__VENDOR_P_AF__": "p-af.js",
    "__VENDOR_P_QOY__": "p-qoy.js",
    "__VENDOR_VUE__": "vue.global.prod.js",
    "__VENDOR_ANTD__": "antd.min.js",
    "__VENDOR_ECHARTS__": "echarts.min.js",
}


def main():
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        html = f.read()

    for ph, fname in PLACEHOLDERS.items():
        path = os.path.join(VENDOR_DIR, fname)
        if not os.path.exists(path):
            print("MISSING vendor file:", path, file=sys.stderr)
            sys.exit(1)
        with open(path, "r", encoding="utf-8") as vf:
            content = vf.read()
        # 避免内联 JS 中的 </script> 提前关闭脚本（保险措施）
        if fname.endswith(".js"):
            content = content.replace("</script", "<\\/script")
        if ph not in html:
            print("WARN placeholder not found:", ph, file=sys.stderr)
            continue
        html = html.replace(ph, content)

    # 草稿模块注入：本地存在 fragment 片段且未被环境变量关闭时注入到锚点；
    # 否则（git 仓库无 fragment，或显式 JLR_DRAFT=off）仅保留空注释占位，保证 git 成品无草稿。
    # 提交无草稿版：JLR_DRAFT=off python3 assemble.py  （即使 fragment 存在也跳过注入）
    fragment_path = os.path.join(VENDOR_DIR, "draft-script.fragment.js")
    anchor = "/* DRAFT_INJECT_SCRIPT */"
    draft_on = os.environ.get("JLR_DRAFT", "on").lower() not in ("0", "off", "false", "no")
    if draft_on and os.path.exists(fragment_path):
        with open(fragment_path, "r", encoding="utf-8") as ff:
            fragment_js = ff.read()
        if anchor in html:
            html = html.replace(anchor, fragment_js, 1)
        else:
            print("WARN anchor not found:", anchor, file=sys.stderr)
    else:
        # git 仓库场景：无 fragment 文件，或显式关闭草稿 → 仅保留空注释占位
        html = html.replace(anchor, "/* no draft module */", 1)

    # 草稿「可交互页面」注入：模板片段 + setup 末尾脚本片段。
    # 两个文件与 draft-script.fragment.js 一样只在本地存在且被 .gitignore 忽略；
    # JLR_DRAFT=off 或文件缺失时锚点替换为空注释，git 成品不含任何草稿页面代码。
    draft_tpl_path = os.path.join(VENDOR_DIR, "draft-activity-register.fragment.html")
    draft_js_path = os.path.join(VENDOR_DIR, "draft-activity-register.fragment.js")
    tpl_anchor = "<!-- DRAFT_INJECT_TEMPLATE -->"
    late_anchor = "/* DRAFT_INJECT_SCRIPT_LATE */"
    if draft_on and os.path.exists(draft_tpl_path) and os.path.exists(draft_js_path):
        with open(draft_tpl_path, "r", encoding="utf-8") as tf:
            html = html.replace(tpl_anchor, tf.read(), 1)
        with open(draft_js_path, "r", encoding="utf-8") as jf:
            html = html.replace(late_anchor, jf.read(), 1)
    else:
        html = html.replace(tpl_anchor, "<!-- no draft page -->", 1)
        html = html.replace(late_anchor, "/* no draft page script */", 1)

    # 检查是否还有未替换的占位符
    leftover = [p for p in PLACEHOLDERS if p in html]
    if leftover:
        print("WARN unresolved placeholders:", leftover, file=sys.stderr)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    size_mb = os.path.getsize(OUT_FILE) / 1024 / 1024
    print("OK generated:", OUT_FILE, "%.2f MB" % size_mb)


if __name__ == "__main__":
    main()
