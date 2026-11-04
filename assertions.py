"""通用断言：把"检查响应"这件事从每个用例里抽出来。

为什么需要：如果每个用例都自己写 `assert resp.status_code == 200`，
失败时报错信息只有一行数字，排查得靠猜。这里的断言会在失败时
把实际响应体一起打出来，省掉一次复现。
"""

import json


def assert_status(response, expected, note=""):
    """检查状态码，失败时把响应体一起抛出来"""
    if response.status_code != expected:
        body = response.text[:600]
        raise AssertionError(
            f"{note + '：' if note else ''}期望状态码 {expected}，实际 {response.status_code}\n"
            f"请求：{response.request.method} {response.request.url}\n"
            f"响应体：{body}"
        )
    return response


def assert_json_field(payload, field, expected, note=""):
    """检查 JSON 里的某个字段，失败时说明实际是什么"""
    actual = payload.get(field, "<字段不存在>") if isinstance(payload, dict) else "<不是对象>"
    if actual != expected:
        raise AssertionError(
            f"{note + '：' if note else ''}字段 {field} 期望 {expected!r}，实际 {actual!r}"
        )
    return actual


def assert_fields_present(payload, fields, note=""):
    """检查一组字段都存在（不关心值）"""
    missing = [f for f in fields if not isinstance(payload, dict) or f not in payload]
    if missing:
        raise AssertionError(
            f"{note + '：' if note else ''}缺少字段 {missing}；实际字段 {sorted(payload or {})}"
        )
    return True


def assert_error_message(response, contains, note=""):
    """检查错误响应里有没有说明具体原因 —— 只说'失败了'的接口是难用的"""
    try:
        payload = response.json()
    except (json.JSONDecodeError, ValueError):
        raise AssertionError(f"{note + '：' if note else ''}响应不是 JSON：{response.text[:300]}")
    text = json.dumps(payload, ensure_ascii=False)
    if contains not in text:
        raise AssertionError(f"{note + '：' if note else ''}错误信息里没有「{contains}」；实际：{text[:400]}")
    return text