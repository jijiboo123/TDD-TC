#!/usr/bin/env python3
"""两种报告，一个模块。

  render_test_report(...)  跑 pytest → 用例级 HTML（通过率、失败详情）
  render_scan_report(...)  体检结果 → 问题级 HTML（高危/中危/低危）

用法：
    python reports.py            # 跑测试并生成测试报告，然后打开
    python reports.py --scan .   # 体检某个目录并生成体检报告
"""

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

STATUS_COLOR = {"passed": "#2fb37a", "failed": "#d9534f", "skipped": "#b08d3e", "error": "#8e944d"}
SEVERITY_COLOR = {"高": "#d9534f", "中": "#e0a13c", "低": "#4c8dff"}

BASE_CSS = """
 :root { color-scheme: light dark; } * { box-sizing: border-box; }
 body { margin:0; padding:28px 32px; font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
        background:#f7f8fa; color:#1f2430; }
 @media (prefers-color-scheme: dark) { body { background:#15171c; color:#e6e9ef; } }
 h1 { font-size:20px; margin:0 0 4px; }
 .sub { font-size:12px; opacity:.6; margin-bottom:20px; }
 .cards { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:16px; }
 .card { flex:1 1 120px; background:rgba(128,128,128,.08); border:1px solid rgba(128,128,128,.25);
         border-radius:10px; padding:12px 14px; }
 .num { font-size:24px; font-weight:700; line-height:1.1; } .label { font-size:12px; opacity:.62; margin-top:4px; }
 .bar { display:flex; height:12px; border-radius:6px; overflow:hidden; background:rgba(128,128,128,.16); margin-bottom:20px; }
 table { width:100%; border-collapse:collapse; font-size:13px; }
 th,td { text-align:left; padding:8px 10px; border-bottom:1px solid rgba(128,128,128,.18); vertical-align:top; }
 th { font-size:12px; opacity:.6; }
 .tag { color:#fff; font-size:11px; padding:2px 7px; border-radius:999px; }
 .path { font-family:Consolas,monospace; font-size:12px; opacity:.85; white-space:nowrap; }
 .advice, .muted { opacity:.7; font-size:12px; }
 .dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }
 tr.group td { background:rgba(76,141,255,.10); font-weight:600; }
 pre { white-space:pre-wrap; font-size:12px; margin:8px 0 0; }
 .test { margin-top:18px; padding:12px 14px; border-radius:10px; font-size:13px; }
 .test.ok { background:rgba(47,179,122,.12); border:1px solid rgba(47,179,122,.4); }
 .test.warn { background:rgba(224,161,60,.12); border:1px solid rgba(224,161,60,.4); }
"""

# ---------------- 测试报告 ----------------

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

def _render_test_html(cases, summary, elapsed, pytest_output):
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

def _test_main():
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




# ---------------- 体检报告 ----------------

COLOR = SEVERITY_COLOR   # 体检报告沿用旧名字


def render_scan_report(findings, info, test_result, out_path):
    out_path = Path(out_path)
    total = max(len(findings), 1)
    counts = {level: sum(1 for x in findings if x.severity == level) for level in COLOR}

    cards = [
        ("高危", counts["高"], COLOR["高"]), ("中危", counts["中"], COLOR["中"]),
        ("低危", counts["低"], COLOR["低"]), ("扫描文件", info["python_files"], "#8b93a7"),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="num" style="color:{c}">{v}</div><div class="label">{l}</div></div>'
        for l, v, c in cards)
    bar = "".join(
        f'<div style="width:{counts[l] / total * 100:.2f}%;background:{COLOR[l]}"></div>'
        for l in ("高", "中", "低") if counts[l])

    rows = []
    for item in findings:
        detail = html.escape(item.detail)
        advice = html.escape(item.advice)
        rows.append(
            f'<tr><td><span class="tag" style="background:{COLOR[item.severity]}">{item.severity}</span></td>'
            f'<td class="path">{html.escape(item.path)}:{item.line}</td>'
            f'<td>{html.escape(item.kind)}</td><td>{detail}</td><td class="advice">{advice}</td></tr>')

    if test_result.get("ran"):
        test_html = (f'<div class="test ok"><b>项目自带测试</b>：{html.escape(test_result["summary"])}'
                     f'<pre>{html.escape(test_result.get("output", ""))}</pre></div>')
    else:
        test_html = (f'<div class="test warn"><b>项目自带测试未运行</b>：'
                     f'{html.escape(test_result.get("reason", ""))}</div>')

    page = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>软件体检报告 · {time.strftime('%Y-%m-%d %H:%M')}</title>
<style>
 :root {{ color-scheme: light dark; }} * {{ box-sizing: border-box; }}
 body {{ margin:0; padding:28px 32px; font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
        background:#f7f8fa; color:#1f2430; }}
 @media (prefers-color-scheme: dark) {{ body {{ background:#15171c; color:#e6e9ef; }} }}
 h1 {{ font-size:20px; margin:0 0 4px; }}
 .sub {{ font-size:12px; opacity:.6; margin-bottom:20px; }}
 .cards {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:16px; }}
 .card {{ flex:1 1 120px; background:rgba(128,128,128,.08); border:1px solid rgba(128,128,128,.25);
         border-radius:10px; padding:12px 14px; }}
 .num {{ font-size:24px; font-weight:700; }} .label {{ font-size:12px; opacity:.62; margin-top:4px; }}
 .bar {{ display:flex; height:12px; border-radius:6px; overflow:hidden; background:rgba(128,128,128,.16); margin-bottom:20px; }}
 table {{ width:100%; border-collapse:collapse; font-size:13px; }}
 th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid rgba(128,128,128,.18); vertical-align:top; }}
 th {{ font-size:12px; opacity:.6; }}
 .tag {{ color:#fff; font-size:11px; padding:2px 7px; border-radius:999px; }}
 .path {{ font-family:Consolas,monospace; font-size:12px; opacity:.85; white-space:nowrap; }}
 .advice {{ opacity:.75; font-size:12px; }}
 .test {{ margin-top:18px; padding:12px 14px; border-radius:10px; font-size:13px; }}
 .test.ok {{ background:rgba(47,179,122,.12); border:1px solid rgba(47,179,122,.4); }}
 .test.warn {{ background:rgba(224,161,60,.12); border:1px solid rgba(224,161,60,.4); }}
 pre {{ white-space:pre-wrap; font-size:12px; margin:8px 0 0; }}
</style></head><body>
<h1>软件体检报告</h1>
<div class="sub">扫描于 {time.strftime('%Y-%m-%d %H:%M:%S')} · 目录 {html.escape(info['root'])}</div>
<div class="cards">{cards_html}</div>
<div class="bar">{bar}</div>
<table><thead><tr><th>级别</th><th>位置</th><th>类型</th><th>问题</th><th>建议</th></tr></thead>
<tbody>{''.join(rows) or '<tr><td colspan="5">没有发现问题</td></tr>'}</tbody></table>
{test_html}
</body></html>"""
    out_path.write_text(page, encoding="utf-8")
    return out_path.resolve()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="测试报告 / 体检报告")
    parser.add_argument("--scan", help="体检这个目录，生成体检报告")
    parser.add_argument("--open", action="store_true", help="生成后用浏览器打开")
    options = parser.parse_args()

    if options.scan:
        import scanner
        findings, info, test_result = scanner.collect(options.scan)
        out = Path(options.scan).resolve() / "体检报告.html"
        render_scan_report(findings, info, test_result, out)
        print(f"体检报告: {out}")
        if options.open:
            webbrowser.open(out.as_uri())
        return 0

    code, elapsed, output = run_pytest([])
    cases, summary = parse_results()
    out = HERE / "report.html"
    out.write_text(_render_test_html(cases, summary, elapsed, output), encoding="utf-8")
    print(f"用例 {summary['total']} 个：通过 {summary['passed']}，失败 {summary['failed'] + summary['error']}，"
          f"耗时 {elapsed:.2f}s")
    print(f"测试报告: {out}")
    if options.open:
        webbrowser.open(out.as_uri())
    return code


if __name__ == "__main__":
    raise SystemExit(main())
