# api-testing-demo

接口自动化测试练习项目：**pytest + requests**，34 个用例，覆盖正常流程与异常边界。

## 为什么自带一个 mock 服务

原本想用 [restful-booker](https://github.com/mwinteringham/restful-booker) 做靶场，但它部署在 Heroku 免费实例上——

```
$ curl https://restful-booker.herokuapp.com/booking
HTTP 000
```

已经连不上了。所以 `mock_server.py` 用标准库实现了一份**同形状**的接口（鉴权、CRUD、400/401/403/404 语义齐全），离线也能跑，不受别人服务器影响。

## 目录

```
api-testing-demo/
├─ mock_server.py          本地 API（201 行，只用标准库）
├─ conftest.py             pytest 夹具：起服务、鉴权、造数据、清数据
├─ tests/
│   ├─ test_health.py      健康检查与路由（5 个）
│   ├─ test_auth.py        鉴权（6 个）
│   ├─ test_crud.py        增删改查主流程（9 个）
│   └─ test_validation.py  参数校验与边界（14 个）
├─ pytest.ini
├─ requirements.txt
└─ 运行测试.bat
```

## 跑起来

```bash
pip install -r requirements.txt
python -m pytest
```

Windows 上也可以双击 `运行测试.bat`。

实测输出：

```
collected 34 items
...
============================= 34 passed in 0.75s =============================
```

## 覆盖了什么

| 类别 | 测的点 |
|---|---|
| 健康检查 | ping 通不通、返回体、Content-Type、未知路由 404 |
| 鉴权 | 正确凭据换 token、错误密码 401、缺 token / 错 token 403 |
| CRUD | 创建返回 ID、创建后能查、出现在列表、PUT 全量更新、PATCH 只改指定字段、删除返回 201、删完 404、重复删除 404 |
| 参数校验 | 缺字段、`depositpaid` 非布尔、`totalprice` 非数字、日期格式非 ISO、`bookingdates` 缺键、查不存在的资源 404 |

**参数化用例**（`@pytest.mark.parametrize`）一个函数覆盖多个边界值，所以 34 个用例其实只用了 20 个测试函数。

## 几个值得注意的设计

1. **每个用例前清空数据**（`autouse` 夹具）——否则用例执行顺序会影响结果，出现"单跑过、全跑挂"。
2. **造数据的夹具负责善后**——`yield` 之后自动删除，不靠用例自己清理。
3. **端口用 0** 让系统分配，避免和本机其他服务抢端口。
4. **等 `/ping` 通再开始测**，不靠 `sleep` 赌时间。

## 下一步可以加

- [ ] Allure 报告（`pip install allure-pytest` + allure 命令行）
- [ ] GitHub Actions：每次 push 自动跑
- [ ] Playwright 补 UI 层用例

## License

MIT