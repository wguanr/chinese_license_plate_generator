#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车牌生成器可视化模块

提供Dashboard界面和图库功能，用于查看和管理生成的车牌资产。
兼容Linux/Windows/macOS平台。
"""

from .app import PlateGeneratorApp, create_app

# 为了向后兼容，保留旧名称
PlateVisualizationApp = PlateGeneratorApp

__version__ = '1.0.0'
__all__ = ['PlateGeneratorApp', 'PlateVisualizationApp', 'create_app']
