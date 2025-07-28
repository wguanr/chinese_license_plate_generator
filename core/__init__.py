#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PCG-USD材质系统核心模块"""

from .config import (
    ConfigSchema,
    DEFAULT_CONFIG
)

from .base_algorithm import (
    BasePCGAlgorithm,
    SimpleAlgorithm,
)



from .texture_classifier import (
    TextureClassifier,
    create_texture_classifier
)

__all__ = [
    'ConfigSchema',
    'DEFAULT_CONFIG',
    'TextureClassifier',
    'create_texture_classifier'
]

__version__ = '2.0.0' 