#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基础PCG算法类

定义PCG算法的核心接口，专注于算法逻辑而非配置管理。
"""

from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional
import random

from .exceptions import AlgorithmError, ValidationError, handle_pcg_errors


class BasePCGAlgorithm(ABC):
    """
    PCG算法基础接口
    
    专注于核心算法逻辑，配置管理和I/O功能已分离到其他模块。
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        """
        初始化基础PCG算法
        
        Args:
            name: 算法名称
            version: 算法版本
        """
        self.name = name
        self.version = version
        self._random = random.Random()
        self._parameters = {}  # 存储算法参数
    
    @abstractmethod
    def generate_variants(self, base_params: Any, count: int, **kwargs) -> List[Any]:
        """
        生成变体 - 核心算法接口
        
        Args:
            base_params: 基础参数
            count: 生成数量
            **kwargs: 其他参数
            
        Returns:
            变体列表
        """
        pass
    
    @abstractmethod 
    def validate_parameters(self, parameters: Any) -> bool:
        """
        验证参数 - 快速验证接口
        
        Args:
            parameters: 待验证的参数
            
        Returns:
            是否有效
        """
        pass
    
    def set_parameter(self, key: str, value: Any):
        """
        设置算法参数
        
        Args:
            key: 参数键
            value: 参数值
        """
        self._parameters[key] = value
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """
        获取算法参数
        
        Args:
            key: 参数键
            default: 默认值
            
        Returns:
            参数值
        """
        return self._parameters.get(key, default)
    
    def get_all_parameters(self) -> Dict[str, Any]:
        """
        获取所有参数
        
        Returns:
            参数字典
        """
        return self._parameters.copy()
    
    def set_random_seed(self, seed: int):
        """
        设置随机种子
        
        Args:
            seed: 随机种子
        """
        self._random.seed(seed)
    
    def get_random_value(self, min_val: float, max_val: float) -> float:
        """
        获取随机值
        
        Args:
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            随机值
        """
        return self._random.uniform(min_val, max_val)
    
    def get_random_choice(self, choices: List[Any]) -> Any:
        """
        随机选择
        
        Args:
            choices: 选择列表
            
        Returns:
            随机选择的元素
        """
        if not choices:
            raise AlgorithmError("选择列表不能为空", algorithm_name=self.name)
        return self._random.choice(choices)
    
    def get_info(self) -> Dict[str, str]:
        """
        获取基本信息
        
        Returns:
            算法基本信息
        """
        return {
            "name": self.name,
            "version": self.version,
            "class": self.__class__.__name__
        }
    
    @handle_pcg_errors(reraise_as=AlgorithmError)
    def safe_generate_variants(self, base_params: Any, count: int, **kwargs) -> List[Any]:
        """
        安全的变体生成（带异常处理）
        
        Args:
            base_params: 基础参数
            count: 生成数量
            **kwargs: 其他参数
            
        Returns:
            变体列表
            
        Raises:
            AlgorithmError: 算法执行失败
        """
        if not self.validate_parameters(base_params):
            raise ValidationError("基础参数验证失败")
        
        if count <= 0:
            raise AlgorithmError("生成数量必须大于0", algorithm_name=self.name)
        
        return self.generate_variants(base_params, count, **kwargs)
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', version='{self.version}')"
    
    def __repr__(self) -> str:
        return self.__str__()


class AlgorithmRegistry:
    """
    简化的算法注册表
    
    提供算法类的注册和获取功能。
    """
    
    _algorithms: Dict[str, type] = {}
    
    @classmethod
    def register(cls, algorithm_class: type):
        """
        注册算法类
        
        Args:
            algorithm_class: 算法类
            
        Raises:
            AlgorithmError: 算法类无效
        """
        if not issubclass(algorithm_class, BasePCGAlgorithm):
            raise AlgorithmError(f"算法类必须继承自BasePCGAlgorithm: {algorithm_class}")
        
        cls._algorithms[algorithm_class.__name__] = algorithm_class
    
    @classmethod
    def get_algorithm_class(cls, name: str) -> Optional[type]:
        """
        获取算法类
        
        Args:
            name: 算法名称
            
        Returns:
            算法类或None
        """
        return cls._algorithms.get(name)
    
    @classmethod
    def list_algorithms(cls) -> List[str]:
        """
        列出所有注册的算法
        
        Returns:
            算法名称列表
        """
        return list(cls._algorithms.keys())
    
    @classmethod
    def create_algorithm(cls, name: str, *args, **kwargs) -> Optional[BasePCGAlgorithm]:
        """
        创建算法实例
        
        Args:
            name: 算法名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            算法实例或None
        """
        algorithm_class = cls.get_algorithm_class(name)
        if algorithm_class:
            return algorithm_class(*args, **kwargs)
        return None
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        检查算法是否已注册
        
        Args:
            name: 算法名称
            
        Returns:
            是否已注册
        """
        return name in cls._algorithms
    
    @classmethod
    def clear_registry(cls):
        """清空注册表（主要用于测试）"""
        cls._algorithms.clear()


# 装饰器：自动注册算法
def register_algorithm(algorithm_class: type):
    """
    自动注册算法的装饰器
    
    Args:
        algorithm_class: 算法类
        
    Returns:
        算法类
    """
    AlgorithmRegistry.register(algorithm_class)
    return algorithm_class


# 简化的算法基类变体（适用于简单场景）
class SimpleAlgorithm(BasePCGAlgorithm):
    """
    简化的算法基类
    
    适用于不需要复杂参数验证的简单算法。
    """
    
    def validate_parameters(self, parameters: Any) -> bool:
        """默认验证：总是返回True"""
        return True


# 算法工厂
class AlgorithmFactory:
    """
    算法工厂
    
    提供便捷的算法创建和管理功能。
    """
    
    @staticmethod
    def create_algorithm(algorithm_type: str, name: str = None, **kwargs) -> BasePCGAlgorithm:
        """
        创建算法实例
        
        Args:
            algorithm_type: 算法类型名称
            name: 算法实例名称（可选）
            **kwargs: 算法参数
            
        Returns:
            算法实例
            
        Raises:
            AlgorithmError: 创建失败
        """
        algorithm = AlgorithmRegistry.create_algorithm(algorithm_type, name or algorithm_type, **kwargs)
        if algorithm is None:
            raise AlgorithmError(f"未找到算法类型: {algorithm_type}")
        return algorithm
    
    @staticmethod
    def get_available_algorithms() -> Dict[str, type]:
        """
        获取可用的算法类型
        
        Returns:
            算法类型字典
        """
        return AlgorithmRegistry._algorithms.copy()
    
    @staticmethod
    def create_batch_algorithms(algorithm_configs: List[Dict[str, Any]]) -> List[BasePCGAlgorithm]:
        """
        批量创建算法实例
        
        Args:
            algorithm_configs: 算法配置列表，每个配置包含type和其他参数
            
        Returns:
            算法实例列表
        """
        algorithms = []
        for config in algorithm_configs:
            if 'type' not in config:
                raise AlgorithmError("算法配置必须包含type字段")
            
            algorithm_type = config.pop('type')
            algorithm = AlgorithmFactory.create_algorithm(algorithm_type, **config)
            algorithms.append(algorithm)
        
        return algorithms


# 算法性能监控装饰器
def monitor_performance(func):
    """
    算法性能监控装饰器
    
    用于监控算法执行时间和资源使用。
    """
    def wrapper(self, *args, **kwargs):
        import time
        start_time = time.time()
        
        try:
            result = func(self, *args, **kwargs)
            execution_time = time.time() - start_time
            
            # 简单的性能日志
            if hasattr(self, 'name'):
                print(f"⏱️  算法 '{self.name}' 执行时间: {execution_time:.3f}秒")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ 算法执行失败，耗时: {execution_time:.3f}秒，错误: {e}")
            raise
    
    return wrapper


# 验证辅助函数
def validate_algorithm_input(parameters: Any, expected_type: type = None) -> bool:
    """
    通用的算法输入验证
    
    Args:
        parameters: 待验证的参数
        expected_type: 期望的参数类型
        
    Returns:
        是否有效
    """
    if parameters is None:
        return False
    
    if expected_type and not isinstance(parameters, expected_type):
        return False
    
    return True 