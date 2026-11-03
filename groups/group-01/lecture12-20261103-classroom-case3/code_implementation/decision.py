"""严格非支配排序与归一化理想点距离；保留退化前沿，不伪造拐点。"""
import numpy as np
from common import InputError


def pareto_frontier(records, objectives=("gwp_kg_per_t_lce", "lcor_cny_per_t_lce")):
    if not records:
        return [], {}
    values = np.array([[row[key] for key in objectives] for row in records], dtype=float)
    if not np.isfinite(values).all():
        raise InputError("帕累托目标必须为有限值")
    # O(n²)在本任务500—数千组范围内足够，不需要外部多目标库。
    mask = np.ones(len(records), dtype=bool)
    for i, row in enumerate(values):
        if np.any(np.all(values <= row, axis=1) & np.any(values < row, axis=1)):
            mask[i] = False
    selected = np.flatnonzero(mask)
    # 相同目标可对应不同空间/收集方案，全部保留，不能擅自当同一个物理方案。
    frontier_values = values[selected]
    span = np.ptp(frontier_values, axis=0)
    normalized = np.divide(frontier_values-frontier_values.min(axis=0), span,
                           out=np.zeros_like(frontier_values), where=span > 0)
    distances = np.linalg.norm(normalized, axis=1)
    frontier = [{**records[i], "normalized_gwp": float(normalized[j, 0]),
                 "normalized_lcor": float(normalized[j, 1]), "utopia_distance": float(distances[j])}
                for j, i in enumerate(selected)]
    # 明确固定并列规则：先距离，再原始输入顺序，不宣称唯一物理拐点。
    anchors = {"A_Cost_Min": frontier[int(np.argmin(frontier_values[:, 1]))],
               "B_Utopia_Distance_Min": frontier[int(np.argmin(distances))],
               "C_GWP_Min": frontier[int(np.argmin(frontier_values[:, 0]))]}
    return frontier, anchors
