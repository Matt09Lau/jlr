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
