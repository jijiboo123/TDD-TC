#!/usr/bin/env python3
"""软件测试可视化 · 体检引擎：给一个文件夹，自动找出「可能的 bug 和安全隐患」。

能力边界（先说清楚，免得期待错位）：
  ✅ 能做的：静态代码检查 —— 已知的危险写法（eval/exec、SQL 拼接、硬编码密码、
     裸 except、可变默认参数…），以及跑一遍项目自带的测试
  ❌ 做不到：理解业务逻辑、凭空测出"这个功能算错了"。没有测试的软件，
     工具无法知道它该有什么行为

所以它的定位是：**第一轮体检**，把人眼容易漏掉的模式扫一遍，把结果排好优先级。

用法：
    python scanner.py <项目目录>              # 命令行输出
    python scanner.py <项目目录> --html 报告.html
    python tester_gui.py                     # 图形界面
"""

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

SEVERITY_ORDER = {"高": 0, "中": 1, "低": 2}
SEVERITY_COLOR = {"高": "#d9534f", "中": "#e0a13c", "低": "#4c8dff"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build", ".pytest_cache"}
MAX_FILES = 400


class Finding:
    def __init__(self, path, line, severity, kind, detail, advice):
        self.path = str(path)
        self.line = line
        self.severity = severity
        self.kind = kind
        self.detail = detail
        self.advice = advice

    def as_dict(self):
        return {"文件": self.path, "行": self.line, "级别": self.severity,
                "类型": self.kind, "问题": self.detail, "建议": self.advice}


class Visitor(ast.NodeVisitor):
    """遍历语法树找危险写法。比正则可靠：能区分"字符串里出现 eval"和"真的调用了 eval"。"""

    def __init__(self, source, rel_path):
        self.source = source
        self.rel = rel_path
        self.findings = []
        self._lines = source.splitlines()

    def add(self, node, severity, kind, detail, advice):
        self.findings.append(Finding(self.rel, getattr(node, "lineno", 0), severity, kind, detail, advice))

    # ---- 高危调用 ----
    def visit_Call(self, node):
        name = self._call_name(node)
        if name in ("eval", "exec"):
            self.add(node, "高", "动态执行代码", f"调用了 {name}()",
                     "攻击者能控制输入时等于任意代码执行，改用 ast.literal_eval 或显式分支")
        elif name == "os.system":
            self.add(node, "高", "命令注入风险", "调用了 os.system()",
                     "改用 subprocess.run(..., shell=False) 并传参数列表")
        elif name in ("pickle.loads", "pickle.load"):
            self.add(node, "高", "反序列化风险", f"调用了 {name}()",
                     "反序列化不可信数据可导致任意代码执行，改用 json")
        elif name == "yaml.load":
            self.add(node, "高", "反序列化风险", "调用了 yaml.load()",
                     "改用 yaml.safe_load()")
        elif name in ("subprocess.Popen", "subprocess.run", "subprocess.call", "subprocess.check_output"):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    self.add(node, "高", "命令注入风险", f"{name}(shell=True)",
                             "shell=True 会解释管道与重定向，改用列表参数并保持 shell=False")
        elif name and name.endswith(".execute") or name and name.endswith(".executemany"):
            self._check_sql(node)
        self.generic_visit(node)

    def _call_name(self, node):
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            parts, cursor = [], func
            while isinstance(cursor, ast.Attribute):
                parts.append(cursor.attr)
                cursor = cursor.value
            if isinstance(cursor, ast.Name):
                parts.append(cursor.id)
            return ".".join(reversed(parts))
        return None

    def _check_sql(self, node):
        """拼 SQL 字符串（f-string 或 +）就是注入口子"""
        if not node.args:
            return
        first = node.args[0]
        if isinstance(first, ast.JoinedStr):
            self.add(node, "高", "SQL 注入", "用 f-string 拼 SQL",
                     "改用参数化查询 execute(sql, params)")
        elif isinstance(first, ast.BinOp) and isinstance(first.op, ast.Add):
            self.add(node, "高", "SQL 注入", "用 + 拼接 SQL", "改用参数化查询 execute(sql, params)")

    # ---- 异常处理 ----
    def visit_ExceptHandler(self, node):
        if node.type is None:
            self.add(node, "中", "异常被吞掉", "裸 except:",
                     "会连 KeyboardInterrupt 一起吞，改成 except Exception as err")
        elif node.body and all(isinstance(stmt, ast.Pass) for stmt in node.body):
            self.add(node, "中", "异常被吞掉", "except 里只有 pass",
                     "静默失败会让 bug 更难查，至少记录日志")
        self.generic_visit(node)

    # ---- 可变默认参数 ----
    def visit_FunctionDef(self, node):
        self._check_defaults(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._check_defaults(node)
        self.generic_visit(node)

    def _check_defaults(self, node):
        for default in node.args.defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.add(node, "中", "可变默认参数", f"函数 {node.name} 用可变对象作默认值",
                         "默认值只在定义时求值一次，跨调用共享；改成 None 再在函数体内初始化")

    # ---- 硬编码凭据 ----
    KEY_PATTERN = re.compile(r"(password|passwd|pwd|secret|token|api_?key|access_?key)", re.I)

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name) and self.KEY_PATTERN.search(target.id):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and node.value.value:
                    self.add(node, "高", "硬编码凭据", f"{target.id} 直接写成明文常量",
                             "移到环境变量或配置文件，并确认该文件不被提交")
        self.generic_visit(node)
    # ---- 文本级补充检查（正则，AST 管不到的）----
    def check_text(self):
        # 有 __main__ 守卫的是命令行入口，print 是它的正常输出而非调试残留
        is_cli_entry = "__main__" in self.source
        for number, line in enumerate(self._lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # 跳过规则定义行本身，否则扫描器会把自己的规则当成待办
            if re.search(r"\b(TODO|FIXME|XXX)\b", line) and "re.search(" not in line and "待办标记" not in line and "TODO/FIXME" not in line:
                self.findings.append(Finding(self.rel, number, "低", "待办标记", "代码里有 TODO/FIXME",
                                             "确认这些没被忘记；交付前应清理"))
            if re.search(r"\bprint\(", line) and not is_cli_entry and "test" not in self.rel.lower():
                self.findings.append(Finding(self.rel, number, "低", "调试残留", "生产代码里有 print()",
                                             "改用 logging，否则输出会混进业务日志"))
            if re.search(r"assert\s+", line) and not is_cli_entry and not any(k in self.rel.lower() for k in ("test", "assert")):
                self.findings.append(Finding(self.rel, number, "中", "用断言做校验", "用 assert 检查业务条件",
                                             "python -O 会移除 assert，校验会失效；改用显式 raise"))


def scan_python(path, rel_path):
    """扫一个 .py 文件：语法错误 + AST 检查 + 文本检查"""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError as err:
        return [Finding(rel_path, 0, "中", "读取失败", str(err), "检查文件权限或编码")]

    findings = []
    try:
        tree = ast.parse(source)
    except SyntaxError as err:
        return [Finding(rel_path, err.lineno or 0, "高", "语法错误",
                        f"{err.msg}", "文件无法被导入，程序跑到这里一定崩")]

    visitor = Visitor(source, rel_path)
    visitor.visit(tree)
    visitor.check_text()
    return visitor.findings


def scan_project(root):
    """扫整个项目，返回 (findings, 项目信息)"""
    root = Path(root).resolve()
    if not root.is_dir():
        raise SystemExit(f"目录不存在: {root}")

    files, skipped = [], 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() == ".py":
            if len(files) >= MAX_FILES:
                skipped += 1
                continue
            files.append(path)

    findings = []
    for path in files:
        findings.extend(scan_python(path, path.relative_to(root).as_posix()))

    info = {
        "root": str(root),
        "python_files": len(files),
        "skipped_files": skipped,
        "has_tests": any("test" in p.name.lower() for p in files),
        "has_requirements": (root / "requirements.txt").exists(),
        "has_readme": any(root.glob("README*")),
        "has_package_json": (root / "package.json").exists(),
        "has_gitignore": (root / ".gitignore").exists(),
    }
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.path, f.line))
    return findings, info


def run_project_tests(root, timeout=180):
    """如果项目自带 pytest 用例，就跑一遍并把结果带回来"""
    root = Path(root).resolve()
    if not any("test" in p.name.lower() for p in root.glob("**/*.py")):
        return {"ran": False, "reason": "项目里没有测试文件，无法验证行为"}
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider"],
            cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ran": False, "reason": f"测试超过 {timeout} 秒未结束，已放弃"}
    tail = [line for line in (result.stdout or "").strip().splitlines() if line.strip()]
    return {"ran": True, "exit_code": result.returncode, "summary": tail[-1] if tail else "", "output": "\n".join(tail[-25:])}

def collect(root, with_tests=True):
    """统一入口：静态检查 + 项目级体检 + （可选）跑自带测试并合并失败项"""
    findings, info = scan_project(root)
    test_result = run_project_tests(root) if with_tests else {"ran": False, "reason": "已跳过"}
    if test_result.get("ran") and test_result.get("exit_code"):
        findings.extend(parse_test_failures(test_result.get("output")))
        findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.path, f.line))
    return findings, info, test_result


# ---------------- 命令行 ----------------

def print_console(findings, info, test_result):
    counts = {level: sum(1 for x in findings if x.severity == level) for level in SEVERITY_ORDER}
    print(f"\n扫描目录: {info['root']}")
    print(f"Python 文件: {info['python_files']} 个"
          + (f"（另有 {info['skipped_files']} 个超过上限被跳过）" if info["skipped_files"] else ""))
    print(f"发现问题: 高 {counts['高']} / 中 {counts['中']} / 低 {counts['低']}\n")
    for item in findings:
        print(f"  [{item.severity}] {item.path}:{item.line}  {item.kind}")
        print(f"        {item.detail}")
        print(f"        → {item.advice}")
    if test_result.get("ran"):
        print(f"\n项目自带测试: {test_result['summary']}")
    else:
        print(f"\n项目自带测试: 未运行（{test_result.get('reason')}）")


def main():
    parser = argparse.ArgumentParser(description="软件体检器：静态检查 + 跑自带测试")
    parser.add_argument("target", help="要检查的项目目录")
    parser.add_argument("--html", help="生成 HTML 报告到这个路径")
    parser.add_argument("--no-tests", action="store_true", help="跳过跑项目自带测试")
    args = parser.parse_args()

    findings, info, test_result = collect(args.target, with_tests=not args.no_tests)

    print_console(findings, info, test_result)

    if args.html:
        import reports as reporter
        path = reporter.render_scan_report(findings, info, test_result, Path(args.html))
        print(f"\nHTML 报告: {path}")
    return 0 if not any(x.severity == "高" for x in findings) else 1



# ---------------- 项目级体检 ----------------

SENSITIVE_FILES = [".env", ".env.local", "id_rsa", "id_dsa", "credentials.json",
                   ".npmrc", ".pypirc", "secrets.json", "config.ini"]
SENSITIVE_SUFFIX = [".pem", ".key", ".pfx", ".p12"]


def scan_sensitive(root):
    """找不该出现在项目里的文件"""
    findings = []
    for path in Path(root).rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name in SENSITIVE_FILES or path.suffix.lower() in SENSITIVE_SUFFIX:
            findings.append(Finding(path.relative_to(root).as_posix(), 0, "高", "敏感文件",
                                    f"项目里有 {path.name}",
                                    "确认它已加入 .gitignore；若曾提交过，密钥要立刻更换"))
    return findings


def scan_hygiene(root, info):
    """工程健康度：缺了这些东西，维护成本会变高"""
    findings = []
    checks = [
        ("has_readme", "缺少 README", "低", "别人不知道该项目怎么跑；补一份说明"),
        ("has_requirements", "缺少依赖清单", "中", "换台机器装不上依赖；补 requirements.txt 或 package.json"),
        ("has_tests", "项目没有测试", "中", "没有测试就无法验证改动有没有弄坏东西；先补冒烟用例"),
        ("has_gitignore", "缺少 .gitignore", "中", "缓存和密钥容易被误提交；补一份"),
    ]
    for key, problem, severity, advice in checks:
        if not info.get(key):
            findings.append(Finding("(项目根目录)", 0, severity, "工程健康度", problem, advice))
    return findings


def parse_test_failures(output):
    """从 pytest 输出里提取失败用例，转成 findings"""
    findings = []
    for line in (output or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("FAILED ") or stripped.startswith("ERROR "):
            parts = stripped.split(" ", 1)[1]
            location, _, reason = parts.partition(" - ")
            findings.append(Finding(location, 0, "高", "测试失败",
                                    reason.strip() or "用例失败",
                                    "这条用例红了，说明对应功能当前不可用"))
    return findings


if __name__ == "__main__":
    raise SystemExit(main())
