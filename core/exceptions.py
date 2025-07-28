#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PCG-USD系统异常定义

定义了系统统一的异常层次结构，便于错误处理和调试。
"""

from typing import Any, Optional, Dict


class PCGSystemError(Exception):
    """
    PCG系统基础异常
    
    所有PCG系统相关异常的基类。
    """
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self) -> str:
        result = self.message
        if self.error_code:
            result = f"[{self.error_code}] {result}"
        return result


class MaterialParameterError(PCGSystemError):
    """
    材质参数相关异常
    
    用于材质参数验证、创建和处理过程中的错误。
    """
    
    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value
        if field:
            self.details['field'] = field
        if value is not None:
            self.details['value'] = value


class TextureValidationError(MaterialParameterError):
    """贴图验证失败异常"""
    
    def __init__(self, texture_path: str, message: str = None):
        message = message or f"贴图验证失败: {texture_path}"
        super().__init__(message, field="texture_path", value=texture_path, error_code="TEX_INVALID")
        self.texture_path = texture_path


class USDIntegrationError(PCGSystemError):
    """
    USD集成相关异常
    
    用于USD库集成、舞台操作和材质绑定过程中的错误。
    """
    
    def __init__(self, message: str, stage_path: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.stage_path = stage_path
        if stage_path:
            self.details['stage_path'] = stage_path


class MDLProcessingError(PCGSystemError):
    """
    MDL处理相关异常
    
    用于MDL文件生成、解析和处理过程中的错误。
    """
    
    def __init__(self, message: str, mdl_path: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.mdl_path = mdl_path
        if mdl_path:
            self.details['mdl_path'] = mdl_path


class ValidationError(PCGSystemError):
    """
    通用验证失败异常
    
    用于各种参数和数据验证失败的情况。
    """
    
    def __init__(self, message: str, field: str = None, value: Any = None, 
                 validation_type: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value
        self.validation_type = validation_type
        
        if field:
            self.details['field'] = field
        if value is not None:
            self.details['value'] = value
        if validation_type:
            self.details['validation_type'] = validation_type


class DependencyError(PCGSystemError):
    """
    依赖相关异常
    
    用于依赖缺失、版本不兼容等问题。
    """
    
    def __init__(self, message: str, dependency_name: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.dependency_name = dependency_name
        if dependency_name:
            self.details['dependency'] = dependency_name


class ConfigurationError(PCGSystemError):
    """
    配置相关异常
    
    用于配置文件格式错误、参数缺失等问题。
    """
    
    def __init__(self, message: str, config_file: str = None, config_key: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.config_file = config_file
        self.config_key = config_key
        
        if config_file:
            self.details['config_file'] = config_file
        if config_key:
            self.details['config_key'] = config_key


class AlgorithmError(PCGSystemError):
    """
    算法执行异常
    
    用于PCG算法执行过程中的错误。
    """
    
    def __init__(self, message: str, algorithm_name: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.algorithm_name = algorithm_name
        if algorithm_name:
            self.details['algorithm'] = algorithm_name


# 便捷的异常创建函数
def create_texture_error(texture_path: str, message: str = None) -> TextureValidationError:
    """创建贴图验证异常"""
    return TextureValidationError(texture_path, message)


def create_validation_error(field: str, value: Any, message: str = None) -> ValidationError:
    """创建验证异常"""
    if not message:
        message = f"字段 '{field}' 验证失败，值: {value}"
    return ValidationError(message, field=field, value=value)


def create_dependency_error(dependency_name: str, message: str = None) -> DependencyError:
    """创建依赖异常"""
    if not message:
        message = f"依赖 '{dependency_name}' 不可用"
    return DependencyError(message, dependency_name=dependency_name)


# 异常处理装饰器
def handle_pcg_errors(default_return=None, reraise_as=None):
    """
    PCG异常处理装饰器
    
    Args:
        default_return: 发生异常时的默认返回值
        reraise_as: 重新抛出为指定的异常类型
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except PCGSystemError:
                # PCG系统异常直接重新抛出
                raise
            except Exception as e:
                if reraise_as:
                    raise reraise_as(f"函数 {func.__name__} 执行失败: {str(e)}") from e
                elif default_return is not None:
                    return default_return
                else:
                    # 包装为PCG系统异常
                    raise PCGSystemError(f"函数 {func.__name__} 执行失败: {str(e)}") from e
        return wrapper
    return decorator


# 错误码常量
class ErrorCodes:
    """错误码常量"""
    
    # 材质参数错误
    MATERIAL_INVALID_PARAMETER = "MAT_INVALID_PARAM"
    MATERIAL_MISSING_TEXTURE = "MAT_MISSING_TEX"
    MATERIAL_INVALID_VALUE = "MAT_INVALID_VAL"
    
    # USD错误
    USD_STAGE_NOT_FOUND = "USD_STAGE_NOT_FOUND"
    USD_MATERIAL_CREATE_FAILED = "USD_MAT_CREATE_FAIL"
    USD_BINDING_FAILED = "USD_BIND_FAIL"
    
    # MDL错误
    MDL_TEMPLATE_NOT_FOUND = "MDL_TEMPLATE_NOT_FOUND"
    MDL_GENERATION_FAILED = "MDL_GEN_FAIL"
    MDL_INVALID_SYNTAX = "MDL_INVALID_SYNTAX"
    
    # 依赖错误
    DEPENDENCY_MISSING = "DEP_MISSING"
    DEPENDENCY_VERSION_INCOMPATIBLE = "DEP_VERSION_INCOMPAT"
    
    # 配置错误
    CONFIG_FILE_NOT_FOUND = "CFG_FILE_NOT_FOUND"
    CONFIG_INVALID_FORMAT = "CFG_INVALID_FORMAT"
    CONFIG_MISSING_KEY = "CFG_MISSING_KEY" 