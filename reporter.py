"""把体检结果渲染成自包含 HTML（样式内联，不引 CDN）。"""

import html
import time
from pathlib import Path

COLOR = {"高": "#d9534f", "中": "#e0a13c", "低": "#4c8dff"}


def write_report(findings, info, test_result, out_path):
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