# PCG-USD 车牌材质系统

一个基于程序化内容生成（PCG）的统一材质系统，专门用于生成符合OpenUSD规范的中国车牌材质。系统整合了材质参数管理、贴图自动分类、材质变体生成和USD导出功能，提供了简洁高效的材质管理解决方案。

## 核心特性

-   🎨 **自动贴图分类**: 根据文件名约定自动对车牌贴图进行分类。
-   🔧 **材质变体管理**: 支持在一个USD文件中生成和管理多种车牌类型的材质变体集。
-   📄 **USD 导出**: 生成符合OpenUSD规范的`.usda`材质库文件，方便在支持USD的各种软件（如Blender, Maya, Houdini, Unreal Engine）中使用。
-   ✨ **PBR材质**: 基于物理的渲染（PBR）标准，使用反照率、粗糙度和金属度参数。
-   ⚙️ **配置驱动**: 通过配置文件和参数类控制材质属性。
-   🐍 **Python原生**: 整个系统基于Python，并提供简单的API进行集成和扩展。

## 系统架构

系统采用模块化设计，核心组件包括：

-   `core/material_params.py`: 定义材质参数的数据类，支持参数验证和序列化。
-   `core/usd_material_system.py`: 统一的USD材质系统，整合所有功能。
-   `core/texture_classifier.py`: 根据命名规则对贴图文件进行分类。
-   `scripts/`: 包含用于执行主要生成流程的脚本。

```
PCG-USD材质系统
├── 贴图分类器 (TextureClassifier)
│   ├── 自动分类贴图
│   └── 变体组映射
├── 材质变体管理器 (MaterialVariantManager)
│   ├── 变体集创建
│   └── USD文件生成
├── USD材质系统 (USDMaterialSystem)
│   ├── 统一接口
│   └── 材质管理
└── 脚本/工具
    └── 生成脚本
```

## 安装依赖

为了使用本系统的全部功能，特别是USD导出功能，您需要安装Pixar的USD Python库。

### 推荐方法：使用pip安装

```bash
pip install usd-core
```

### 其他方法：使用conda安装

```bash
conda install -c conda-forge usd-core
```

### 在Blender等独立环境中使用

如果要在Blender等使用独立Python环境的软件中使用，需要将库安装到其对应的环境中。

1.  找到Blender的Python可执行文件路径。可以在Blender的Python控制台中运行以下命令查看：
    ```python
    import sys
    print(sys.executable)
    ```
2.  使用该路径下的pip进行安装。例如，在Windows上：
    ```bash
    "C:\Program Files\Blender Foundation\Blender 4.2\4.2\python\bin\python.exe" -m pip install usd-core
    ```

### 验证安装

运行以下Python代码来验证USD库是否安装成功：

```python
try:
    from pxr import Usd, UsdGeom, Sdf
    print("USD库安装成功！")
except ImportError as e:
    print(f"USD库安装失败: {e}")
```

## 快速开始

### 1. 使用脚本生成

通过运行项目提供的脚本，可以快速生成车牌材质和模型。

```bash
# 运行主生成脚本
python scripts/generate_license_plates.py --input assets/plates_base/img --output data/output
```

### 2. 作为库在代码中使用

您也可以将本系统作为库导入到您自己的Python项目中。

```python
from core.usd_material_system import create_usd_material_system

# 1. 创建材质系统
system = create_usd_material_system(
    assets_dir="assets",
    output_dir="output",
    usd_stage_path="output/stage.usda"
)

# 2. 创建一个材质实例
material = system.create_material_instance(
    instance_name="license_plate_001",
    albedo_texture_path="assets/textures/plate_blue_car_false.png",
    roughness=0.2,
    metallic=0.8
)

# 3. 基于基础材质生成变体
variants = system.generate_material_variants(
    base_material_name="license_plate_001",
    variant_count=5
)

# 4. 导出为USD材质库
system.export_materials(
    export_format="usd",
    export_path="output/exported_materials"
)
```

### 3. 查看和使用USD文件

您可以使用任何支持USD的软件来查看生成的文件（例如 `license_plate_materials.usda`）。

-   **`usdview`** (USD官方查看器):
    ```bash
    usdview output/license_plate_materials.usda
    ```
    在`usdview`中，您可以选择包含材质的Prim，并在右侧的“Meta Data”选项卡中找到变体集（如 `variantType`），然后通过下拉菜单切换不同的车牌变体。

-   **Blender, Maya, Houdini等**: 直接导入`.usda`文件。

##核心概念

### PBR 材质参数

本系统使用标准的PBR工作流，主要包含以下参数：

1.  **`albedo_texture`** (反照率贴图)
    -   作用：定义材质的基础颜色和纹理，如车牌的文字、背景和边框。
    -   类型：`texture_2d`

2.  **`roughness`** (粗糙度)
    -   作用：控制表面的微观粗糙程度。
    -   范围：`[0.0, 1.0]` (0.0 = 完全光滑, 1.0 = 完全粗糙/哑光)

3.  **`metallic`** (金属度)
    -   作用：控制材质的金属质感。
    -   范围：`[0.0, 1.0]` (0.0 = 非金属, 1.0 = 纯金属)


### 贴图命名约定

为了实现自动分类，贴图文件需要遵循特定的命名约定。

-   **3字段格式**: `name_color_is_double.png` (例如: `plate_blue_car_false.png`)
-   **4字段格式**: `name_color_special_use_is_double.png` (例如: `plate_black_shi_false.png`)

系统会根据文件名中的 **颜色** 关键字将贴图映射到不同的车牌类型。

### 支持的车牌类型与变体

系统预定义了多种车牌类型，每种类型都有默认的材质参数。这些类型会作为USD文件中的变体集存在。

| 变体组 (`variantType`) | 描述 | 粗糙度 (`roughness`) | 金属度 (`metallic`) | 对应颜色关键字 |
| :--- | :--- | :--- | :--- | :--- |
| `civilian` | 民用车辆车牌 | 0.2 | 0.1 | `blue` |
| `new_energy` | 新能源车辆车牌 | 0.15 | 0.8 | `green` |
| `commercial` | 商用车辆车牌 | 0.3 | 0.5 | `yellow` |
| `official` | 官方/警用车辆车牌 | 0.1 | 0.9 | `white` |
| `special` | 特殊车辆车牌 | 0.05 | 0.95 | `black`, `red` |

## 扩展与自定义

### 添加新的车牌类型

1.  **更新配置**: 在相关的配置文件或代码中（如 `core/config.py`），为 `material_templates` 添加一个新的条目。
    ```python
    'custom_type': {
        'roughness': 0.25,
        'metallic': 0.6,
        'description': '自定义的新类型车牌'
    }
    ```
2.  **更新命名规则**: 在 `naming_patterns` 中添加新的颜色或关键字映射，使其能正确分类新类型的贴图。
    ```python
    'new_color_keyword': ['new_color', 'custom_type']
    ```

### 自定义材质参数

您可以在创建材质实例时直接覆盖默认参数，或修改配置文件中的默认模板。

## 故障排除

-   **`ImportError: No module named 'pxr'`**: USD库未正确安装或未在当前Python环境中。请参照 **[安装依赖](#安装依赖)** 部分进行安装。
-   **贴图分类失败或不正确**:
    -   检查贴图文件名是否遵循 **[贴图命名约定](#贴图命名约定)**。
    -   检查贴图文件是否存在且路径可读。
-   **USD文件生成失败**:
    -   确认输出目录存在并且有写入权限。
    -   检查生成的变体集是否为空。
-   **材质在渲染器中显示异常**:
    -   检查 `roughness` 和 `metallic` 参数是否在 `[0.0, 1.0]` 的有效范围内。
    -   确认贴图文件路径在USD文件中是正确的相对路径或绝对路径。

## 贡献

欢迎通过提交Issue和Pull Request来改进这个系统。

## 许可证

本项目遵循MIT许可证。
