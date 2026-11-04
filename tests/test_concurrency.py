"""并发用例：单线程跑出来的"对"，在多线程下可能全错。

为什么接口测试要关心并发：
  - ID 生成、库存扣减这类"读-改-写"操作，没加锁就会让两个请求拿到同一个号；
  - 线上事故常常不是逻辑写错，而是"两人同时点了提交"。

这里用标准库的 concurrent.futures 起线程池，直接打本地 mock 服务。
跑法：
    python -m pytest tests/test_concurrency.py -v
"""

import concurrent.futures
import statistics
import time

import allure
import pytest
import requests

pytestmark = [pytest.mark.regression, allure.feature("接口 · 并发")]

WORKERS = 10      # 同时压 10 个线程
COUNT = 30        # 每个用例发 30 个请求


def _create(base_url, headers, payload, index):
    body = {**payload, "firstname": f"并发{index}"}
    return requests.post(f"{base_url}/booking", json=body, headers=headers, timeout=10)


def test_concurrent_creates_get_unique_ids(base_url, auth_headers, booking_payload):
    """10 个线程同时创建 30 条，不能有两条拿到同一个 ID。"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        responses = list(pool.map(lambda i: _create(base_url, auth_headers, booking_payload, i), range(COUNT)))

    bad = [(r.status_code, r.text[:80]) for r in responses if r.status_code != 200]
    assert not bad, f"有请求没成功：{bad}"

    ids = [r.json()["bookingid"] for r in responses]
    assert len(set(ids)) == COUNT, f"出现了重复 ID（说明发号没加锁）：{sorted(ids)}"


def test_concurrent_creates_are_all_stored(base_url, auth_headers, booking_payload):
    """并发写入不能丢数据：30 条创建完，列表里必须正好 30 条。"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(lambda i: _create(base_url, auth_headers, booking_payload, i), range(COUNT)))

    listed = requests.get(f"{base_url}/booking", timeout=10).json()
    assert len(listed) == COUNT, f"丢了数据：期望 {COUNT} 条，实际 {len(listed)} 条"


def test_concurrent_reads_see_a_stable_picture(base_url, auth_headers, booking_payload):
    """一边写一边读，读到的条数不能忽多忽少（这里写完再读，验证读路径也不串）。"""
    for index in range(5):
        _create(base_url, auth_headers, booking_payload, index)

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        responses = list(pool.map(lambda _: requests.get(f"{base_url}/booking", timeout=10), range(20)))

    sizes = {len(r.json()) for r in responses}
    assert sizes == {5}, f"并发读到的条数不一致：{sorted(sizes)}"


def test_concurrent_patch_on_different_items_do_not_collide(base_url, auth_headers, booking_payload):
    """同时改不同的单子，互不干扰——改 A 不能把 B 的价格带跑。"""
    ids = [_create(base_url, auth_headers, booking_payload, i).json()["bookingid"] for i in range(5)]

    def patch(index):
        return requests.patch(
            f"{base_url}/booking/{ids[index]}",
            json={"totalprice": 1000 + index},
            headers=auth_headers,
            timeout=10,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(patch, range(5)))

    assert all(r.status_code == 200 for r in results), [r.status_code for r in results]
    for index, booking_id in enumerate(ids):
        body = requests.get(f"{base_url}/booking/{booking_id}", timeout=10).json()
        assert body["totalprice"] == 1000 + index, f"订单 {booking_id} 的价格被别的线程改了：{body['totalprice']}"


def test_concurrent_delete_only_one_wins(base_url, auth_headers, booking_payload):
    """5 个线程同时删同一条：只能有一个拿到 201，其余都是 404。

    这条守的是"删除必须原子"——先查在不在、再删，两步之间被人插进来，
    就会出现两个 201（都以为自己删成功了）。
    """
    booking_id = _create(base_url, auth_headers, booking_payload, 0).json()["bookingid"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        codes = list(pool.map(lambda _: requests.delete(f"{base_url}/booking/{booking_id}",
                                                        headers=auth_headers, timeout=10).status_code, range(5)))

    assert codes.count(201) == 1, f"删除不原子：{codes}"
    assert codes.count(404) == 4, f"重复删除应该都是 404：{codes}"


def test_health_check_latency(base_url):
    """性能冒烟：本机健康检查的中位延迟应该在毫秒级，慢了说明服务本身有问题。"""
    samples = []
    for _ in range(50):
        started = time.perf_counter()
        assert requests.get(f"{base_url}/ping", timeout=5).status_code == 200
        samples.append((time.perf_counter() - started) * 1000)

    median = statistics.median(samples)
    assert median < 200, f"健康检查中位延迟 {median:.1f}ms，太慢了（阈值 200ms）"
