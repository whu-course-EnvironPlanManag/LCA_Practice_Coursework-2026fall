"""只读提取提供的20张.xls；保留原值、表名、单元格和年份，不推算电池安装量。"""
from pathlib import Path
import hashlib
import re
from common import ROOT, DATA, InputError, write_csv, write_json


def column_name(index):
    result = ""
    while index:
        index, rem = divmod(index-1, 26)
        result = chr(65+rem)+result
    return result


def extract_yearbook(directory=None):
    try:
        import xlrd
    except ImportError as exc:
        raise InputError("读取.xls需要xlrd：python -m pip install -r code_implementation/requirements.txt") from exc
    folder = Path(directory) if directory else DATA / "raw/湖北统计年鉴2025-定"
    files = sorted(folder.rglob("*.xls"))
    if not files:
        raise InputError(f"找不到年鉴.xls: {folder}")
    cells, context, manifest = [], [], []
    for path in files:
        book = xlrd.open_workbook(path)
        file_ref = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest.append({"file": file_ref, "sha256": digest, "sheets": book.sheet_names()})
        for sheet in book.sheets():
            for r in range(sheet.nrows):
                for c in range(sheet.ncols):
                    value = sheet.cell_value(r, c)
                    if value == "":
                        continue
                    cells.append({"source": file_ref, "sheet": sheet.name,
                                  "cell": f"{column_name(c+1)}{r+1}", "value": value,
                                  "cell_type": sheet.cell_type(r, c), "source_sha256": digest})
        sheet = book.sheet_by_index(0)
        def add(r, c, year, region, indicator, unit, category, note):
            value = sheet.cell_value(r-1, c-1)
            if not isinstance(value, (int, float)):
                raise InputError(f"年鉴固定提取单元格已变化: {path.name}/{r}/{c}")
            context.append({"year": year, "region": region, "indicator": indicator, "value": value,
                            "unit": unit, "category": category, "model_usage": note,
                            "source": file_ref, "source_locator": f"{sheet.name}!{column_name(c)}{r}",
                            "source_sha256": digest})
        if path.name.startswith("1607-"):
            for c in range(3, 14):
                add(7, c, int(sheet.cell_value(4, c-1)), "湖北省", "私人汽车拥有量", "辆", "all_vehicle_stock",
                    "含非新能源车辆，不能直接作为EV保有量或安装队列；年份间隔不连续")
        elif path.name.startswith("1606-"):
            add(10, 3, 2024, "湖北省", "民用汽车拥有量", "辆", "all_vehicle_stock", "不是新能源汽车保有量")
        elif path.name.startswith("1308-"):
            add(20, 5, 2024, "湖北省", "规模以上工业新能源汽车产量", "辆", "industrial_production", "不是湖北新增注册量；含跨省销售")
            add(40, 5, 2024, "湖北省", "规模以上工业锂离子电池产量", "只(自然只)", "industrial_production", "电芯只数不等于动力整包数量或kWh；不得直接转换")
        elif path.name.startswith("0607-"):
            for c in range(3, 8):
                year = int(sheet.cell_value(4, c-1))
                for r, name in ((7, "电力生产量"), (8, "火电生产量"), (9, "水电核电风电及其他生产量"), (11, "电力消费量")):
                    add(r, c, year, "湖北省", name, "亿kWh", "electricity_statistics", "生产结构不等于消费侧LCA电网因子；2025版年鉴中该表止于2023年")
        elif path.name.startswith("1005-"):
            for r in range(9, 21):
                city = re.sub(r"\s+", "", str(sheet.cell_value(r-1, 0)))
                add(r, 3, 2024, city, "全年用电量", "亿kWh", "city_electricity", "仅12个主要城市，不代表全省全部行政单元")
                add(r, 4, 2024, city, "工业用电量", "亿kWh", "city_electricity", "不是回收工厂可用剩余容量或电价")
    write_csv(DATA / "yearbook_cells.csv", cells)
    write_csv(DATA / "hubei_yearbook_context.csv", context)
    write_json(DATA / "yearbook_source_manifest.json", manifest)
    print(f"年鉴读取完成：{len(files)}个文件，{len(cells)}个非空单元格，{len(context)}条带口径的背景统计。")
    return context


if __name__ == "__main__":
    extract_yearbook()
