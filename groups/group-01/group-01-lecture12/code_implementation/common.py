"""方向A公共输入检查。AI辅助实现；提示词与校验记录见README。"""
from pathlib import Path
import csv
import json
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_cohort"
OUTPUT = ROOT / "figures_output"
RESULTS = DATA / "results"
ELEMENTS = ("Li", "Ni", "Co", "Mn")


class InputError(ValueError):
    """输入缺失、单位不明或无法追溯；不替换为模拟数据。"""


def number(value, name, minimum=None, maximum=None):
    if isinstance(value, bool) or value is None or value == "":
        raise InputError(f"{name}缺少有效数值")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise InputError(f"{name}不是数值: {value}") from exc
    if not math.isfinite(result):
        raise InputError(f"{name}不能为NaN或无穷大")
    if minimum is not None and result < minimum:
        raise InputError(f"{name}小于{minimum}")
    if maximum is not None and result > maximum:
        raise InputError(f"{name}大于{maximum}")
    return result


def fraction(value, name):
    return number(value, name, 0, 1)


def source(row, context):
    for key in ("source", "source_locator"):
        if row.get(key) is None or not str(row.get(key, "")).strip():
            raise InputError(f"{context}缺少{key}，须记录出处及页码/表格/单元格")


def read_csv(name, required=(), allow_empty=False, directory=None):
    path = Path(directory or DATA) / name
    if not path.is_file():
        raise InputError(f"缺少输入表: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or set(required) - set(reader.fieldnames):
            raise InputError(f"{name}表头缺少: {sorted(set(required)-set(reader.fieldnames or []))}")
        rows = [row for row in reader if any(str(v or "").strip() for v in row.values())]
    if not rows and not allow_empty:
        raise InputError(f"{name}只有表头，等待组员补充真实输入")
    return rows


def write_csv(path, rows, fieldnames=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and not fieldnames:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def load_config(path=None):
    result = json.loads(Path(path or DATA / "model_config.json").read_text(encoding="utf-8-sig"))
    result["policy_rules"] = json.loads((DATA / "policy_rules.json").read_text(encoding="utf-8-sig"))
    return result
