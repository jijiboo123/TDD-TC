"""模板：拿这个文件改成「测你自己的接口」。

默认这 3 个用例是 skip 状态，所以不影响现有 53 个用例的结果。
想启用就把 @pytest.mark.skip 那一行删掉。

改哪三处，下面标了 ①②③。
"""

import pytest
import requests

# ① 被测服务的地址。想测你自己的就换成真实地址，例如 "http://127.0.0.1:8000"
BASE_URL = "http://127.0.0.1:8321"


@pytest.mark.skip(reason="模板用例，改完删掉这行就会执行")
def test_你的第一个接口():
    # ② 发请求：换成你要测的路径和参数
    response = requests.get(f"{BASE_URL}/ping", timeout=5)

    # ③ 断言：这就是"测试"的本质——把期望写成条件，不满足就报错
    assert response.status_code == 200, f"状态码不对：{response.status_code}"
    assert response.text == '"pong"', f"返回内容不对：{response.text}"


@pytest.mark.skip(reason="模板用例，改完删掉这行就会执行")
def test_登录接口_正常情况():
    response = requests.post(
        f"{BASE_URL}/auth",
        json={"username": "admin", "password": "password123"},
        timeout=5,
    )
    assert response.status_code == 200
    assert "token" in response.json()


@pytest.mark.skip(reason="模板用例，改完删掉这行就会执行")
def test_登录接口_密码错误():
    """异常场景才是测试的重点：密码错了，服务必须拒绝。"""
    response = requests.post(
        f"{BASE_URL}/auth",
        json={"username": "admin", "password": "错误密码"},
        timeout=5,
    )
    assert response.status_code == 401, "密码错了竟然还登录成功，这是安全漏洞"