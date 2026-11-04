#!/usr/bin/env python3
"""跑测试并生成一个自包含的 HTML 报告（不依赖 allure / pytest-html / Java）。

做法只有三步：
  1. 用 --junitxml 让 pytest 输出机器可读的结果
  2. 解析那份 XML
  3. 拼一个纯静态 HTML（样式内联、图表用 div 画，不引任何 CDN）

用法：
    python report.py                # 跑全部测试并生成 report.html
    python report.py --open         # 生成后自动用浏览器打开
    python report.py -k validation  # 只跑名字匹配的用例
"""

import argparse
import html
import subprocess
import sys
import time
import webbrowser
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
XML_OUT = HERE / "report.xml"
HTML_OUT = HERE / "report.html"

STATUS_COLOR = {"passed": "#2fb37a", "failed": "#d9534f", "skipped": "#b08d3e", "error": "#8e44ad"}


def run_pytest(extra_args):
    """跑 pytest，返回 (退出码, 耗时秒)"""
    command = [sys.executable, "-m", "pytest", f"--junitxml={XML_OUT}", "-q"]
    command += extra_args
    started = time.time()
    process = subprocess.run(command, cwd=HERE, capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
    return process.returncode, time.time() - started, process.stdout


def parse_results():
    """解析 junit xml → (用例列表, 汇总)"""
    if not XML_OUT.exists():
        raise SystemExit("没有生成 report.xml，pytest 可能没跑起来")
    tree = ET.parse(XML_OUT)
    cases = []
    for testcase in tree.iter("testcase"):
        status = "passed"
        detail = ""
        for child in testcase:
            if child.tag == "failure":
                status = "failed"
                detail = (child.get("message") or "") + "\n" + (child.text or "")
            elif child.tag == "error":
                status = "error"
                detail = (child.get("message") or "") + "\n" + (child.text or "")
            elif child.tag == "skipped":
                status = "skipped"
                detail = child.get("message") or ""
        cases.append({
            "module": testcase.get("classname") or "",
            "name": testcase.get("name") or "",
            "time": float(testcase.get("time") or 0),
            "status": status,
            "detail": detail.strip()[:1200],
        })
    summary = defaultdict(int)
    for case in cases:
        summary[case["status"]] += 1
    summary["total"] = len(cases)
    return cases, summary

def render_html(cases, summary, elapsed, pytest_output):
    total = max(summary["total"], 1)
    passed = summary["passed"]
    rate = passed / total * 100

    # 按模块分组
    groups = defaultdict(list)
    for case in cases:
        module = case["module"].split(".")[-1] or "(未分组)"
        groups[module].append(case)

    bars = "".join(
        f'<div class="bar-seg" style="width:{summary[key] / total * 100:.2f}%;background:{STATUS_COLOR[key]}" '
        f'title="{key}: {summary[key]}"></div>'
        for key in ("passed", "failed", "error", "skipped") if summary[key]
    )

    cards = [
        ("用例总数", summary["total"], "#4c8dff"),
        ("通过", passed, STATUS_COLOR["passed"]),
        ("失败", summary["failed"] + summary["error"], STATUS_COLOR["failed"]),
        ("跳过", summary["skipped"], STATUS_COLOR["skipped"]),
        ("通过率", f"{rate:.1f}%", "#4c8dff"),
        ("总耗时", f"{elapsed:.2f}s", "#8b93a7"),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="num" style="color:{color}">{value}</div>'
        f'<div class="label">{label}</div></div>'
        for label, value, color in cards
    )

    rows = []
    for module in sorted(groups):
        module_cases = groups[module]
        ok = sum(1 for c in module_cases if c["status"] == "passed")
        rows.append(
            f'<tr class="group"><td colspan="4">{html.escape(module)}'
            f'<span class="muted"> · {ok}/{len(module_cases)} 通过 · '
            f'{sum(c["time"] for c in module_cases):.2f}s</span></td></tr>'
        )
        for case in module_cases:
            color = STATUS_COLOR[case["status"]]
            detail = ""
            if case["detail"]:
                detail = f'<details><summary>查看失败信息</summary><pre>{html.escape(case["detail"])}</pre></details>'
            rows.append(
                f'<tr><td><span class="dot" style="background:{color}"></span>'
                f'{html.escape(case["name"])}</td>'
                f'<td style="color:{color}">{case["status"]}</td>'
                f'<td class="muted">{case["time"]:.3f}s</td>'
                f'<td>{detail}</td></tr>'
            )

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>接口自动化测试报告 · {time.strftime('%Y-%m-%d %H:%M:%S')}</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; padding:28px 32px; font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
         background:#f7f8fa; color:#1f2430; }}
  @media (prefers-color-scheme: dark) {{ body {{ background:#15171c; color:#e6e9ef; }} }}
  h1 {{ font-size:20px; margin:0 0 4px; }}
  .sub {{ font-size:12px; opacity:.6; margin-bottom:22px; }}
  .cards {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:22px; }}
  .card {{ flex:1 1 130px; background:rgba(128,128,128,.08); border:1px solid rgba(128,128,128,.25);
           border-radius:10px; padding:12px 14px; }}
  .num {{ font-size:24px; font-weight:700; line-height:1.1; }}
  .label {{ font-size:12px; opacity:.62; margin-top:4px; }}
  .bar {{ display:flex; height:12px; border-radius:6px; overflow:hidden; background:rgba(128,128,128,.16);
          margin-bottom:24px; }}
  .bar-seg {{ height:100%; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid rgba(128,128,128,.18); vertical-align:top; }}
  th {{ font-size:12px; opacity:.6; font-weight:600; }}
  tr.group td {{ background:rgba(76,141,255,.10); font-weight:600; }}
  .muted {{ opacity:.6; font-weight:400; }}
  .dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }}
  pre {{ white-space:pre-wrap; font-size:12px; background:rgba(128,128,128,.10);
         padding:8px; border-radius:6px; margin:6px 0 0; }}
  details summary {{ cursor:pointer; font-size:12px; opacity:.7; }}
</style></head><body>
<h1>接口自动化测试报告</h1>
<div class="sub">生成于 {time.strftime('%Y-%m-%d %H:%M:%S')} · pytest + requests · 被测服务由 mock_server.py 提供</div>
<div class="cards">{cards_html}</div>
<div class="bar">{bars}</div>
<table>
  <thead><tr><th>用例</th><th>结果</th><th>耗时</th><th>失败信息</th></tr></thead>
  <tbody>{''.join(rows)}</tbody>
</table>
<details style="margin-top:18px"><summary>pytest 原始输出</summary>
<pre>{html.escape(pytest_output[-4000:])}</pre></details>
</body></html>"""

def main():
    parser = argparse.ArgumentParser(description="生成可视化测试报告")
    parser.add_argument("--open", action="store_true", help="生成后用浏览器打开")
    parser.add_argument("args", nargs="*", help="透传给 pytest 的参数，例如 -k validation")
    options = parser.parse_args()

    code, elapsed, output = run_pytest(options.args)
    cases, summary = parse_results()
    HTML_OUT.write_text(render_html(cases, summary, elapsed, output), encoding="utf-8")

    print(f"用例 {summary['total']} 个：通过 {summary['passed']}，失败 {summary['failed'] + summary['error']}，"
          f"跳过 {summary['skipped']}，耗时 {elapsed:.2f}s")
    print(f"报告已生成：{HTML_OUT}")

    if options.open:
        webbrowser.open(HTML_OUT.as_uri())
        print("已在浏览器中打开")
    return code


if __name__ == "__main__":
    raise SystemExit(main())