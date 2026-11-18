"""按产品匹配作者系数，独立核对 2022 年全球产出、进口及出口。"""
import csv
from collections import defaultdict

import openpyxl


def convert_baseline(revision, output, write):
    streams = [
        ('production', 'Production', '1.*/Raw data*/2022.csv', '3.P content*', '1.*/Agricultural products_P*.xlsx'),
        ('imports', 'Import Quantity', '2.*/*imports/2022.csv', '4.P content*', '2.*/*imports*.xlsx'),
        ('exports', 'Export Quantity', '2.*/*exports/2022.csv', '4.P content*', '2.*/*exports*.xlsx'),
    ]
    details, comparison = [], []
    for stream, element, raw, dictionary, reference in streams:
        book = openpyxl.load_workbook(next(revision.glob(dictionary)), read_only=True, data_only=True)
        coefficients = {str(name).strip(): (category, factor)
                        for name, category, factor in list(book.active.iter_rows(max_col=3, values_only=True))[1:]
                        if name}
        book.close()
        totals = defaultdict(float)
        with next(revision.glob(raw)).open(encoding='utf-8-sig') as file:
            for row in csv.DictReader(file):
                if (row['Area'], row['Year'], row['Element']) != ('World', '2022', element):
                    continue
                item = row['Item'].strip()
                category, factor = coefficients.get(item, ('', None))
                status = '已换算'
                phosphorus = None
                if row['Unit'] != 't':
                    status = '单位非吨或缺失'
                elif not row['Value']:
                    status = '数量缺失'
                elif factor is None:
                    status = '未匹配系数'
                else:
                    phosphorus = float(row['Value']) * factor
                    totals[category] += phosphorus
                details.append(dict(stream=stream, year=2022, item=item, category=category,
                                    unit=row['Unit'], quantity=row['Value'], t_P_per_t=factor,
                                    P_t=phosphorus, status=status))
        book = openpyxl.load_workbook(next(revision.glob(reference)), read_only=True, data_only=True)
        records = iter(book.worksheets[0].values)
        column = next(records).index(2022)
        published = {r[1]: r[column] for r in records if r[0] == 'World'}
        book.close()
        if not published or not totals:
            raise ValueError(f'{stream} 缺少全球类别核验数据')
        for category in sorted(totals.keys() | published.keys()):
            value = totals.get(category)
            target = published.get(category)
            difference = value - target if target is not None and value is not None else None
            comparison.append(dict(stream=stream, year=2022, category=category, calculated_t_P=value,
                                   author_t_P=target, difference_t_P=difference))
    write(output/'product_conversion_2022.csv', details)
    write(output/'product_comparison_2022.csv', comparison)
