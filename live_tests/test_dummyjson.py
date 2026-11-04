"""真实公开 API 冒烟：同一套测试思路，换到一个我们控制不了的服务上。

为什么值得做：本地 mock 是自己写的，想怎么造就怎么造；真实 API 有网络延迟、
文档和实际可能不一致、字段说变就变。能跑通，才说明这套用例不是"只能在我家跑"。

被测服务：https://dummyjson.com （公开的假数据 API，有 posts / auth / 增删改）
默认跳过，要跑先设 LIVE_API=1（或双击 运行真实API测试.bat）。
"""

import statistics
import time
from pathlib import Path

import allure
import pytest
import requests

from schema_validator import load, validate

pytestmark = [pytest.mark.live, allure.feature("真实 API · dummyjson")]

SCHEMA = Path(__file__).resolve().parent.parent / "schema" / "post.schema.json"


def post_schema():
    return load(SCHEMA)


def test_service_reachable(base_url):
    assert requests.get(f"{base_url}/posts?limit=1", timeout=15).status_code == 200


def test_login_returns_token(token):
    """真实服务登录链路：拿到 JWT 才算通。"""
    assert isinstance(token, str) and len(token) > 20


def test_bad_password_is_rejected(base_url):
    response = requests.post(
        f"{base_url}/auth/login", json={"username": "emilys", "password": "not-the-password"}, timeout=15)
    assert response.status_code in (400, 401), response.text


def test_post_detail_matches_contract(base_url):
    """契约校验：字段类型按 schema 走，多出来的字段（reactions/views）允许存在。"""
    body = requests.get(f"{base_url}/posts/1", timeout=15).json()
    validate(body, post_schema(), "post 详情")


def test_list_pagination(base_url):
    body = requests.get(f"{base_url}/posts?limit=5&skip=0", timeout=15).json()
    assert body["limit"] == 5
    assert body["skip"] == 0
    assert body["total"] >= 100
    assert len(body["posts"]) == 5


def test_skip_moves_the_window(base_url):
    """翻页要换一批 id，而不是把第一页又发一遍。"""
    first = [item["id"] for item in requests.get(f"{base_url}/posts?limit=5&skip=0", timeout=15).json()["posts"]]
    second = [item["id"] for item in requests.get(f"{base_url}/posts?limit=5&skip=5", timeout=15).json()["posts"]]
    assert first != second


def test_create_returns_new_id(base_url):
    payload = {"title": "自动化创建", "body": "来自 live 用例", "userId": 1}
    response = requests.post(f"{base_url}/posts/add", json=payload, timeout=15)
    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    validate(body, post_schema(), "创建响应")


def test_update_changes_title(base_url):
    response = requests.put(f"{base_url}/posts/1", json={"title": "改过的标题"}, timeout=15)
    assert response.status_code == 200
    assert response.json()["title"] == "改过的标题"


def test_delete_marks_deleted(base_url):
    response = requests.delete(f"{base_url}/posts/1", timeout=15)
    assert response.status_code == 200
    assert response.json().get("isDeleted") is True


def test_network_latency_smoke(base_url):
    """跨公网跑，阈值放宽到 3 秒——测的是"通不通、会不会离谱"，不是性能。"""
    samples = []
    for _ in range(10):
        started = time.perf_counter()
        assert requests.get(f"{base_url}/posts?limit=1", timeout=15).status_code == 200
        samples.append((time.perf_counter() - started) * 1000)
    median = statistics.median(samples)
    allure.attach(f"中位 {median:.0f}ms，最大 {max(samples):.0f}ms",
                  name="跨公网延迟", attachment_type=allure.attachment_type.TEXT)
    assert median < 3000, f"中位延迟 {median:.0f}ms，网络或服务异常"
