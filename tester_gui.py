#!/usr/bin/env python3
"""软件体检器 · 图形界面

用法：双击运行（或 python tester_gui.py），选一个软件文件夹，点「开始体检」。
"""

import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import reports as reporter
import scanner

COLOR = {"高": "#d9534f", "中": "#e0a13c", "低": "#4c8dff"}


class App:
    def __init__(self, root):
        self.root = root
        self.findings = []
        self.info = {}
        self.test_result = {}
        root.title("软件体检器 · 选一个文件夹就能查 bug")
        root.geometry("1120x720")
        root.minsize(900, 600)

        self.folder = tk.StringVar(value="")
        self.status = tk.StringVar(value="选择一个软件文件夹，然后点「开始体检」")

        self._build_top()
        self._build_table()
        self._build_bottom()

    def _build_top(self):
        bar = ttk.Frame(self.root, padding=(12, 12, 12, 6))
        bar.pack(fill="x")
        ttk.Label(bar, text="软件文件夹").pack(side="left")
        ttk.Entry(bar, textvariable=self.folder, width=62).pack(side="left", padx=6)
        ttk.Button(bar, text="浏览…", command=self.pick).pack(side="left")
        self.btn_scan = ttk.Button(bar, text="开始体检", command=self.start)
        self.btn_scan.pack(side="left", padx=8)
        self.run_tests = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="同时跑项目自带测试",
                        variable=self.run_tests).pack(side="left", padx=6)

    def _build_table(self):
        box = ttk.Frame(self.root, padding=(12, 0, 12, 0))
        box.pack(fill="both", expand=True)
        cols = (("sev", "级别", 60), ("loc", "位置", 240), ("kind", "类型", 130),
                ("detail", "问题", 380), ("advice", "建议", 380))
        self.tree = ttk.Treeview(box, columns=[c[0] for c in cols], show="headings", height=18)
        for key, title, width in cols:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w")
        for level, color in COLOR.items():
            self.tree.tag_configure(level, foreground=color)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<Double-1>", self.open_file)

    def _build_bottom(self):
        bar = ttk.Frame(self.root, padding=(12, 8, 12, 12))
        bar.pack(fill="x")
        self.stats = ttk.Label(bar, textvariable=self.status, foreground="#2c3e50")
        self.stats.pack(side="left")
        ttk.Button(bar, text="生成 HTML 报告", command=self.make_report).pack(side="right")
    # ---------- 交互 ----------
    def pick(self):
        chosen = filedialog.askdirectory(title="选择要体检的软件文件夹")
        if chosen:
            self.folder.set(chosen)

    def start(self):
        target = self.folder.get().strip()
        if not target:
            messagebox.showinfo("还没选文件夹", "先点「浏览…」选一个软件目录。")
            return
        if not Path(target).is_dir():
            messagebox.showerror("路径不存在", target)
            return
        self.btn_scan.config(state="disabled")
        self.status.set("正在扫描…")
        self.root.update()
        threading.Thread(target=self._scan_worker, args=(target, self.run_tests.get()), daemon=True).start()

    def _scan_worker(self, target, with_tests):
        try:
            findings, info, test_result = scanner.collect(target, with_tests=with_tests)
            self.root.after(0, lambda: self._show(findings, info, test_result))
        except Exception as err:  # noqa: BLE001 - 界面不能因为一个坏项目崩掉
            self.root.after(0, lambda: self._fail(err))

    def _fail(self, err):
        self.btn_scan.config(state="normal")
        self.status.set(f"扫描失败：{err}")

    def _show(self, findings, info, test_result):
        self.findings, self.info, self.test_result = findings, info, test_result
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in findings:
            self.tree.insert("", "end", values=(
                item.severity, f"{item.path}:{item.line}", item.kind, item.detail, item.advice,
            ), tags=(item.severity,))
        counts = {level: sum(1 for x in findings if x.severity == level) for level in COLOR}
        test_note = (f" · 自带测试：{test_result['summary']}" if test_result.get("ran")
                     else " · 自带测试未运行")
        self.status.set(
            f"扫描 {info['python_files']} 个 Python 文件 · 高危 {counts['高']} / 中危 {counts['中']} / 低危 {counts['低']}{test_note}")
        self.btn_scan.config(state="normal")

    def open_file(self, _event=None):
        picked = self.tree.selection()
        if not picked:
            return
        location = self.tree.item(picked[0], "values")[1]
        path_text = location.rsplit(":", 1)[0]
        full = Path(self.info.get("root", "")) / path_text
        if full.exists():
            import os
            os.startfile(full)   # noqa: S606 - 用户主动双击，打开源文件
        else:
            messagebox.showinfo("找不到文件", str(full))

    def make_report(self):
        if not self.info:
            messagebox.showinfo("还没扫描", "先点「开始体检」。")
            return
        target = Path(self.info["root"]) / "体检报告.html"
        path = reporter.render_scan_report(self.findings, self.info, self.test_result, target)
        webbrowser.open(path.as_uri())
        self.status.set(f"报告已生成并打开：{path}")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()