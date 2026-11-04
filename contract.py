"""接口契约快照：记录响应里每个字段的类型，下次跑时比对。

解决什么问题：后端改字段名、把数字改成字符串，功能测试可能照样过
（因为断言只看值），但前端会炸。契约测试专门盯"结构有没有变"。

用法：
    python contract.py                   # 生成/更新快照
    pytest tests/test_contract.py        # 校验

快照首次运行为空时自动生成，之后变动就会失败。
"""

import json
from pathlib import Path

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"


def schema_of(value):
    """把一个 JSON 值压成"结构描述"，不含具体数据"""
    if isinstance(value, dict):
        return {key: schema_of(sub) for key, sub in sorted(value.items())}
    if isinstance(value, list):
        return [schema_of(value[0])] if value else []
    return type(value).__name__


def compare(name, payload, update=False):
    """返回 (是否一致, 差异说明)。update=True 时直接写快照。"""
    path = SNAPSHOT_DIR / f"{name}.json"
    actual = schema_of(payload)
    if update or not path.exists():
        path.write_text(json.dumps(actual, ensure_ascii=False, indent=2), encoding="utf-8")
        return True, f"已写入快照 {path.name}"
    expected = json.loads(path.read_text(encoding="utf-8"))
    if expected == actual:
        return True, "结构未变"
    diffs = []
    for key in sorted(set(expected) | set(actual)):
        old, new = expected.get(key, "<缺>"), actual.get(key, "<缺>")
        if old != new:
            diffs.append(f"{key}: {old} → {new}")
    return False, "结构变了：" + "；".join(diffs)