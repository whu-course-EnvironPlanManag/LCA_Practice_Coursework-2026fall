# -*- coding: utf-8 -*-
"""合并Markdown章节、补术语表并生成DOCX。

运行：python build_report.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
REPORT = ROOT / "report" / "final_20261104"
OUT = REPORT / "C成员最终报告_LCOR_MAC与推荐方案.md"

TERMS = """
## 术语与缩写

| 缩写 | 英文全称 | 中文名称 | 本报告口径 |
| --- | --- | --- | --- |
| LIB | Lithium-ion Battery | 锂离子电池 | 退役动力电池 |
| LFP | Lithium Iron Phosphate | 磷酸铁锂 | 正极体系 |
| NMC | Nickel Manganese Cobalt Oxide | 镍锰钴三元 | 622/811技术情景 |
| NCA | Nickel Cobalt Aluminum Oxide | 镍钴铝 | 文献对比体系 |
| LCE | Lithium Carbonate Equivalent | 碳酸锂当量 | 功能单位，非合格品产量 |
| dMFA | dynamic Material Flow Analysis | 动态物质流分析 | 市域队列，与园区分开 |
| LCA | Life Cycle Assessment | 生命周期评价 | cradle-to-gate加运输 |
| TEA | Techno-Economic Analysis | 技术经济分析 | 年金+OPEX−收入 |
| GWP | Global Warming Potential | 全球变暖潜势 | GWP100，kg CO₂e |
| SOH | State of Health | 健康状态 | 容量情景，非筛选率 |
| EOL | End of Life | 寿命终止 | 退役阶段 |
| EPR | Extended Producer Responsibility | 生产者责任延伸 | 政策背景 |
| CRF | Capital Recovery Factor | 资本回收系数 | 7%/20年=0.09439293 |
| LCOR | Levelized Cost of Recycling | 平准化回收净成本 | 元/t LCE-eq |
| MAC | Marginal Abatement Cost | 边际减排成本 | 元/t CO₂e |
| MRV | Monitoring, Reporting, Verification | 监测报告核查 | 数字平台功能 |
| PPA | Power Purchase Agreement | 绿电购电协议 | 绿电锁价 |
| BMS | Battery Management System | 电池管理系统 | 拆解/重组部件 |
| FU | Functional Unit | 功能单位 | 1 t LCE-eq |
"""


def read(name):
    return (REPORT / name).read_text(encoding="utf-8")


def build_markdown():
    parts = [
        "# 退役动力电池循环利用园区规划：成员C LCOR、MAC与推荐方案（R1）\n",
        "\n**版本**：v3.0（2026-11-04）　**数据基准**：A R1　**功能单位**：1 t LCE-eq　"
        "**边界**：R1_2026_gate\n\n",
        "> 本报告为课程规划仿真，不是企业实测、法律合规认证或投资建议。"
        "价格均为规划参考价，未取得成交原件；补贴、碳信用与绿色溢价在基准中为0。\n\n",
        "**阅读顺序**：执行摘要 → 第3章指标 → 第4章投资与费用 → 第5章LCOR/MAC/推荐 → "
        "第6章管理 → 附录（来源、假设、政策测试、复现、清单对照）。\n\n",
        "**数据属性标注**：组内设定 / 文献原值 / 文献迁移 / 情景假设。"
        "缺失值保持UNKNOWN，不以目标值代填。\n\n",
        "---\n\n",
        read("ch00_summary.md"),
        "\n\n---\n\n",
        read("ch03_indicators.md"),
        "\n\n---\n\n",
        read("ch04_investment_cost.md"),
        "\n\n---\n\n",
        read("ch05_economics.md"),
        "\n\n---\n\n",
        read("ch06_management.md"),
        "\n\n---\n\n",
        read("appendix.md"),
        "\n\n---\n\n",
        TERMS,
    ]
    text = "".join(parts)
    OUT.write_text(text, encoding="utf-8")
    print("markdown ->", OUT, len(text), "chars")
    return text


def add_table(doc, rows):
    if not rows:
        return
    ncol = len(rows[0])
    table = doc.add_table(rows=len(rows), cols=ncol)
    table.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            if j < ncol:
                table.cell(i, j).text = cell


def build_docx(md_text):
    try:
        from docx import Document
        from docx.shared import Pt, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
    except ImportError:
        print("python-docx 未安装，跳过DOCX")
        return

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "宋体"
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.left_margin = section.right_margin = Cm(2.4)
        section.top_margin = section.bottom_margin = Cm(2.2)

    lines = md_text.splitlines()
    i = 0
    in_code = False
    table_buf = []
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("```"):
            in_code = not in_code
            i += 1
            continue
        if in_code:
            p = doc.add_paragraph(line)
            p.style = doc.styles["Normal"]
            p.runs[0].font.name = "Consolas"
            p.runs[0].font.size = Pt(8)
            i += 1
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.match(r"^:?-{2,}:?$", c) for c in cells):
                i += 1
                continue
            table_buf.append(cells)
            if i + 1 >= len(lines) or not lines[i + 1].startswith("|"):
                add_table(doc, table_buf)
                table_buf = []
            i += 1
            continue
        if line.startswith("# "):
            doc.add_heading(line[2:].strip(), level=1)
        elif line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=2)
        elif line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=3)
        elif line.startswith("!["):
            m = re.match(r"!\[[^\]]*\]\(([^)]+)\)", line)
            if m:
                img = (REPORT / m.group(1)).resolve()
                if img.exists():
                    doc.add_picture(str(img), width=Cm(15.5))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif line.startswith("> "):
            doc.add_paragraph(line[2:].strip())
        elif line.startswith("- "):
            doc.add_paragraph(line[2:].strip(), style="List Bullet")
        elif re.match(r"^\d+\. ", line):
            doc.add_paragraph(re.sub(r"^\d+\. ", "", line), style="List Number")
        elif line.strip() in ("---", ""):
            doc.add_paragraph("")
        else:
            txt = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
            txt = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", txt)
            doc.add_paragraph(txt)
        i += 1

    out = REPORT / "C成员最终报告_LCOR_MAC与推荐方案.docx"
    doc.save(out)
    print("docx ->", out)


if __name__ == "__main__":
    build_docx(build_markdown())
