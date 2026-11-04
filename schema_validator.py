"""极简 JSON Schema 校验器 —— 只用标准库，够这个项目用就行。

为什么要它：`contract.py` 的快照记录的是"结构长什么样"（字段、类型），
但它管不了"值合不合法"——比如 totalprice 是 -1，类型上仍是 int，快照照样过。
JSON Schema 能把规则写死：必填、范围、枚举、日期格式，全都算契约。

支持的关键字（故意只做子集，用不到的不实现）：
    type / required / properties / additionalProperties / items
    enum / minimum / maximum / minLength / format(date) / $ref(同目录文件)

用法：
    from schema_validator import load, validate
    validate(response.json(), load("schema/booking_created.schema.json"), "创建响应")
"""

import json
import os
import re
from datetime import datetime

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SchemaError(AssertionError):
    """校验失败。继承 AssertionError，pytest 直接抛出来就能看到清楚的报错。"""


def _is_type(value, expected):
    """注意 bool 是 int 的子类：True 不能算 integer/number。"""
    if expected in ("integer", "number"):
        if isinstance(value, bool):
            return False
        return isinstance(value, int) if expected == "integer" else isinstance(value, (int, float))
    mapping = {
        "object": dict,
        "array": list,
        "string": str,
        "boolean": bool,
        "null": type(None),
    }
    return isinstance(value, mapping[expected])


def _check(value, schema, path):
    errors = []
    expected = schema.get("type")
    if expected and not _is_type(value, expected):
        errors.append(f"{path}: 期望 {expected}，实际是 {type(value).__name__}（{value!r}）")
        return errors          # 类型都不对，后面的规则没有意义

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: 只能是 {schema['enum']} 之一，实际 {value!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: 不能小于 {schema['minimum']}，实际 {value}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: 不能大于 {schema['maximum']}，实际 {value}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: 长度不能小于 {schema['minLength']}，实际 {value!r}")
        if schema.get("format") == "date":
            if not _DATE.match(value):
                errors.append(f"{path}: 日期要写成 YYYY-MM-DD，实际 {value!r}")
            else:
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    errors.append(f"{path}: 不是真实存在的日期，实际 {value!r}")

    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{path}.{name}: 缺少必填字段")
        properties = schema.get("properties", {})
        for name, rule in properties.items():
            if name in value:
                errors.extend(_check(value[name], rule, f"{path}.{name}"))
        if schema.get("additionalProperties") is False:
            for name in value:
                if name not in properties:
                    errors.append(f"{path}.{name}: 契约里没有这个字段")

    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            errors.extend(_check(item, schema["items"], f"{path}[{index}]"))

    return errors


def validate(instance, schema, where="响应"):
    """校验不通过时抛 SchemaError，把所有问题一次列出来。"""
    errors = _check(instance, schema, where)
    if errors:
        raise SchemaError("契约不符：\n  - " + "\n  - ".join(errors))


def load(path):
    """读一份 schema，并把 $ref 就地展开成真实规则（只支持同目录文件）。"""
    path = os.path.abspath(path)
    with open(path, encoding="utf-8") as handle:
        schema = json.load(handle)
    return _expand_refs(schema, os.path.dirname(path))


def _expand_refs(node, base):
    if isinstance(node, dict):
        if "$ref" in node:
            return load(os.path.join(base, node["$ref"]))
        return {key: _expand_refs(value, base) for key, value in node.items()}
    if isinstance(node, list):
        return [_expand_refs(item, base) for item in node]
    return node
