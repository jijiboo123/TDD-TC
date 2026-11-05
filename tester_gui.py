#!/usr/bin/env python3
"""软件测试可视化 · 主页面（图形界面）

打开后自动做三件事：
  1. 环境自检（Python / 依赖 / 浏览器 / Java），结果直接显示在顶部；
  2. 让你选择要检测的软件：整个文件夹，或者单个 .py 文件；
  3. 体检结果按级别列出来，可一键生成 HTML 报告。

用法：双击 `开始使用.bat`，或 python tester_gui.py
自检（不显示窗口）：python tester_gui.py --selftest
"""

import argparse
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import check_env
import reports as reporter
import scanner

ROOT = Path(__file__).resolve().parent
COLOR = {"高": "#d9534f", "中": "#e0a13c", "低": "#4c8dff", "ok": "#2e7d32", "warn": "#e0a13c", "bad": "#c62828"}


class App:
    def __init__(self, root):
        self.root = root
        self.findings = []
        self.info = {}
        self.test_result = {}

        root.title("软件测试可视化 · 主页面")
        root.geometry("1180x760")
        root.minsize(960, 640)

        self.target = tk.StringVar(value="")
        self.subproject = tk.StringVar(value="（当前目录）")
        self.status = tk.StringVar(value="选一个文件夹或源码文件，点「开始体检」")
        self.env_text = tk.StringVar(value="正在检测环境…")

        self._build_header()
        self._build_env()
        self._build_target()
        self._build_support()
        self._build_table()
        self._build_bottom()

        self.root.after(150, self.check_env_async)

    # ---------------- 界面 ----------------
    def _build_header(self):
        bar = ttk.Frame(self.root, padding=(14, 12, 14, 4))
        bar.pack(fill="x")
        ttk.Label(bar, text="软件测试可视化", font=("Microsoft YaHei", 16, "bold")).pack(side="left")
        ttk.Label(bar, text="  环境自检 → 选被测项目 → 开始体检", foreground="#6b7280").pack(side="left")

    def _build_env(self):
        box = ttk.LabelFrame(self.root, text=" 环境状态 ", padding=(10, 6))
        box.pack(fill="x", padx=14, pady=6)
        self.env_label = ttk.Label(box, textvariable=self.env_text, foreground="#6b7280")
        self.env_label.pack(side="left", fill="x", expand=True)
        ttk.Button(box, text="重新检测", command=self.check_env_async).pack(side="right")

    def _build_target(self):
        box = ttk.LabelFrame(self.root, text=" 被测项目 ", padding=(10, 8))
        box.pack(fill="x", padx=14, pady=6)
        row = ttk.Frame(box)
        row.pack(fill="x")
        ttk.Label(row, text="路径").pack(side="left")
        ttk.Entry(row, textvariable=self.target).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(row, text="选文件夹…", command=self.pick_folder).pack(side="left")
        ttk.Button(row, text="选源码文件…", command=self.pick_file).pack(side="left", padx=4)
        self.btn_scan = ttk.Button(row, text="开始体检", command=self.start)
        self.btn_scan.pack(side="left", padx=8)
        self.run_tests = tk.BooleanVar(value=True)
        ttk.Checkbutton(row, text="同时跑项目自带测试", variable=self.run_tests).pack(side="left")

        row2 = ttk.Frame(box)
        row2.pack(fill="x", pady=(6, 0))
        ttk.Label(row2, text="子项目").pack(side="left")
        self.sub_box = ttk.Combobox(row2, textvariable=self.subproject, state="disabled", width=42)
        self.sub_box.pack(side="left", padx=6)
        ttk.Label(row2, text="（选到工作区目录时，在这里挑具体项目）", foreground="#6b7280").pack(side="left")

    def _build_support(self):
        box = ttk.LabelFrame(self.root, text=" 能检测哪些文件 ", padding=(10, 6))
        box.pack(fill="x", padx=14, pady=4)
        for name, detail in scanner.SUPPORTED.items():
            line = ttk.Frame(box)
            line.pack(fill="x", anchor="w")
            ttk.Label(line, text=f"✓ {name}", foreground=COLOR["ok"], width=22).pack(side="left", padx=(0, 8))
            ttk.Label(line, text=detail, foreground="#4b5563", wraplength=880, justify="left").pack(side="left", fill="x")
        ttk.Label(box, text=f"注：{scanner.UNSUPPORTED}", foreground="#9ca3af").pack(anchor="w", pady=(4, 0))

    def _build_table(self):
        box = ttk.Frame(self.root, padding=(14, 4, 14, 0))
        box.pack(fill="both", expand=True)
        cols = (("sev", "级别", 60), ("loc", "位置", 250), ("kind", "类型", 130),
                ("detail", "问题", 380), ("advice", "建议", 380))
        self.tree = ttk.Treeview(box, columns=[c[0] for c in cols], show="headings", height=14)
        for key, title, width in cols:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w")
        for level, color in COLOR.items():
            if level in ("高", "中", "低"):
                self.tree.tag_configure(level, foreground=color)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<Double-1>", self.open_file)

    def _build_bottom(self):
        bar = ttk.Frame(self.root, padding=(14, 8, 14, 12))
        bar.pack(fill="x")
        ttk.Label(bar, textvariable=self.status, foreground="#2c3e50").pack(side="left")
        ttk.Button(bar, text="生成 HTML 报告", command=self.make_report).pack(side="right")
        ttk.Button(bar, text="打开控制台菜单", command=self.open_console_menu).pack(side="right", padx=6)

    # ---------------- 环境自检 ----------------
    def check_env_async(self):
        self.env_text.set("正在检测环境…")
        self.env_label.configure(foreground="#6b7280")
        threading.Thread(target=self._env_worker, daemon=True).start()

    def _env_worker(self):
        try:
            status = check_env.collect_status()
        except Exception as error:          # 界面不能因为自检崩溃
            self.root.after(0, lambda err=error: self._env_failed(err))
            return
        self.root.after(0, lambda data=status: self._env_done(data))

    def _env_failed(self, error):
        self.env_text.set(f"环境自检失败：{error}")
        self.env_label.configure(foreground=COLOR["bad"])

    def _env_done(self, status):
        parts = [
            f"Python {status['python']} {'✓' if status['python_ok'] else '✗'}",
            f"pytest {'✓' if status['modules']['pytest'] else '✗'}",
            f"UI {'✓' if status['modules']['playwright'] and status['chromium'] else '✗'}",
            f"Allure {'✓' if status['java_ok'] and status['allure'] else '✗'}",
        ]
        if status["problems"]:
            mark = "⚠ " if status["core_ok"] else "✗ "
            text = mark + " · ".join(parts) + "  —— " + "；".join(status["problems"])
            self.env_label.configure(foreground=COLOR["warn"] if status["core_ok"] else COLOR["bad"])
        else:
            text = " · ".join(parts) + "  —— 全部就绪"
            self.env_label.configure(foreground=COLOR["ok"])
        self.env_text.set(text)

    # ---------------- 选目标 / 体检 ----------------
    def pick_folder(self):
        chosen = filedialog.askdirectory(title="选择要体检的软件文件夹")
        if chosen:
            self.target.set(chosen)
            self.refresh_subprojects()

    def pick_file(self):
        chosen = filedialog.askopenfilename(
            title="选择要体检的源码文件",
            filetypes=[
                ("支持的类型", "*.py *.java *.js *.jsx *.ts *.tsx *.go"),
                ("Python", "*.py"),
                ("Java", "*.java"),
                ("JavaScript / TypeScript", "*.js *.jsx *.ts *.tsx"),
                ("Go", "*.go"),
                ("所有文件", "*.*"),
            ],
        )
        if chosen:
            self.target.set(chosen)
            self.refresh_subprojects()

    def refresh_subprojects(self):
        """选到工作区（一层里有多个项目）时，列出子项目让用户挑，而不是替他乱跑。"""
        base = Path(self.target.get().strip())
        found = scanner.list_sub_projects(base) if base.is_dir() else []
        if found:
            self.sub_box.configure(state="readonly")
            self.sub_box["values"] = ["（请选择子项目）", *found]
            self.subproject.set("（请选择子项目）")
        else:
            self.sub_box.configure(state="disabled")
            self.sub_box["values"] = []
            self.subproject.set("（当前目录）")

    def resolve_target(self):
        """返回真正要扫的路径：选了子项目就用子项目。"""
        base = Path(self.target.get().strip())
        chosen = self.subproject.get()
        if base.is_dir() and chosen not in ("（当前目录）", "（请选择子项目）", ""):
            return base / chosen
        return base

    def start(self):
        target = self.target.get().strip()
        if not target:
            messagebox.showinfo("还没选目标", "先选一个文件夹或源码文件。")
            return
        path = Path(target)
        if not path.exists():
            messagebox.showerror("路径不存在", target)
            return
        allowed = {".py", *scanner.TEXT_LANGUAGES}
        if path.is_file() and path.suffix.lower() not in allowed:
            messagebox.showerror("暂不支持", f"{path.suffix or '无后缀'} 暂不支持，可扫描：{', '.join(sorted(allowed))}")
            return
        if path.is_dir():
            subs = scanner.list_sub_projects(path)
            chosen = self.subproject.get()
            if subs and chosen not in subs and self.run_tests.get():
                messagebox.showwarning(
                    "这是工作区，不是单个项目",
                    f"这个目录下有 {len(subs)} 个独立项目：\n" + "\n".join(f"  · {name}" for name in subs[:8])
                    + "\n\n请在上方「子项目」里选一个再体检；\n"
                      "只想做静态检查、不跑测试的话，取消勾选「同时跑项目自带测试」。",
                )
                return
        scan_target = self.resolve_target()
        self.btn_scan.config(state="disabled")
        self.status.set(f"正在扫描 {scan_target} …")
        threading.Thread(target=self._scan_worker, args=(str(scan_target), self.run_tests.get()), daemon=True).start()

    def _scan_worker(self, target, with_tests):
        try:
            findings, info, test_result = scanner.collect(target, with_tests=with_tests)
            self.root.after(0, lambda: self._show(findings, info, test_result))
        except Exception as error:           # 坏项目不能把界面带崩
            self.root.after(0, lambda err=error: self._fail(err))

    def _fail(self, error):
        self.btn_scan.config(state="normal")
        self.status.set(f"扫描失败：{error}")

    def _show(self, findings, info, test_result):
        self.findings, self.info, self.test_result = findings, info, test_result
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in findings:
            self.tree.insert("", "end", values=(
                item.severity, f"{item.path}:{item.line}", item.kind, item.detail, item.advice,
            ), tags=(item.severity,))
        counts = {level: sum(1 for x in findings if x.severity == level) for level in ("高", "中", "低")}
        if info.get("target_file"):
            scope = f"单文件 {info['target_file']}"
        else:
            scope = f"{info['python_files']} 个 Python 文件"
            if info.get("other_files"):
                scope += f" + {info['other_files']} 个其他源码"
        if test_result.get("skipped_workspace"):
            test_note = " · 自带测试：已跳过（这是工作区，请在上面选具体子项目）"
        elif test_result.get("collection_failed"):
            test_note = " · 自带测试：无法收集（多半缺依赖或目录选太大）"
        elif test_result.get("ran"):
            test_note = f" · 自带测试：{test_result['summary']}"
        else:
            test_note = f" · 自带测试未运行（{test_result.get('reason', '未选择')}）"
        if info.get("multi_project"):
            test_note += f" · 注意：这个目录下有 {info['sub_projects']} 个独立项目，建议选具体项目子目录"
        self.status.set(f"已扫描 {scope} · 高危 {counts['高']} / 中危 {counts['中']} / 低危 {counts['低']}{test_note}")
        self.btn_scan.config(state="normal")

    # ---------------- 结果操作 ----------------
    def open_file(self, _event=None):
        picked = self.tree.selection()
        if not picked:
            return
        location = self.tree.item(picked[0], "values")[1]
        path_text = location.rsplit(":", 1)[0]
        full = Path(self.info.get("root", "")) / path_text
        if full.exists():
            import os
            os.startfile(full)      # noqa: S606 - 用户主动双击，打开源文件
        else:
            messagebox.showinfo("找不到文件", str(full))

    def make_report(self):
        if not self.info:
            messagebox.showinfo("还没扫描", "先点「开始体检」。")
            return
        target_dir = Path(self.info["root"]) if self.info.get("target_file") else Path(self.info["root"])
        path = reporter.render_scan_report(self.findings, self.info, self.test_result, target_dir / "体检报告.html")
        webbrowser.open(path.as_uri())
        self.status.set(f"报告已生成并打开：{path}")

    def open_console_menu(self):
        subprocess.Popen([sys.executable, "start_menu.py"], cwd=ROOT,
                         creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))


def main():
    parser = argparse.ArgumentParser(description="软件测试可视化 · 主页面")
    parser.add_argument("--selftest", action="store_true", help="只建窗口并在 1 秒后关闭，用于验证界面能启动")
    args = parser.parse_args()

    root = tk.Tk()
    App(root)
    if args.selftest:
        root.after(1000, root.destroy)
        root.mainloop()
        print("gui ok")
        return 0
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
