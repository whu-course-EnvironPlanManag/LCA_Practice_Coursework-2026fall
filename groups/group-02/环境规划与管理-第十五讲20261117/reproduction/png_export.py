# -*- coding: utf-8 -*-
"""PNG 静态图导出。

使用系统 Edge 无头截图，从已生成的离线 HTML 渲染 PNG。kaleido 0.2.1
捆绑的 Chrome 88 在部分 Windows 环境无法初始化（mf.dll 缺失导致
DXVAVDA 致命错误并挂起），因此采用 Edge 作为稳定方案；Edge 渲染的
HTML 与浏览器所见完全一致（WYSIWYG）。
"""

import os
import subprocess

_EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def _find_edge():
    for path in _EDGE_PATHS:
        if os.path.exists(path):
            return path
    return None


def export_png(html_path, png_path, width, height):
    """从离线 HTML 用 Edge 无头截图生成 PNG，返回是否成功。"""
    edge = _find_edge()
    if not edge:
        return False
    url = "file:///" + os.path.abspath(html_path).replace("\\", "/")
    try:
        subprocess.run(
            [edge, "--headless", "--disable-gpu", "--no-sandbox",
             "--hide-scrollbars", "--virtual-time-budget=8000",
             f"--window-size={width},{height}",
             f"--screenshot={png_path}", url],
            capture_output=True, timeout=90,
        )
    except Exception:
        return False
    return os.path.exists(png_path) and os.path.getsize(png_path) > 0
