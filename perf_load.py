"""零依赖性能基线：并发梯度 + p50/p95/p99 + 阈值判定。

和功能测试的分工：
  - 功能测试问"对不对"；
  - 性能基线问"多快、并发上去会不会塌、有没有退化"。

为什么不用 JMeter/Locust：这个项目坚持"不装包也能跑"，标准库的线程池足够量
一个单机 mock 的延迟分布。真到要压几千并发，再上专业工具也不迟。

用法：
    python perf_load.py                                # 默认 120 请求，并发 1/5/20
    python perf_load.py --requests 300 --levels 1,10,50
    python perf_load.py --p95-ping 300 --p95-list 500  # CI 机器慢，放宽阈值
"""

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import mock_server
import requests

PAYLOAD = {
    "firstname": "压测",
    "lastname": "客",
    "totalprice": 288,
    "depositpaid": True,
    "bookingdates": {"checkin": "2026-11-10", "checkout": "2026-11-12"},
}
SCENARIOS = ("ping", "list", "create")


def percentile(values, ratio):
    """不用 numpy 的百分位：排序后按比例取下标，够用。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(ratio * (len(ordered) - 1))))
    return ordered[index]


def measure(base_url, headers, scenario, level, total):
    """用 level 个线程打 total 个请求，返回这一轮的统计。"""
    latencies = []
    codes = []
    cursor = {"index": 0}
    lock = threading.Lock()

    def worker():
        while True:
            with lock:
                index = cursor["index"]
                if index >= total:
                    return
                cursor["index"] += 1
            started = time.perf_counter()
            if scenario == "ping":
                response = requests.get(f"{base_url}/ping", timeout=10)
            elif scenario == "list":
                response = requests.get(f"{base_url}/booking?page=1&size=20", timeout=10)
            else:
                body = {**PAYLOAD, "firstname": f"压测{index}"}
                response = requests.post(f"{base_url}/booking", json=body, headers=headers, timeout=10)
            elapsed = (time.perf_counter() - started) * 1000
            with lock:
                latencies.append(elapsed)
                codes.append(response.status_code)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=level) as pool:
        list(pool.map(lambda _: worker(), range(level)))
    wall = time.perf_counter() - started

    return {
        "scenario": scenario,
        "level": level,
        "count": len(latencies),
        "p50": percentile(latencies, 0.50),
        "p95": percentile(latencies, 0.95),
        "p99": percentile(latencies, 0.99),
        "max": max(latencies) if latencies else 0.0,
        "rps": len(latencies) / wall if wall else 0.0,
        "errors": sum(1 for code in codes if code not in (200, 201)),
    }


def main():
    parser = argparse.ArgumentParser(description="零依赖性能基线（本地 mock）")
    parser.add_argument("--requests", type=int, default=120, help="每个场景每个并发级的请求数")
    parser.add_argument("--levels", default="1,5,20", help="并发梯度，逗号分隔，例如 1,5,20")
    parser.add_argument("--p95-ping", type=float, default=100.0, help="ping 的 p95 阈值（毫秒）")
    parser.add_argument("--p95-list", type=float, default=200.0, help="列表的 p95 阈值（毫秒）")
    parser.add_argument("--p95-create", type=float, default=300.0, help="创建的 p95 阈值（毫秒）")
    parser.add_argument("--json", default="perf-results.json", help="结果另存为 JSON")
    args = parser.parse_args()

    levels = [int(item) for item in args.levels.split(",") if item.strip()]
    thresholds = {"ping": args.p95_ping, "list": args.p95_list, "create": args.p95_create}

    server, base_url = mock_server.start(port=0)
    token = requests.post(
        f"{base_url}/auth", json={"username": "admin", "password": "password123"}, timeout=5
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # 预热，避免把首次请求的初始化耗时算进去
        for _ in range(10):
            requests.get(f"{base_url}/ping", timeout=5)

        results = []
        print(f"被测服务: {base_url}    每级请求数: {args.requests}    并发梯度: {levels}\n")
        print(f"{'场景':<8}{'并发':>4}{'请求数':>7}{'p50':>9}{'p95':>9}{'p99':>9}{'最大':>9}{'吞吐':>10}{'错误':>6}")
        for scenario in SCENARIOS:
            for level in levels:
                mock_server.STORE.reset()          # 每个用例都从干净库存开始
                row = measure(base_url, headers, scenario, level, args.requests)
                results.append(row)
                print(
                    f"{row['scenario']:<8}{row['level']:>4}{row['count']:>7}"
                    f"{row['p50']:>8.1f}ms{row['p95']:>8.1f}ms{row['p99']:>8.1f}ms"
                    f"{row['max']:>8.1f}ms{row['rps']:>9.1f}/s{row['errors']:>5}"
                )
            print()

        failures = []
        for row in results:
            limit = thresholds[row["scenario"]]
            if row["p95"] > limit:
                failures.append(f"{row['scenario']}@{row['level']} 并发 p95={row['p95']:.1f}ms 超过阈值 {limit}ms")
            if row["errors"]:
                failures.append(f"{row['scenario']}@{row['level']} 并发出现 {row['errors']} 个错误响应")

        if failures:
            print("性能阈值未通过：")
            for item in failures:
                print(f"  - {item}")
        else:
            print("性能阈值全部通过 ✅")

        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump({"base_url": base_url, "thresholds": thresholds, "results": results,
                       "failures": failures}, handle, ensure_ascii=False, indent=2)
        print(f"原始数据: {args.json}")
        return 1 if failures else 0
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
