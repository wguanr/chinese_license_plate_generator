# 车牌生成器管理系统 API 文档

**版本**: 2.0.0

本文档详细说明了车牌生成器管理系统的后端 API 接口，涵盖系统配置、车牌生成、资产管理和数据集导出等功能。所有接口均基于 RESTful 架构设计，使用 JSON 格式进行数据交换。

## 1. 基础信息

- **根URL**: `http://<your_server_address>:5000`
- **响应格式**: 所有 API 响应均为 JSON 格式。
- **认证**: 当前版本所有 API 均为开放接口，无需认证。

## 2. 系统与配置接口

### 2.1. 获取系统状态

获取服务器的运行状态和配置信息。

- **Endpoint**: `GET /api/system/status`
- **方法**: `GET`
- **成功响应 (200 OK)**:

```json
{
  "platform": "Linux",
  "python_version": "3.11.0rc1",
  "generator_available": true,
  "noise_generator_available": true,
  "output_dir": "/home/ubuntu/chinese_license_plate_generator/data/output",
  "export_dir": "/home/ubuntu/chinese_license_plate_generator/data/export"
}
```

### 2.2. 获取车牌类型

获取系统支持的所有车牌类型及其详细信息。

- **Endpoint**: `GET /api/config/plate_types`
- **方法**: `GET`
- **成功响应 (200 OK)**:

```json
{
  "types": [
    {"id": "blue", "name": "蓝色车牌", "description": "普通民用车牌", "color": "#1890ff"},
    {"id": "yellow", "name": "黄色车牌", "description": "大型车辆车牌", "color": "#faad14"},
    // ... 其他类型
  ]
}
```

### 2.3. 获取噪声预设

获取系统支持的噪声效果预设。

- **Endpoint**: `GET /api/config/noise_presets`
- **方法**: `GET`
- **成功响应 (200 OK)**:

```json
{
  "presets": [
    {"id": "clean", "name": "无噪声", "description": "干净的车牌图像"},
    {"id": "light", "name": "轻度噪声", "description": "少量污渍和轻微磨损"},
    // ... 其他预设
  ]
}
```

### 2.4. 获取省份列表

获取用于生成车牌的省份简称列表。

- **Endpoint**: `GET /api/config/provinces`
- **方法**: `GET`
- **成功响应 (200 OK)**:

```json
{
  "provinces": ["京", "津", "沪", "渝", ...]
}
```

## 3. 车牌生成接口

### 3.1. 生成单张预览

实时生成一张车牌图像用于预览，此接口为同步阻塞调用。

- **Endpoint**: `POST /api/generate/preview`
- **方法**: `POST`
- **请求体 (JSON)**:

```json
{
  "plate_type": "blue",
  "noise_preset": "light",
  "province": "京",
  "custom_number": "A88888"
}
```

| 参数 | 类型 | 必选 | 默认值 | 描述 |
|---|---|---|---|---|
| `plate_type` | string | 否 | `blue` | 车牌类型ID，参见 `GET /api/config/plate_types` |
| `noise_preset` | string | 否 | `clean` | 噪声预设ID，参见 `GET /api/config/noise_presets` |
| `province` | string | 否 | `""` | 省份简称，为空则随机 |
| `custom_number` | string | 否 | `""` | 自定义车牌号，为空则随机生成 |

- **成功响应 (200 OK)**:

```json
{
  "success": true,
  "image_url": "/output/generated/task_id/京A88888_blue_light.jpg",
  "filename": "京A88888_blue_light.jpg"
}
```

- **失败响应 (500 Internal Server Error)**:

```json
{
  "success": false,
  "error": "生成器未初始化"
}
```

### 3.2. 批量生成任务

创建一个异步的批量生成任务。

- **Endpoint**: `POST /api/generate/batch`
- **方法**: `POST`
- **请求体 (JSON)**:

```json
{
  "plate_type": "green_car",
  "count": 50,
  "noise_preset": "random",
  "province": "沪"
}
```

| 参数 | 类型 | 必选 | 默认值 | 描述 |
|---|---|---|---|---|
| `plate_type` | string | 否 | `blue` | 车牌类型ID |
| `count` | integer | 否 | `10` | 生成数量，最大为100 |
| `noise_preset` | string | 否 | `medium` | 噪声预设ID |
| `province` | string | 否 | `""` | 省份简称 |

- **成功响应 (200 OK)**:

```json
{
  "success": true,
  "task_id": "f8b1b2a2",
  "message": "已创建生成任务，共 50 张"
}
```

### 3.3. 获取任务状态

查询指定任务的当前状态和进度。

- **Endpoint**: `GET /api/generate/task/<task_id>`
- **方法**: `GET`
- **URL参数**:
  - `task_id` (string): 任务ID
- **成功响应 (200 OK)**:

```json
{
  "task_id": "f8b1b2a2",
  "status": "completed", // running, completed, failed
  "progress": 100,
  "total": 50,
  "created_at": "2026-01-30T05:00:00Z",
  "completed_at": "2026-01-30T05:01:00Z",
  "error": null,
  "results": [
    "/output/generated/f8b1b2a2/沪AD12345_green_car_random.jpg",
    // ...
  ]
}
```

### 3.4. 获取所有任务

获取所有已创建的任务列表。

- **Endpoint**: `GET /api/generate/tasks`
- **方法**: `GET`
- **成功响应 (200 OK)**:

```json
{
  "tasks": [
    {
      "task_id": "f8b1b2a2",
      "status": "completed",
      // ... 其他任务信息
    }
  ]
}
```

## 4. 资产管理接口

### 4.1. 获取资产列表

获取已生成的车牌资产列表，支持筛选和分页。

- **Endpoint**: `GET /api/assets`
- **方法**: `GET`
- **查询参数**:

| 参数 | 类型 | 默认值 | 描述 |
|---|---|---|---|
| `page` | integer | `1` | 页码 |
| `per_page` | integer | `20` | 每页数量 |
| `color` | string | `""` | 按颜色筛选 (blue, yellow, green, white, black) |
| `noise` | string | `""` | 按噪声等级筛选 (clean, light, medium, heavy, extreme, random) |
| `search` | string | `""` | 按车牌号或文件名搜索 |

- **成功响应 (200 OK)**:

```json
{
  "total": 60,
  "page": 1,
  "per_page": 20,
  "assets": [
    {
      "asset_id": "...",
      "plate_number": "粤AXBTB澳",
      "filename": "粤AXBTB澳_black_random_0000.jpg",
      // ... 其他资产信息
    }
  ]
}
```

### 4.2. 获取资产统计

获取资产的统计信息。

- **Endpoint**: `GET /api/assets/stats`
- **方法**: `GET`
- **成功响应 (200 OK)**:

```json
{
  "total": 60,
  "by_type": {"blue": 10, "green_car": 20, ...},
  "by_color": {"blue": 10, "green": 20, ...},
  "by_noise": {"random": 60},
  "total_size_mb": 0.77
}
```

### 4.3. 删除资产

批量删除一个或多个资产。

- **Endpoint**: `POST /api/assets/delete`
- **方法**: `POST`
- **请求体 (JSON)**:

```json
{
  "asset_ids": ["asset_id_1", "asset_id_2"]
}
```

- **成功响应 (200 OK)**:

```json
{
  "success": true,
  "deleted": 2
}
```

## 5. 数据集导出接口

### 5.1. 开始导出

触发一个数据集导出任务。

- **Endpoint**: `POST /api/export/start`
- **方法**: `POST`
- **请求体 (JSON)**:

```json
{
  "format": "dino",
  "name": "my_dino_dataset",
  "source": "all"
}
```

| 参数 | 类型 | 必选 | 默认值 | 描述 |
|---|---|---|---|---|
| `format` | string | 是 | - | 导出格式 (dino, kitti, usd, json, all) |
| `name` | string | 否 | `license_plates` | 数据集名称 |
| `source` | string | 否 | `all` | 数据源 (all, noisy, generated) |

- **成功响应 (200 OK)**:

```json
{
  "success": true,
  "message": "成功导出 60 张图像",
  "total_images": 60,
  "results": {
    "dino": "/home/ubuntu/chinese_license_plate_generator/data/export/my_dino_dataset"
  }
}
```

### 5.2. 获取导出状态

查询所有格式的数据集导出状态。

- **Endpoint**: `GET /api/export/status`
- **方法**: `GET`
- **成功响应 (200 OK)**:

```json
{
  "exports": [
    {
      "format": "dino",
      "exists": true,
      "size_mb": 0.48,
      "modified": "2026-01-30T05:00:00Z"
    },
    // ... 其他格式
  ]
}
```

### 5.3. 下载导出的数据集

下载指定格式的数据集压缩包。

- **Endpoint**: `GET /api/export/download/<format_type>`
- **方法**: `GET`
- **URL参数**:
  - `format_type` (string): 格式ID (dino, kitti, usd, json)
- **查询参数**:
  - `name` (string): 数据集名称，需与导出时一致。
- **成功响应 (200 OK)**:
  - 返回一个 `application/zip` 或 `application/json` 文件。

## 6. 文件服务

### 6.1. 访问输出文件

直接访问生成的图像文件。

- **Endpoint**: `GET /output/<path:filepath>`
- **方法**: `GET`
- **示例**: `GET /output/generated/task_id/plate.jpg`
