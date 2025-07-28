#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USD及贴图资源高级查看器生成脚本
"""

import os
import argparse
from pathlib import Path
import json
import re

def find_output_root(start_path: Path) -> Path:
    """向上查找项目根目录，然后定位data/output目录"""
    current = start_path.resolve()
    while not (current / '.git').exists() and current.parent != current:
        current = current.parent
    if not (current / '.git').exists():
        raise FileNotFoundError("无法找到项目根目录 (未找到.git目录)")
    return current / "data" / "output"

def get_viewer_html(plates_data_json: str, all_categories: list, all_colors: list) -> str:
    """生成最终的HTML文件内容"""

    # 将Python列表转为JavaScript数组字符串
    js_categories = json.dumps(["全部", *all_categories])
    js_colors = json.dumps(["全部", *all_colors])

    HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>USD 资源高级查看器</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; background-color: #f0f2f5; color: #333; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        header {{ background-color: #fff; padding: 20px 40px; text-align: center; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        header h1 {{ margin: 0; color: #1a1a1a; font-size: 2em; }}
        header p {{ margin: 5px 0 0; color: #888; }}
        .controls {{ background-color: #fff; padding: 20px; margin-bottom: 20px; border-radius: 8px; display: flex; flex-wrap: wrap; gap: 20px; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        .controls .control-group {{ display: flex; flex-direction: column; }}
        .controls label {{ font-size: 0.85em; color: #555; margin-bottom: 5px; }}
        .controls input, .controls select, .controls button {{ padding: 8px 12px; font-size: 1em; border-radius: 6px; border: 1px solid #d9d9d9; transition: all 0.2s; }}
        .controls input:focus, .controls select:focus {{ border-color: #40a9ff; box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2); outline: none; }}
        .controls input[type="search"] {{ min-width: 250px; }}
        .controls button {{ background-color: #1890ff; color: white; border-color: #1890ff; cursor: pointer; }}
        .controls button:hover {{ background-color: #40a9ff; }}
        .category {{ margin-bottom: 30px; }}
        .category-header {{ padding: 10px 0; border-bottom: 2px solid #e8e8e8; margin-bottom: 20px; display:flex; justify-content:space-between; align-items:center; }}
        .category-header h2 {{ margin: 0; font-size: 1.8em; color: #1a1a1a; }}
        .usd-link a {{ color: #1890ff; text-decoration: none; font-weight: bold; background-color: #e6f7ff; padding: 8px 12px; border-radius: 6px; border: 1px solid #91d5ff; }}
        .usd-link a:hover {{ background-color: #bae7ff; }}
        .gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }}
        .thumbnail {{ background-color: #fff; border: 1px solid #e8e8e8; border-radius: 8px; overflow: hidden; text-align: center; transition: all 0.2s; box-shadow: 0 1px 4px rgba(0,0,0,0.04); cursor: pointer; }}
        .thumbnail:hover {{ transform: translateY(-5px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        .thumbnail img {{ width: 100%; height: auto; display: block; }}
        .thumbnail-info {{ padding: 15px; font-size: 0.9em; }}
        .thumbnail-info .plate-number {{ font-weight: bold; font-size: 1.1em; color: #333; margin: 0 0 10px 0; }}
        .thumbnail-info .meta-tags {{ display: flex; flex-wrap: wrap; gap: 5px; justify-content: center; }}
        .thumbnail-info .tag {{ background-color: #f0f0f0; color: #555; padding: 3px 8px; border-radius: 4px; font-size: 0.8em; }}
        #no-results {{ text-align: center; padding: 50px; font-size: 1.2em; color: #888; }}
        .lightbox {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.8); display: none; justify-content: center; align-items: center; z-index: 1000; }}
        .lightbox.active {{ display: flex; }}
        .lightbox img {{ max-width: 90%; max-height: 90%; box-shadow: 0 0 25px rgba(0,0,0,0.5); border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>USD 资源查看器</h1>
            <p>一个用于浏览、筛选和搜索程序化生成的车牌资产的工具。</p>
        </header>

        <div class="controls">
            <div class="control-group">
                <label for="search-box">搜索车牌</label>
                <input type="search" id="search-box" placeholder="输入车牌号...">
            </div>
            <div class="control-group">
                <label for="filter-category">类型</label>
                <select id="filter-category"></select>
            </div>
            <div class="control-group">
                <label for="filter-color">颜色</label>
                <select id="filter-color"></select>
            </div>
            <div class="control-group">
                <label for="filter-layers">图层</label>
                <select id="filter-layers">
                    <option value="全部">全部</option>
                    <option value="单层">单层</option>
                    <option value="双层">双层</option>
                </select>
            </div>
            <div class="control-group">
                <label for="filter-dirt">污渍</label>
                <select id="filter-dirt">
                    <option value="全部">全部</option>
                    <option value="是">是</option>
                    <option value="否">否</option>
                </select>
            </div>
            <div class="control-group" style="justify-content: flex-end;">
                 <button id="reset-filters">重置筛选</button>
            </div>
        </div>

        <div id="gallery-container"></div>
        <div id="no-results" style="display: none;">未找到匹配的结果。</div>
    </div>
    
    <div class="lightbox" id="lightbox">
        <img src="" alt="放大的车牌图片">
    </div>

    <script>
        const platesData = {plates_data_json};
        const allCategories = {js_categories};
        const allColors = {js_colors};

        document.addEventListener('DOMContentLoaded', () => {{
            const searchBox = document.getElementById('search-box');
            const categoryFilter = document.getElementById('filter-category');
            const colorFilter = document.getElementById('filter-color');
            const layersFilter = document.getElementById('filter-layers');
            const dirtFilter = document.getElementById('filter-dirt');
            const resetButton = document.getElementById('reset-filters');
            const galleryContainer = document.getElementById('gallery-container');
            const noResults = document.getElementById('no-results');
            const lightbox = document.getElementById('lightbox');
            const lightboxImg = lightbox.querySelector('img');

            function populateFilters() {{
                allCategories.forEach(cat => {{
                    const option = new Option(cat, cat);
                    categoryFilter.add(option);
                }});
                allColors.forEach(col => {{
                    const option = new Option(col, col);
                    colorFilter.add(option);
                }});
            }}

            function createTag(text, color = '#f0f0f0') {{
                const tag = document.createElement('span');
                tag.className = 'tag';
                tag.textContent = text;
                tag.style.backgroundColor = color;
                if(color !== '#f0f0f0') tag.style.color = 'white';
                return tag;
            }}

            function renderGallery(data) {{
                galleryContainer.innerHTML = '';
                const groupedByCategory = data.reduce((acc, plate) => {{
                    acc[plate.category] = acc[plate.category] || [];
                    acc[plate.category].plates.push(plate);
                    acc[plate.category].usd_path = plate.usd_path;
                    return acc;
                }}, Object.fromEntries(allCategories.slice(1).map(c => [c, {{plates: [], usd_path: ''}}])));

                let foundItems = 0;
                for (const categoryName in groupedByCategory) {{
                    const group = groupedByCategory[categoryName];
                    if(group.plates.length === 0) continue;

                    const categorySection = document.createElement('section');
                    categorySection.className = 'category';

                    const header = document.createElement('div');
                    header.className = 'category-header';
                    header.innerHTML = `<h2>${{categoryName}}</h2>
                        <div class="usd-link">
                           <a href="${{group.usd_path}}" download>下载 ${{categoryName}} USD 文件</a>
                        </div>`;
                    
                    const gallery = document.createElement('div');
                    gallery.className = 'gallery';

                    group.plates.forEach(plate => {{
                        foundItems++;
                        const thumbnail = document.createElement('div');
                        thumbnail.className = 'thumbnail';
                        thumbnail.dataset.imagePath = plate.image_path;

                        const img = document.createElement('img');
                        img.src = plate.image_path;
                        img.alt = plate.plate_number;
                        img.loading = 'lazy';
                        thumbnail.appendChild(img);

                        const info = document.createElement('div');
                        info.className = 'thumbnail-info';
                        
                        const number = document.createElement('p');
                        number.className = 'plate-number';
                        number.textContent = plate.plate_number_display;
                        info.appendChild(number);

                        const tags = document.createElement('div');
                        tags.className = 'meta-tags';
                        tags.appendChild(createTag(plate.color, plate.color_hex));
                        tags.appendChild(createTag(plate.layers));
                        if(plate.dirt) tags.appendChild(createTag('有污渍'));
                        info.appendChild(tags);

                        thumbnail.appendChild(info);
                        gallery.appendChild(thumbnail);
                    }});
                    
                    categorySection.appendChild(header);
                    categorySection.appendChild(gallery);
                    galleryContainer.appendChild(categorySection);
                }}

                noResults.style.display = foundItems === 0 ? 'block' : 'none';
            }}

            function applyFilters() {{
                const searchTerm = searchBox.value.toUpperCase();
                const selectedCategory = categoryFilter.value;
                const selectedColor = colorFilter.value;
                const selectedLayers = layersFilter.value;
                const selectedDirt = dirtFilter.value;

                const filteredData = platesData.filter(plate => {{
                    const searchMatch = plate.plate_number.toUpperCase().includes(searchTerm);
                    const categoryMatch = selectedCategory === '全部' || plate.category === selectedCategory;
                    const colorMatch = selectedColor === '全部' || plate.color === selectedColor;
                    const layersMatch = selectedLayers === '全部' || plate.layers === selectedLayers;
                    const dirtMatch = selectedDirt === '全部' || (selectedDirt === '是' && plate.dirt) || (selectedDirt === '否' && !plate.dirt);
                    return searchMatch && categoryMatch && colorMatch && layersMatch && dirtMatch;
                }});

                renderGallery(filteredData);
            }}

            function resetAll() {{
                searchBox.value = '';
                categoryFilter.value = '全部';
                colorFilter.value = '全部';
                layersFilter.value = '全部';
                dirtFilter.value = '全部';
                applyFilters();
            }}

            populateFilters();
            renderGallery(platesData);

            [searchBox, categoryFilter, colorFilter, layersFilter, dirtFilter].forEach(el => {{
                el.addEventListener('input', applyFilters);
            }});
            resetButton.addEventListener('click', resetAll);
            
            galleryContainer.addEventListener('click', e => {{
                const thumbnail = e.target.closest('.thumbnail');
                if (thumbnail) {{
                    lightboxImg.src = thumbnail.dataset.imagePath;
                    lightbox.classList.add('active');
                }}
            }});
            
            lightbox.addEventListener('click', () => {{
                lightbox.classList.remove('active');
            }});
        }});
    </script>
</body>
</html>
    """
    return HTML_TEMPLATE

def generate_viewer(output_dir: str, viewer_path: str):
    """扫描output目录并生成HTML查看器。"""
    output_path = Path(output_dir)
    if not output_path.is_dir():
        print(f"❌ 错误: 输出目录 '{output_dir}' 不存在。请先生成资源。")
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ 已创建目录: {output_dir}")

    print(f"📂 正在扫描目录: {output_path}")

    all_items = []
    all_categories = set()
    all_colors = set()
    
    color_map = {
        "blue": "#1890ff",
        "yellow": "#fadb14",
        "green": "#52c41a",
        "white": "#d9d9d9",
        "black": "#262626",
    }

    viewer_file = Path(viewer_path)

    for category_dir in sorted(output_path.iterdir()):
        if not category_dir.is_dir():
            continue
            
        category_name = category_dir.name
        print(f"  - 发现分类: {category_name}")
        all_categories.add(category_name)

        usd_file = next(category_dir.glob("*.usda"), None)
        materials_dir = category_dir / "materials"

        if not usd_file or not materials_dir.is_dir():
            print(f"    ⚠️  跳过 '{category_name}': 缺少USD文件或materials目录。")
            continue

        usd_rel_path = os.path.relpath(usd_file, viewer_file.parent).replace('\\', '/')

        for image_file in sorted(materials_dir.iterdir()):
            if image_file.suffix.lower() not in ['.png', '.jpg', '.jpeg']:
                continue

            # --- 元数据解析 ---
            stem = image_file.stem
            parts = stem.split('_')
            
            plate_number_display = parts[0]
            plate_number_search = plate_number_display.replace('·', '')
            color = "unknown"
            dirt = False

            if len(parts) > 1:
                # 假设倒数第二个是颜色，最后一个是污渍状态
                color = parts[-2] if parts[-2] in color_map else "unknown"
                dirt_str = parts[-1]
                dirt = dirt_str.lower() == 'true' or dirt_str == '1'
                
                # 如果颜色解析不正确，调整车牌号
                if color == "unknown":
                    plate_number_display = stem
                    plate_number_search = stem
                else:
                    all_colors.add(color)
                    # 重新组合可能包含"_"的车牌号
                    plate_number_display = '_'.join(parts[:-2])

            layers = "双层" if '·' in plate_number_display else "单层"
            img_rel_path = os.path.relpath(image_file, viewer_file.parent).replace('\\', '/')

            all_items.append({
                "category": category_name,
                "plate_number": plate_number_search,
                "plate_number_display": plate_number_display,
                "image_path": img_rel_path,
                "usd_path": usd_rel_path,
                "color": color,
                "color_hex": next((c for name, c in color_map.items() if name in color), '#777'),
                "dirt": dirt,
                "layers": layers
            })
            
    if not all_items:
        print("🤷‍ 未找到任何有效的资源。将生成一个空的查看器。")
    
    final_html = get_viewer_html(
        json.dumps(all_items, ensure_ascii=False),
        sorted(list(all_categories)),
        sorted(list(all_colors))
    )

    with open(viewer_path, "w", encoding="utf-8") as f:
        f.write(final_html)
    
    print(f"\n✅ 高级查看器已成功生成: {viewer_path}")
    print("👉 请在浏览器中打开该文件查看结果。")

def main():
    parser = argparse.ArgumentParser(description="生成USD资源高级查看器")
    
    try:
        project_output_dir = find_output_root(Path.cwd())
        default_output = str(project_output_dir)
        default_viewer_path = str(project_output_dir / "viewer.html")
    except FileNotFoundError as e:
        print(f"⚠️  {e}")
        default_output = "data/output"
        default_viewer_path = "data/output/viewer.html"

    parser.add_argument(
        "--output_dir", type=str, default=default_output,
        help=f"包含分类子目录的output文件夹路径 (默认: {default_output})"
    )
    parser.add_argument(
        "--viewer_path", type=str, default=default_viewer_path,
        help=f"生成的viewer.html文件的保存路径 (默认: {default_viewer_path})"
    )
    args = parser.parse_args()
    generate_viewer(args.output_dir, args.viewer_path)

if __name__ == "__main__":
    main() 