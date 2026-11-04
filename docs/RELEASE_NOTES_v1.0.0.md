# v1.0.0 — 101 条用例 / 95% 覆盖 / 7 关 CI

一个可以直接拿去讲、拿去跑的软件测试项目：本地 mock 靶场 + 接口/UI/并发/契约/性能/真实 API 六类验证，全部零重型依赖。

## 用例与指标

| 项 | 数值 |
|---|---|
| 接口用例 | 92（89 passed + 3 模板跳过） |
| UI 用例（Playwright） | 9 |
| 联网用例（dummyjson，默认跳过） | 10 |
| 语句覆盖率 | 95.0% |
| 缺陷记录 | 7 条（含越权、超卖、并发竞态） |
| CI | 7 关自动 + 1 关手动 |

## 能力清单

- **接口层**：健康检查、鉴权（admin/viewer 角色）、CRUD、参数校验、分页过滤、房间库存、幂等键
- **契约层**：类型快照（`contract.py`）+ 零依赖 JSON Schema 校验（`schema_validator.py`）
- **并发层**：10 线程并发建单、并发删、并发抢库存（防超卖）
- **UI 层**：Playwright 点真实管理页面，失败自动截图 + trace
- **性能层**：`perf_load.py` 并发梯度 1/5/20/30，p50/p95/p99 + 阈值退出码
- **真实 API**：`live_tests/` 对 dummyjson 的 10 条联网用例，连不上自动 skip

## 工程化

- CI：静态检查（compileall + 自研体检器 + ruff）→ 冒烟 → 三版本回归矩阵 → UI → 汇总
- 报告：自研 HTML（`reports.py`）+ Allure（分组 / 步骤 / 附件 / 环境信息 / 历史趋势）
- 失败证据：截图 + Playwright trace，CI 失败上传 artifact
- 文档：`docs/测试方案.md`（等价类 / 边界值 / 判定表 / 用例清单）、`docs/缺陷记录.md`

## 快速开始

```powershell
pip install -r requirements.txt
python -m pytest                 # 92 条接口用例
python coverage_simple.py        # 覆盖率
python perf_load.py              # 性能基线
```

UI 层与 Allure 需要额外环境，见 README 第 11 / 13 节。

## 值得一说的三个缺陷

1. **超卖**：10 人抢 5 间房卖出 9 间——"查库存"和"扣库存"没在同一把锁里；
2. **越权**：加角色时只校验了创建接口，viewer 能删数据；
3. **闭包失效**：异常回调 `lambda: self._fail(err)` 捕获了 `except` 结束就失效的变量，真出错时反而 `NameError`。

每个缺陷在 `docs/缺陷记录.md` 里都有：复现步骤、根因、修复、回归验证。
