# 软件测试可视化

接口自动化测试练习项目：**pytest + requests**，56 个用例，覆盖正常流程、异常边界、并发安全，并自带零依赖的指标工具（报告 / 覆盖率）。

## 为什么自带一个 mock 服务

原本想用 [restful-booker](https://github.com/mwinteringham/restful-booker) 做靶场，但它部署在 Heroku 免费实例上——

```
$ curl https://restful-booker.herokuapp.com/booking
HTTP 000
```

已经连不上了。所以 `mock_server.py` 用标准库实现了一份**同形状**的接口（鉴权、CRUD、400/401/403/404 语义齐全），离线也能跑，不受别人服务器影响。

## 目录

```
软件测试可视化/
├─ mock_server.py          本地 API（只用标准库，线程安全）
├─ conftest.py             pytest 夹具：起服务、鉴权、造数据、清数据
├─ retry.py                失败重试插件（零依赖，给 flaky 用例用）
├─ coverage_simple.py      语句覆盖率（零依赖，sys.settrace）
├─ assertions.py           失败信息更清楚的断言库
├─ contract.py             生成 / 比对契约快照
├─ reports.py              report.xml → 自包含 HTML 报告
├─ scanner.py              图形化体检器（静态检查 + 跑测试）
├─ tests/
│   ├─ test_health.py      健康检查与路由（5 个）
│   ├─ test_auth.py        鉴权（6 个）
│   ├─ test_crud.py        增删改查主流程（9 个）
│   ├─ test_validation.py  参数校验与边界（14 个）
│   ├─ test_smoke.py       冒烟层（4 个）
│   ├─ test_data_driven.py 数据驱动（7 个）
│   ├─ test_contract.py    契约快照（2 个）
│   └─ test_concurrency.py 并发安全与延迟（6 个）
├─ data/booking_cases.json 数据驱动用例表
├─ snapshots/              契约快照
├─ examples/               演示用的"偶发失败"用例（默认不跑）
├─ pytest.ini
├─ requirements.txt
└─ 运行测试.bat / 一键测试.bat
```

## 跑起来

```bash
pip install -r requirements.txt
python -m pytest
```

Windows 上也可以双击 `运行测试.bat`。

实测输出：

```
collected 56 items
...
==================== 53 passed, 3 skipped in 2.60s ====================
```

（跳过的 3 个是 `test_my_api_template.py` 里的模板用例，删掉 `@pytest.mark.skip` 就会执行。）

## 覆盖了什么

| 类别 | 测的点 |
|---|---|
| 健康检查 | ping 通不通、返回体、Content-Type、未知路由 404 |
| 鉴权 | 正确凭据换 token、错误密码 401、缺 token / 错 token 403 |
| CRUD | 创建返回 ID、创建后能查、出现在列表、PUT 全量更新、PATCH 只改指定字段、删除返回 201、删完 404、重复删除 404 |
| 参数校验 | 缺字段、`depositpaid` 非布尔、`totalprice` 非数字、日期格式非 ISO、`bookingdates` 缺键、查不存在的资源 404 |
| 并发 | 10 线程并发建 30 条不重号、不丢数据、改不同单子互不干扰、重复删除只成功一次、健康检查延迟 < 200ms |

**参数化用例**（`@pytest.mark.parametrize`）一个函数覆盖多个边界值，所以 56 个用例其实只用了 41 个测试函数。

## 几个值得注意的设计

1. **每个用例前清空数据**（`autouse` 夹具）——否则用例执行顺序会影响结果，出现"单跑过、全跑挂"。
2. **造数据的夹具负责善后**——`yield` 之后自动删除，不靠用例自己清理。
3. **端口用 0** 让系统分配，避免和本机其他服务抢端口。
4. **等 `/ping` 通再开始测**，不靠 `sleep` 赌时间。

## 能力清单（已完成 / 没做）

- [x] 本地 mock 服务 + 分层用例（冒烟 / 回归）
- [x] 数据驱动用例（`data/booking_cases.json`）
- [x] 契约快照（字段类型变了就红）
- [x] 零依赖 HTML 报告（`reports.py`）
- [x] GitHub Actions 四关流水线
- [x] 失败重试（`retry.py`，只给 flaky 用例开）
- [x] 并发用例 + 零依赖语句覆盖率（93.8%）
- [ ] Allure 报告（要装 `allure-pytest` + Java 运行时）
- [ ] Playwright 补 UI 层（要下载浏览器，约 300MB）

## License

MIT

## 测试工作流

一套能日常用的流程，不只是"跑一下看看"。

```
写用例  →  冒烟先跑（-m smoke）  →  全量回归  →  出报告  →  看红字定位  →  修
                                        ↑                              ↓
                                     CI 每次提交自动跑  ←───────────────┘
```

### 1. 分层：冒烟 / 回归

用例打了标记（`pytest.ini` 里声明），可以分开跑：

```bash
pytest -m smoke            # 只跑冒烟（4 个，0.5s）—— 服务挂了立刻知道
pytest -m "not smoke"      # 跳过冒烟，只跑细节
pytest -m regression       # 回归组
```

**为什么分层**：CI 上先跑冒烟，挂了就不用浪费时间跑后面几百个用例。

### 2. 断言要能"说清哪不对"

`assertions.py` 提供四个helper，失败时会把实际响应体打出来：

```python
from assertions import assert_status, assert_json_field, assert_fields_present, assert_error_message

assert_status(response, 200, "创建预订")          # 失败会带上响应体
assert_fields_present(body, ["token"], "登录返回")  # 缺字段会说缺哪个
assert_error_message(response, "Bad credentials")  # 错误信息里必须有原因
```

对比一下：

| 写法 | 失败时你看到 |
|---|---|
| `assert r.status_code == 200` | `assert 500 == 200` ← 还得自己复现 |
| `assert_status(r, 200, "创建预订")` | 状态码 + 请求 URL + 响应体 ← 直接定位 |

### 3. 一键跑 + 出报告

双击 `一键测试.bat`：跑全量 → 生成 HTML 报告 → 自动开浏览器。

### 4. CI

`.github/workflows/test.yml` 在 push 时跑三个 Python 版本（3.11/3.12/3.13）。



### 5. 数据驱动用例

测试场景写在 `data/booking_cases.json` 里，加一行就是加一个用例，不用改代码：

```json
{"id": "价格为0", "payload": {...}, "expect": 200}
```

`tests/test_data_driven.py` 读这个文件，用 `@pytest.mark.parametrize` 展开。

### 6. 契约快照

`contract.py` 记录响应里每个字段的**类型结构**，结构变了就失败：

```
snapshots/create_booking.json
{ "booking": { "bookingdates": {"checkin": "str", ...}, "totalprice": "int" }, "bookingid": "int" }
```

**为什么需要**：后端把 `totalprice` 从数字改成字符串，功能断言可能照样过，但前端会炸。契约测试专盯这个。

```bash
python contract.py          # 重新生成快照（确认改动是预期的）
pytest tests/test_contract.py
```

### 7. 切换被测服务

默认跑本地 mock。要测真实服务就设环境变量：

```powershell
$env:API_BASE_URL = "http://127.0.0.1:8000"
python -m pytest
```

### 8. 失败重试（治理 flaky 用例）

CI 里最烦的不是"一直红"，而是"有时红有时绿"——这类用例叫 **flaky**（偶发失败）。
`retry.py` 是项目自带的零依赖重试插件（不需要 `pytest-rerunfailures`）：

```python
@pytest.mark.flaky(reruns=2, delay=0.3)
def test_第三方接口():
    ...
```

重试**只对打了标记的用例生效**，跑完会单独打印"重试记录"，点名谁靠重试才过的：

```
  RERUN tests/test_x.py::test_y：第 1 次没通过，0.3s 后重试
------------------------ 重试记录 ------------------------
  tests/test_x.py::test_y  重试 1 次后通过
  共 1 个用例靠重试变绿 —— 记下来查根因，别长期留着
```

**为什么不能全局重试**：重试会掩盖真缺陷，还会拖慢 CI。正确顺序是：先查是不是用例自己的问题（等待时间不够、依赖了执行顺序、共享数据没清），确认是外部抖动才加标记，并把它记进待办。

想看效果：`python -m pytest examples/ -q`（两条故意偶发失败的用例，默认不在回归里跑）。

### 9. 并发安全

`tests/test_concurrency.py` 用线程池同时打 10 个请求，守四类 bug：

| 场景 | 断言 | 打中的是哪类 bug |
|---|---|---|
| 并发创建 30 条 | ID 不重复、列表正好 30 条 | 发号没加锁 → 两张单拿到同一个号 |
| 并发读 | 读到的条数稳定 | 读写同一份数据没隔离 |
| 并发改不同单子 | 互不串数据 | 共享状态写错 |
| 并发删同一条 | 只有 1 个返回 201 | "先查再删"两步之间被插队 |

写这组用例时顺手审出 mock 的 `do_DELETE` 是"先查在不在、再删"两步——实测 240 次并发删除没撞上（窗口只有几微秒），但结构上就是错的，已改成一把锁里的原子 `pop`。**代码审查能发现的问题，别等线上发生。**

### 10. 覆盖率（零依赖）

`python coverage_simple.py` 用标准库 `sys.settrace` 统计 `mock_server.py` 的语句覆盖：

```
被测文件: mock_server.py
可执行行: 177    已覆盖: 166    覆盖率: 93.8%
未覆盖的行: 209-218、222
```

- **分母** = 编译后字节码里的可执行行（不是"文件共多少行"）；
- **分子** = 跑完接口场景后真正执行过的行；
- 剩下的 `209-218` 是命令行入口 `main()`，只有直接 `python mock_server.py` 才走。

CI 里带 `--min 90`，覆盖率掉下去流水线直接红。

## 这个项目自己发现过三个问题

写完数据驱动用例后，**测试立刻抓到 mock 服务的两个真实缺陷**：

| 缺陷 | 症状 | 修复 |
|---|---|---|
| 空名字能创建 | `firstname: ""` 返回 200 | `validate()` 加非空检查 |
| 假日期能通过 | `2026-13-45` 被接受 | 正则只管位数，改用 `datetime.strptime` 真校验 |

补充 `checkout > checkin` 规则后，用例从 2 failed 变成全绿。

第三个问题是写并发用例时审出来的：`do_DELETE` 里"先查在不在、再删"不是原子操作（见第 9 节），已经改成一把锁里完成。

**这就是测试的价值**——不是"证明代码是对的"，是"在它错的时候立刻知道"。

## 还能加什么

- [ ] Playwright 补 UI 层（要下载浏览器，适合本机装好后再加）
- [ ] Allure 报告（要装 `allure-pytest` 和 Java 运行时）
- [ ] 用 `pytest-xdist` 把 56 个用例并行跑（现在 2.6 秒，收益不大，属于扩展练习）

