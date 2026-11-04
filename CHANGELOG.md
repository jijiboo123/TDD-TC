# 更新日志

## v1.0.2 — 2026-11-04

**修一个双击就中的坑**

- 修复：双击 `开始使用.bat` 时中文乱码、半行被当成命令执行。
  原因：cmd 用控制台代码页（936）读取 UTF-8 批处理，多字节字符跨读取缓冲区后会裂开。
- 方案：菜单逻辑移到 `start_menu.py`（Python 直接写 Unicode），`开始使用.bat` 只做 ASCII 启动器；
  其余 `.bat` 也统一改成 ASCII，中文提示全部由 Python 输出。
- 顺带：`开始使用.bat` 启动前会检查 python 是否在 PATH。

## v1.0.1 — 2026-11-04

**开箱即用**

- 新增 `开始使用.bat`：9 个入口的一键控制台（接口 / UI / 报告 / Allure / 覆盖率 / 性能 / 真实 API / 打开目录 / 退出）
- 新增 `check_env.py`：环境自检（Python、pytest/requests/allure-pytest、playwright+Chromium、Java+allure），从注册表读取 JAVA_HOME/PATH，刚装完不用重启也能识别
- 桌面快捷方式「软件测试项目」指向控制台菜单
- README 顶部加「下次打开先看这里」

## v1.0.0 — 2026-11-04

第一个"拿得出手"的版本：**101 条本地用例 + 10 条联网用例，7 关 CI，7 份缺陷记录**。

**测试能力**

- 接口 92 条：健康检查、鉴权、CRUD、参数校验、数据驱动、契约（快照 + JSON Schema）、角色越权、分页、库存、幂等、并发
- UI 9 条（Playwright）：登录、创建、改价、删除、空名报错、房型选择、库存扣减、售罄提示
- 联网 10 条（dummyjson）：登录 JWT、契约、分页、增删改、跨公网延迟，默认跳过

**质量指标**

- 语句覆盖率 95.0%（零依赖 `coverage_simple.py`）
- 性能基线：并发梯度 1/5/20/30，p95 阈值判定（零依赖 `perf_load.py`）
- 静态检查：`ruff` 0 告警 + 自研体检器 高/中/低 0

**工程化**

- CI 7 关：静态+覆盖率 → 冒烟 → 三版本回归矩阵 → UI → 汇总；另有性能、Allure、真实 API 三个附加任务
- 报告：自研 HTML + Allure（分组、步骤、附件、环境信息、历史趋势）
- 失败证据：UI 截图 + Playwright trace，CI 失败上传 artifact
- 文档：`docs/测试方案.md`、`docs/缺陷记录.md`（7 个缺陷的完整缺陷单）

## v0.9 — 业务模型升级

- mock 增加 admin/viewer 角色、`page/size/roomtype` 分页、房间库存
- 并发用例撞出 **BUG-005 越权删除**（S2）、**BUG-006 超卖**（S1：10 人抢 5 间卖出 9 间）

## v0.8 — 幂等与性能

- `Idempotency-Key`：同一 key 重复/并发提交只建一单
- `perf_load.py`：性能基线，首次运行发现监听队列过小导致 p99 抖动（515ms → 14ms）

## v0.7 — UI 层与文档

- Playwright UI 层 + 管理页面（`web/index.html`）
- `docs/测试方案.md`（等价类 / 边界值 / 判定表 / 用例清单）
- `docs/缺陷记录.md`（BUG-001 ~ BUG-004）

## v0.6 — 契约测试

- `contract.py` 类型快照 + `schema_validator.py` JSON Schema 规则校验（零依赖）

## v0.5 — 稳定性

- `retry.py` 失败重试插件（只对 flaky 用例生效）
- 并发用例、`coverage_simple.py` 语句覆盖率、失败现场留存

## v0.4 — CI

- GitHub Actions 分关阻断（静态 → 冒烟 → 多版本回归 → 汇总）

## v0.3 — 数据驱动与缺陷

- 用例数据外置到 JSON；契约快照
- 发现并修复 **BUG-001 空名字可创建**、**BUG-002 假日期通过**

## v0.2 — 工作流

- 冒烟 / 回归分层、断言库、一键脚本、零依赖 HTML 报告

## v0.1 — 起点

- 本地 mock 服务 + 34 条接口用例（restful-booker 下线后的替代方案）
