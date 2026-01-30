# FastNoiseLite集成使用指南

**快速参考**: 如何在车牌生成器中使用FastNoiseLite噪声系统

---

## 🚀 快速开始

### 1. 启动Go服务

```bash
cd /home/ubuntu/chinese_license_plate_generator/go_noise_service
./noise-service &
```

服务将在后台运行，监听 `http://localhost:8080`

### 2. 在Python中使用

#### 方式一：使用集成噪声系统（推荐）

```python
from core.integrated_noise_system import create_integrated_generator, NoiseSourcePriority

# 创建生成器
generator = create_integrated_generator(NoiseSourcePriority.BALANCED)

# 生成噪声
noise = generator.generate(
    width=512,
    height=512,
    noise_type="dirt",  # 可选: "dirt", "crack", "scratch", "dust", "splat"
    seed=42
)

# noise 是 numpy.ndarray，形状 (height, width)，类型 uint8，值范围 [0, 255]
```

#### 方式二：直接使用FastNoiseLite客户端

```python
from core.fastnoise_client import FastNoiseClient, FastNoisePresets

# 创建客户端
client = FastNoiseClient("http://localhost:8080")

# 使用预设
config = FastNoisePresets.perlin_fbm(width=512, height=512, seed=42)
noise = client.generate(config)
```

---

## 📖 常用场景

### 场景1：为车牌添加污垢效果

```python
from core.integrated_noise_system import create_integrated_generator, NoiseSourcePriority
from PIL import Image
import numpy as np

# 加载车牌图像
plate_img = Image.open("plate.png").convert("RGB")
width, height = plate_img.size

# 生成污垢噪声
generator = create_integrated_generator(NoiseSourcePriority.FASTNOISE_FIRST)
dirt_noise = generator.generate(width, height, "dirt", seed=42)

# 转换为PIL图像
dirt_img = Image.fromarray(dirt_noise, mode='L')

# 混合到车牌（multiply模式）
plate_array = np.array(plate_img).astype(np.float32) / 255.0
dirt_array = np.array(dirt_img).astype(np.float32) / 255.0

# 应用噪声（降低强度）
dirt_array = 0.7 + dirt_array * 0.3  # 将噪声映射到 [0.7, 1.0]

result = plate_array * dirt_array[:, :, np.newaxis]
result = (result * 255).astype(np.uint8)

result_img = Image.fromarray(result)
result_img.save("plate_with_dirt.png")
```

### 场景2：生成多层复合噪声

```python
from core.integrated_noise_system import create_integrated_generator, NoiseSourcePriority

generator = create_integrated_generator(NoiseSourcePriority.BALANCED)

# 生成多层噪声并混合
multi_layer_noise = generator.generate_multi_layer(
    width=512,
    height=512,
    noise_types=["dirt", "scratch", "dust"],
    blend_mode="multiply"  # 可选: "multiply", "add", "overlay", "screen"
)

# 保存结果
from PIL import Image
Image.fromarray(multi_layer_noise).save("multi_layer_noise.png")
```

### 场景3：批量生成不同种子的噪声

```python
from core.integrated_noise_system import create_integrated_generator, NoiseSourcePriority
from PIL import Image

generator = create_integrated_generator(NoiseSourcePriority.FASTNOISE_FIRST)

# 生成100张不同的污垢纹理
for i in range(100):
    noise = generator.generate(512, 512, "dirt", seed=i)
    Image.fromarray(noise).save(f"dirt_noise_{i:03d}.png")
```

### 场景4：自定义FastNoiseLite参数

```python
from core.fastnoise_client import FastNoiseClient, FastNoiseConfig

client = FastNoiseClient()

# 自定义配置
config = FastNoiseConfig(
    width=1024,
    height=1024,
    noise_type="cellular",
    seed=12345,
    frequency=0.03,
    fractal_type="none",
    cellular_distance_func="manhattan",
    cellular_return_type="distance2sub"
)

noise = client.generate(config)
```

---

## 🎨 噪声类型选择指南

| 噪声类型 | 推荐用途 | 特点 |
|---------|---------|------|
| **dirt** | 污垢、泥土 | 平滑自然，大块分布 |
| **crack** | 裂纹、破损 | 细线状，不规则 |
| **scratch** | 划痕、磨损 | 线条状，方向性强 |
| **dust** | 灰尘、细微颗粒 | 细腻，高频细节 |
| **splat** | 飞溅、水渍 | 斑点状，边缘清晰 |

---

## ⚙️ 优先级模式选择

| 模式 | 使用场景 | 特点 |
|------|---------|------|
| `ASSET_FIRST` | 需要高质量纹理 | 80%使用预制资源，20%程序化 |
| `FASTNOISE_FIRST` | 需要无限变化 | 80%程序化，20%预制资源 |
| `BALANCED` | 通用场景 | 50/50平衡 |
| `FASTNOISE_ONLY` | 测试/开发 | 100%程序化，无预制资源 |
| `ASSET_ONLY` | 离线渲染 | 100%预制资源，无程序化 |

**推荐**:
- 实时预览/交互式应用: `FASTNOISE_FIRST`
- 批量生成/数据集制作: `BALANCED`
- 高质量渲染: `ASSET_FIRST`

---

## 🔧 高级配置

### 混合模式说明

| 混合模式 | 效果 | 适用场景 |
|---------|------|---------|
| `multiply` | 相乘（变暗） | 添加污垢、阴影 |
| `add` | 相加（变亮） | 添加高光、光晕 |
| `overlay` | 叠加 | 增强对比度 |
| `screen` | 滤色（变亮） | 柔和的增亮效果 |

### FastNoiseLite参数调优

#### 频率 (frequency)
- **低频 (0.001-0.01)**: 大块、平滑的图案
- **中频 (0.01-0.05)**: 适中的细节
- **高频 (0.05-0.1)**: 细密的纹理

#### 分形层数 (fractal_octaves)
- **少层 (1-3)**: 简单、平滑
- **中等 (4-6)**: 平衡的细节
- **多层 (7-10)**: 丰富的细节，但计算量大

#### 间隙度 (fractal_lacunarity)
- **低值 (1.5-2.0)**: 细节分布均匀
- **高值 (2.5-3.0)**: 细节层次分明

#### 增益 (fractal_gain)
- **低值 (0.3-0.5)**: 高层细节较弱
- **高值 (0.6-0.8)**: 高层细节较强

---

## 🐛 故障排除

### 问题1: 连接Go服务失败

**错误信息**: `ConnectionError: Cannot connect to FastNoiseLite service`

**解决方案**:
```bash
# 检查服务是否运行
curl http://localhost:8080/health

# 如果没有响应，启动服务
cd /home/ubuntu/chinese_license_plate_generator/go_noise_service
./noise-service &

# 查看日志
cat /tmp/noise-service.log
```

### 问题2: 生成的噪声全黑或全白

**可能原因**: 频率设置不当

**解决方案**:
```python
# 调整频率到合理范围
config.frequency = 0.01  # 推荐值: 0.005-0.05
```

### 问题3: 生成速度慢

**可能原因**: 
1. 尺寸过大（>1024）
2. 分形层数过多（>8）

**解决方案**:
```python
# 方案1: 使用预制资源
generator = create_integrated_generator(NoiseSourcePriority.ASSET_FIRST)

# 方案2: 减少分形层数
config.fractal_octaves = 4  # 从6减少到4

# 方案3: 先生成小尺寸，再放大
noise_small = generator.generate(256, 256, "dirt")
noise_large = Image.fromarray(noise_small).resize((1024, 1024), Image.LANCZOS)
```

---

## 📊 性能优化建议

### 1. 使用缓存

```python
# 集成噪声系统默认启用缓存
config = IntegratedNoiseConfig(cache_enabled=True)
generator = IntegratedNoiseGenerator(config)

# 相同参数的第二次调用会直接从缓存返回
noise1 = generator.generate(512, 512, "dirt", seed=42)
noise2 = generator.generate(512, 512, "dirt", seed=42)  # 从缓存读取
```

### 2. 批量生成

```python
# 不推荐：逐个生成
for i in range(100):
    noise = generator.generate(512, 512, "dirt", seed=i)
    process(noise)

# 推荐：预生成后批量处理
noises = [generator.generate(512, 512, "dirt", seed=i) for i in range(100)]
for noise in noises:
    process(noise)
```

### 3. 选择合适的尺寸

| 用途 | 推荐尺寸 | 原因 |
|------|---------|------|
| 实时预览 | 256x256 | 速度快 |
| 常规使用 | 512x512 | 平衡 |
| 高质量渲染 | 1024x1024 | 细节丰富 |
| 超高清 | 2048x2048 | 使用预制资源 |

---

## 💡 最佳实践

### 1. 噪声强度控制

```python
# 生成噪声
noise = generator.generate(512, 512, "dirt")

# 控制强度（0.0 = 无效果，1.0 = 全强度）
strength = 0.3
noise_adjusted = (noise.astype(np.float32) / 255.0) * strength + (1 - strength)
noise_adjusted = (noise_adjusted * 255).astype(np.uint8)
```

### 2. 噪声区域限制

```python
# 只在特定区域应用噪声
mask = np.zeros((512, 512), dtype=np.uint8)
mask[100:400, 100:400] = 255  # 定义区域

noise = generator.generate(512, 512, "dirt")
noise_masked = (noise * (mask / 255.0)).astype(np.uint8)
```

### 3. 噪声动画

```python
# 通过改变种子生成动画序列
for frame in range(60):  # 60帧
    seed = int(1000 + frame * 10)  # 种子随时间变化
    noise = generator.generate(512, 512, "dirt", seed=seed)
    Image.fromarray(noise).save(f"frame_{frame:03d}.png")
```

---

## 📚 API参考

### IntegratedNoiseGenerator

```python
generator = create_integrated_generator(priority: NoiseSourcePriority)

# 生成单层噪声
noise = generator.generate(
    width: int,
    height: int,
    noise_type: str = "dirt",
    seed: Optional[int] = None
) -> np.ndarray

# 生成多层噪声
multi = generator.generate_multi_layer(
    width: int,
    height: int,
    noise_types: List[str],
    blend_mode: str = "multiply"
) -> np.ndarray
```

### FastNoiseClient

```python
client = FastNoiseClient(service_url: str = "http://localhost:8080")

# 生成噪声
noise = client.generate(config: FastNoiseConfig) -> np.ndarray

# 生成并保存
client.generate_to_file(config: FastNoiseConfig, output_path: str)
```

### FastNoiseConfig

```python
config = FastNoiseConfig(
    width: int = 512,
    height: int = 512,
    noise_type: str = "opensimplex2",
    seed: int = 1337,
    frequency: float = 0.01,
    fractal_type: str = "fbm",
    fractal_octaves: int = 6,
    fractal_lacunarity: float = 2.0,
    fractal_gain: float = 0.5,
    cellular_distance_func: str = "euclidean",
    cellular_return_type: str = "distance"
)
```

---

## 🔗 相关文档

- **集成报告**: `/home/ubuntu/fastnoise_integration_report.md`
- **FastNoiseLite官方文档**: https://github.com/Auburn/FastNoiseLite
- **车牌生成器项目**: `/home/ubuntu/chinese_license_plate_generator`

---

## 📝 示例代码库

完整示例代码位于:
- **客户端测试**: `core/fastnoise_client.py` (运行 `if __name__ == "__main__"` 部分)
- **集成系统测试**: `core/integrated_noise_system.py` (运行 `if __name__ == "__main__"` 部分)

---

**更新时间**: 2026年1月30日  
**版本**: v1.0.0
