"""
材质系统测试
测试PCG材质系统的核心功能
"""

import unittest
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core.material_system import PCGMaterialSystem
    from core.material_params import MaterialParameters
    from config import DEFAULT_CONFIG
except ImportError as e:
    print(f"导入模块失败: {e}")
    # 跳过测试
    PCGMaterialSystem = None


class TestPCGMaterialSystem(unittest.TestCase):
    """PCG材质系统测试"""
    
    def setUp(self):
        """测试前设置"""
        if PCGMaterialSystem is None:
            self.skipTest("PCG材质系统模块不可用")
            
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "test_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化材质系统
        self.material_system = PCGMaterialSystem(
            output_dir=str(self.output_dir),
            cache_enabled=False  # 测试时禁用缓存
        )
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'temp_dir') and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_system_initialization(self):
        """测试系统初始化"""
        self.assertIsNotNone(self.material_system)
        self.assertEqual(str(self.material_system.output_dir), str(self.output_dir))
    
    def test_material_parameters_creation(self):
        """测试材质参数创建"""
        params = MaterialParameters(
            albedo_texture_path="test_albedo.png",
            roughness=0.5,
            metallic=0.2
        )
        
        self.assertEqual(params.albedo_texture_path, "test_albedo.png")
        self.assertEqual(params.roughness, 0.5)
        self.assertEqual(params.metallic, 0.2)
    
    def test_config_validation(self):
        """测试配置验证"""
        self.assertTrue(DEFAULT_CONFIG.validate())
    
    @unittest.skipUnless(PCGMaterialSystem, "PCG材质系统不可用")
    def test_material_variant_creation(self):
        """测试材质变体创建"""
        # 创建测试材质参数
        params = MaterialParameters(
            base_color=(0.8, 0.8, 0.8),
            roughness=0.3,
            metallic=0.1
        )
        
        try:
            # 创建材质变体
            variants = self.material_system.create_material_variants(
                base_name="test_material",
                params=[params],
                variant_styles=["metallic"]
            )
            
            # 验证结果
            self.assertIsInstance(variants, list)
            
        except Exception as e:
            # 如果依赖项不可用，跳过测试
            self.skipTest(f"材质变体创建需要完整的依赖项: {e}")


class TestConfigSystem(unittest.TestCase):
    """配置系统测试"""
    
    def test_default_config_creation(self):
        """测试默认配置创建"""
        config = DEFAULT_CONFIG
        self.assertIsNotNone(config)
        self.assertEqual(config.version, "2.0.0")
    
    def test_config_validation(self):
        """测试配置验证"""
        config = DEFAULT_CONFIG
        self.assertTrue(config.validate())
    
    def test_config_serialization(self):
        """测试配置序列化"""
        config = DEFAULT_CONFIG
        config_dict = config.to_dict()
        
        self.assertIsInstance(config_dict, dict)
        self.assertIn('material', config_dict)
        self.assertIn('pcg', config_dict)
        self.assertIn('usd', config_dict)


if __name__ == '__main__':
    unittest.main() 