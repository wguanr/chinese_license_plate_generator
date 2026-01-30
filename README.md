# Chinese License Plate Generator & Synthetic Data Toolkit

这是一个功能强大的程序化内容生成（PCG）系统，专门用于创建高度逼真的中国车牌3D资产和合成数据集。项目整合了从车牌生成、PBR 贴图、噪声叠加到多格式数据导出的完整工作流，并提供了一个直观的 Web 管理界面。

**访问地址**: [https://5000-idxnv37w3vo4e9t66kzji-fa184fd9.sg1.manus.computer/](https://5000-idxnv37w3vo4e9t66kzji-fa184fd9.sg1.manus.computer/)

## ✨ 核心功能

| 功能模块 | 特性 | 描述 |
|---|---|---|
| 🌐 **Web 管理界面** | 控制台、生成、资产管理、3D 查看、导出 | 一个完整的 Flask 前端，用于管理整个生成流程。|
| 🎨 **车牌生成** | 多类型、自定义、程序化 | 支持生成蓝色、绿色新能源、黄色、黑色等多种真实车牌。 |
| 💥 **PBR 噪声系统** | 贴图驱动、多层叠加、物理渲染 | 使用 500+ 真实噪声贴图，生成 BaseColor, Normal, Roughness 等 PBR 贴图。 |
| 📦 **数据集导出** | DINO, KITTI, USD, JSON | 一键导出适用于目标检测和 3D 仿真的多种主流数据集格式。 |
| 👓 **交互式 3D 查看器** | GLB 渲染、PBR 材质、环境光 | 在网页中实时渲染和查看生成的 3D 车牌模型，支持视角、光照切换。 |
| 🔌 **RESTful API** | 异步任务、状态查询、文件服务 | 提供一套完整的后端 API，用于程序化调用和系统集成。 |

## 🚀 快速开始

### 1. 安装依赖

系统依赖 Python 3 和一些第三方库。核心依赖包括 Pixar 的 USD 工具包。

```bash
sudo apt-get update
sudo apt-get install -y python3-pip git-lfs unrar
sudo pip3 install -r requirements.txt
```

### 2. 拉取 LFS 资源

项目使用 Git LFS 存储大型贴图资源。请确保已安装 `git-lfs` 并拉取资源。

```bash
git lfs install
git lfs pull
```

### 3. 启动管理系统

```bash
python3 visualization/run_server.py
```

服务启动后，即可通过浏览器访问 `http://localhost:5000`。

## 🏛️ 系统架构

系统采用高度模块化的设计，确保了功能的独立性和可扩展性。

```mermaid
graph TD
    subgraph A [用户界面]
        A1[Web UI (Flask)]
    end

    subgraph B [核心生成器]
        B1[车牌生成器]
        B2[PBR 噪声模块]
        B3[贴图管理器]
    end

    subgraph C [数据与导出]
        C1[数据集导出器]
        C2[USD/GLB 导出器]
        C3[JSON 元数据]
    end

    A1 --> B1
    A1 --> C1
    B1 --> B2
    B2 --> B3
    B1 --> C2
    C1 --> C2
    C1 --> C3
```

- **Web UI (Flask)**: 提供用户交互界面，调用后端 API 完成操作。
- **车牌生成器**: 负责根据用户配置生成基础车牌图像。
- **PBR 噪声模块**: 核心的物理渲染模块，使用真实贴图生成 PBR 材质。
- **数据集导出器**: 将生成的资产打包成 DINO, KITTI 等标准格式。
- **USD/GLB 导出器**: 负责将 3D 模型和材质导出为 `.usda` 和 `.glb` 文件。

## 🔧 API 文档

系统提供了一套完整的 RESTful API，用于程序化访问。详细的接口说明、参数和示例请查阅 `api_documentation.md` 文件。

## 💡 核心概念

### PBR 贴图工作流

系统采用标准的 PBR (Physically Based Rendering) 金属/粗糙度工作流。

- **BaseColor**: 污渍、灰尘、飞溅等贴图通过多层叠加混合，影响基础颜色。
- **Normal**: 裂纹、划痕等高度信息被转换为法线贴图，用于表现表面凹凸细节。
- **Roughness**: 根据噪声的分布和强度自动生成，控制表面粗糙度。
- **Metallic**: 车牌为非金属材质，基础值为 0。

### 噪声贴图

噪声系统使用了一个包含 500+ 高分辨率（2048x2048）真实照片贴图的资源包，涵盖了裂纹、污渍、灰尘、划痕等多种类型。通过随机采样、UV 缩放和多层混合，可以创造出无限的噪声组合。

## 🤝 贡献

欢迎通过提交 Issue 和 Pull Request 来改进这个系统。

## 📄 许可证

本项目遵循 MIT 许可证。
