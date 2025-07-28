from pathlib import Path
import bpy
import bmesh
import os
from mathutils import Vector
import math

# 尝试导入USD库
try:
    from pxr import Usd, UsdGeom, Sdf, UsdShade, Gf
    USD_AVAILABLE = True
    print("USD库导入成功")
except ImportError:
    USD_AVAILABLE = False
    print("警告：USD库未安装，USD导出功能将不可用")

def show_message(message, title="信息", icon='INFO'):
    """在Blender中显示消息"""
    def draw(self, context):
        self.layout.label(text=message)
    
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

class LicensePlateGenerator:
    def __init__(self):
        self.clear_scene()
        # 创建或获取collection
        if "LicensePlates" not in bpy.data.collections:
            self.collection = bpy.data.collections.new("LicensePlates")
            bpy.context.scene.collection.children.link(self.collection)
        else:
            self.collection = bpy.data.collections["LicensePlates"]
        
        # 存储生成的车牌信息，用于USD导出
        self.license_plates = []
        
    def clear_scene(self):
        """清除场景中的所有对象"""
        # 确保在对象模式下
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
            
        # 取消选择所有对象
        bpy.ops.object.select_all(action='DESELECT')
        
        # 选择所有对象
        for obj in bpy.data.objects:
            obj.select_set(True)
        
        # 删除选中的对象
        bpy.ops.object.delete()
        
        # 删除所有collection
        for collection in bpy.data.collections:
            bpy.data.collections.remove(collection)
        
        # 清除所有材质
        for material in bpy.data.materials:
            bpy.data.materials.remove(material, do_unlink=True)
            
        # 清除所有纹理
        for texture in bpy.data.textures:
            bpy.data.textures.remove(texture, do_unlink=True)
            
        # 清除所有图片
        for image in bpy.data.images:
            bpy.data.images.remove(image, do_unlink=True)
            
        # 清除所有网格数据
        for mesh in bpy.data.meshes:
            bpy.data.meshes.remove(mesh, do_unlink=True)
            
        # 清除所有灯光
        for light in bpy.data.lights:
            bpy.data.lights.remove(light, do_unlink=True)
            
        # 清除所有相机
        for camera in bpy.data.cameras:
            bpy.data.cameras.remove(camera, do_unlink=True)
    
    def create_material(self, image_path):
        """为每个车牌创建独立的材质"""
        # 从图片路径获取文件名作为材质名
        material_name = f"LicensePlateMaterial_{Path(image_path).stem}"
        material = bpy.data.materials.new(name=material_name)
        material.use_nodes = True
        
        # 清除默认节点
        material.node_tree.nodes.clear()
        
        # 创建节点
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        
        # 材质输出节点
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        output_node.location = (600, 0)
        
        # 主着色器节点
        principled_node = nodes.new(type='ShaderNodeBsdfPrincipled')
        principled_node.location = (400, 0)
        
        # 图像纹理节点
        texture_node = nodes.new(type='ShaderNodeTexImage')
        texture_node.location = (0, 0)
        
        # 添加纹理坐标节点
        texcoord_node = nodes.new(type='ShaderNodeTexCoord')
        texcoord_node.location = (-200, 0)
        
        # 添加映射节点
        mapping_node = nodes.new(type='ShaderNodeMapping')
        mapping_node.location = (-100, 0)
        
        # 连接节点
        links.new(texcoord_node.outputs['UV'], mapping_node.inputs['Vector'])
        links.new(mapping_node.outputs['Vector'], texture_node.inputs['Vector'])
        links.new(texture_node.outputs['Color'], principled_node.inputs['Base Color'])
        links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])
        
        # 设置材质属性
        principled_node.inputs['Metallic'].default_value = 0.0
        principled_node.inputs['Roughness'].default_value = 0.2
        if 'Specular IOR Level' in principled_node.inputs:
            principled_node.inputs['Specular IOR Level'].default_value = 0.5
        elif 'Specular' in principled_node.inputs:
            principled_node.inputs['Specular'].default_value = 0.5
        
        # 设置映射节点属性
        mapping_node.inputs['Scale'].default_value = (1, 1, 1)
        mapping_node.inputs['Rotation'].default_value = (0, 0, 0)
        
        # 加载图片
        image = bpy.data.images.load(image_path)
        texture_node.image = image
        
        # 设置纹理节点参数
        texture_node.extension = 'CLIP'
        texture_node.interpolation = 'Linear'
        texture_node.projection = 'FLAT'
        texture_node.projection_blend = 0.0
        
        return material
    
    def create_license_plate_geometry(self, width=0.52, height=0.11, thickness=0.002):
        """创建车牌几何体"""
        # 创建立方体网格
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
        plate = bpy.context.active_object
        plate.name = "LicensePlate"
        
        # 将对象添加到collection
        bpy.context.scene.collection.objects.unlink(plate)
        self.collection.objects.link(plate)
        
        # 旋转车牌，使其垂直放置（绕X轴旋转90度）
        plate.rotation_euler = (math.radians(90), 0, 0) 
        
        # 缩放到车牌尺寸
        plate.scale = (width, height, thickness)
        
        # 应用变换
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        
        # 进入编辑模式添加倒角
        bpy.context.view_layer.objects.active = plate
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 选择所有边
        bpy.ops.mesh.select_all(action='SELECT')
        
        # 添加倒角修改器
        bpy.ops.object.mode_set(mode='OBJECT')
        bevel_modifier = plate.modifiers.new(name="Bevel", type='BEVEL')
        bevel_modifier.width = 0.002
        bevel_modifier.segments = 3
        
        return plate
    
    def apply_material_to_object(self, obj, material):
        """将材质应用到对象"""
        # 清除现有材质
        obj.data.materials.clear()
        
        # 添加新材质
        obj.data.materials.append(material)
        
        # 设置纹理坐标
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 选择所有面
        bpy.ops.mesh.select_all(action='SELECT')
        
        # 删除所有现有的UV层
        while obj.data.uv_layers:
            obj.data.uv_layers.remove(obj.data.uv_layers[0])
        
        # 创建新的UV层
        uv_layer = obj.data.uv_layers.new(name="UVMap")
        
        # 取消选择所有面
        bpy.ops.mesh.select_all(action='DESELECT')
        
        # 切换到面选择模式
        bpy.ops.mesh.select_mode(type='FACE')
        
        # 选择上表面（Z轴正方向的面）
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # 选择Z轴正方向的面（车牌正面）
        for face in obj.data.polygons:
            if face.normal.z > 0.9:  # 选择法线朝Z轴正方向的面
                face.select = True
        
        # 回到编辑模式
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 设置活动UV层为新创建的UV层
        bpy.context.active_object.data.uv_layers.active = uv_layer
        
        # 只对选中的面进行UV映射
        bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
        
        # 返回对象模式
        bpy.ops.object.mode_set(mode='OBJECT')
    
    def add_lighting(self):
        """添加照明设置"""
        # 添加太阳光，调整位置以更好地照亮垂直放置的车牌
        bpy.ops.object.light_add(type='SUN', location=(5, -10, 5))
        sun = bpy.context.active_object
        sun.name = "Sun_Light"
        sun.data.energy = 5
        
        # 添加环境光，提供均匀照明
        bpy.ops.object.light_add(type='AREA', location=(0, -5, 0))
        area_light = bpy.context.active_object
        area_light.name = "Area_Light"
        area_light.data.energy = 8
        area_light.data.size = 20
        

    def setup_camera(self):
        """设置摄像机"""
        # 添加摄像机，调整位置以更好地查看垂直放置的车牌
        bpy.ops.object.camera_add(location=(0, -5, 0))
        camera = bpy.context.active_object
        camera.name = "Camera"
        
        # 设置摄像机视角，直接面向垂直车牌
        camera.rotation_euler = (math.radians(90), 0, 0)
        
        # 设置为活动摄像机
        bpy.context.scene.camera = camera
    
    def arrange_plates_in_grid(self, plates, spacing=1.0):
        """将车牌排列成网格，确保有足够间距"""
        grid_size = math.ceil(math.sqrt(len(plates)))
        for i, plate in enumerate(plates):
            row = i // grid_size
            col = i % grid_size
            # 增加间距，确保车牌不会重叠
            plate.location = (col * spacing, -row * spacing, 0)
    
    def get_image_dimensions(self, image_path):
        """使用Blender的API获取图片尺寸"""
        try:
            # 加载图片
            image = bpy.data.images.load(image_path)
            # 获取尺寸（像素）
            width = image.size[0]
            height = image.size[1]
            # 转换为米（假设图片是1000像素/米）
            width_m = width / 1000
            height_m = height / 1000
            return width_m, height_m
        except Exception as e:
            print(f"Error loading image {image_path}: {str(e)}")
            # 返回默认尺寸
            return 0.52, 0.11

    def export_to_usd_with_variants(self, output_path):
        """导出车牌到USD文件，每个车牌作为一个变体"""
        if not USD_AVAILABLE:
            show_message("USD库未安装，无法导出USD文件", title="错误", icon='ERROR')
            return False
            
        if not self.license_plates:
            show_message("没有生成车牌数据", title="错误", icon='ERROR')
            return False
        
        try:
            # 创建USD Stage
            stage = Usd.Stage.CreateNew(output_path)
            
            # 设置根层的元数据
            stage.SetDefaultPrim(stage.DefinePrim("/LicensePlateVariants"))
            
            # 创建根节点
            root_prim = stage.DefinePrim("/LicensePlateVariants", "Xform")
            root_prim.SetDocumentation("包含100个车牌变体的USD文件")
            
            # 创建变体集
            variant_set = root_prim.GetVariantSets().AddVariantSet("plateVariant")
            
            # 为每个车牌创建变体
            for i, plate_info in enumerate(self.license_plates):
                variant_name = f"plate_{i+1:03d}"
                
                # 添加变体
                variant_set.AddVariant(variant_name)
                variant_set.SetVariantSelection(variant_name)
                
                # 在变体编辑上下文中创建几何体
                with variant_set.GetVariantEditContext():
                    # 创建车牌几何体
                    plate_prim = stage.DefinePrim(f"/LicensePlateVariants/LicensePlate", "Mesh")
                    
                    # 设置网格数据
                    mesh = UsdGeom.Mesh(plate_prim)
                    
                    # 创建立方体顶点 (垂直放置的车牌)
                    width = plate_info['width']
                    height = plate_info['height'] 
                    thickness = plate_info['thickness']
                    
                    # 定义立方体的8个顶点 (垂直放置)
                    points = [
                        (-width/2, -thickness/2, -height/2),  # 左下后
                        ( width/2, -thickness/2, -height/2),  # 右下后
                        ( width/2,  thickness/2, -height/2),  # 右下前
                        (-width/2,  thickness/2, -height/2),  # 左下前
                        (-width/2, -thickness/2,  height/2),  # 左上后
                        ( width/2, -thickness/2,  height/2),  # 右上后
                        ( width/2,  thickness/2,  height/2),  # 右上前
                        (-width/2,  thickness/2,  height/2),  # 左上前
                    ]
                    
                    # 定义面 (每个面由4个顶点组成)
                    face_vertex_indices = [
                        # 前面 (Z正方向)
                        3, 2, 6, 7,
                        # 后面 (Z负方向)  
                        0, 4, 5, 1,
                        # 右面 (X正方向)
                        1, 5, 6, 2,
                        # 左面 (X负方向)
                        4, 0, 3, 7,
                        # 上面 (Y正方向)
                        4, 7, 6, 5,
                        # 下面 (Y负方向)
                        0, 1, 2, 3,
                    ]
                    
                    face_vertex_counts = [4] * 6  # 6个面，每个面4个顶点
                    
                    # 设置网格属性
                    mesh.CreatePointsAttr().Set(points)
                    mesh.CreateFaceVertexIndicesAttr().Set(face_vertex_indices)
                    mesh.CreateFaceVertexCountsAttr().Set(face_vertex_counts)
                    
                    # 创建UV坐标 (只为前面创建UV)
                    # 前面的UV坐标
                    uvs = []
                    for face_idx in range(6):
                        if face_idx == 0:  # 前面
                            uvs.extend([(0, 0), (1, 0), (1, 1), (0, 1)])
                        else:  # 其他面使用默认UV
                            uvs.extend([(0, 0), (1, 0), (1, 1), (0, 1)])
                    
                    # 创建UV属性
                    uv_attr = mesh.CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
                    uv_attr.Set(uvs)
                    
                    # 创建材质
                    material_path = f"/LicensePlateVariants/Materials/Material_{i+1:03d}"
                    material_prim = stage.DefinePrim(material_path, "Material")
                    material = UsdShade.Material(material_prim)
                    
                    # 创建着色器
                    shader_path = f"{material_path}/PbrShader"
                    shader_prim = stage.DefinePrim(shader_path, "Shader")
                    shader = UsdShade.Shader(shader_prim)
                    shader.CreateIdAttr("UsdPreviewSurface")
                    
                    # 创建纹理
                    texture_path = f"{material_path}/DiffuseTexture"
                    texture_prim = stage.DefinePrim(texture_path, "Shader")
                    texture = UsdShade.Shader(texture_prim)
                    texture.CreateIdAttr("UsdUVTexture")
                    
                    # 设置纹理文件路径（相对路径）
                    image_name = Path(plate_info['image_path']).name
                    texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(f"./textures/{image_name}")
                    
                    # 连接着色网络
                    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
                    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
                        texture.ConnectableAPI(), "rgb")
                    
                    # 绑定材质到几何体
                    UsdShade.MaterialBindingAPI(plate_prim).Bind(material)
                    
                    # 添加自定义属性记录图片信息
                    plate_prim.CreateAttribute("custom:imagePath", Sdf.ValueTypeNames.String).Set(plate_info['image_path'])
                    plate_prim.CreateAttribute("custom:plateIndex", Sdf.ValueTypeNames.Int).Set(i + 1)
            
            # 设置默认变体选择为第一个车牌
            if self.license_plates:
                variant_set.SetVariantSelection("plate_001")
            
            # 保存USD文件
            stage.GetRootLayer().Save()
            
            show_message(f"成功导出USD文件：{output_path}\n包含{len(self.license_plates)}个车牌变体", title="导出成功", icon='INFO')
            return True
            
        except Exception as e:
            show_message(f"USD导出失败：{str(e)}", title="错误", icon='ERROR')
            print(f"USD导出错误详情：{str(e)}")
            return False

    def generate_license_plates(self, image_paths):
        """批量生成车牌3D模型"""
        try:
            # 创建所有车牌
            plates = []
            for i, image_path in enumerate(image_paths):
                # 读取图片尺寸
                img_width, img_height = self.get_image_dimensions(image_path)
                
                # 创建几何体
                plate = self.create_license_plate_geometry(img_width, img_height)
                
                # 为每个车牌创建独立的材质
                material = self.create_material(image_path)
                
                # 应用材质
                self.apply_material_to_object(plate, material)
                
                # 存储车牌信息用于USD导出
                plate_info = {
                    'index': i + 1,
                    'image_path': image_path,
                    'width': img_width,
                    'height': img_height,
                    'thickness': 0.002,
                    'object': plate,
                    'material': material
                }
                self.license_plates.append(plate_info)
                
                plates.append(plate)
        
            # 不使用网格排列，所有车牌都保持在原点位置垂直放置
            # self.arrange_plates_in_grid(plates)
            
            # 添加照明
            self.add_lighting()
            
            # 设置摄像机
            self.setup_camera()
            
            # 切换到材质预览模式
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.shading.type = 'MATERIAL'
            
        except Exception as e:
            raise

def main():
    # 创建生成器实例
    generator = LicensePlateGenerator()
    
    # 设置图片路径
    img_dir = r'D:\simulation\AirSim\Unreal\Environments\Blocks\Plugins\AutelAI\External\Python\chinese_license_plate_generator\100_carplates_multiple'
    img_dir = img_dir + r'\img'
    show_message(img_dir, title="图片路径", icon='INFO')
    target_cp = 100
    
    # 获取所有JPG文件
    image_paths = [str(p) for p in Path(img_dir).glob('*.jpg')]
    
    if len(image_paths) == 0:
        show_message("没有找到图片文件", title="错误", icon='ERROR')
        return
    
    # 随机采样指定数量的图片
    if len(image_paths) > target_cp:
        import random
        image_paths = random.sample(image_paths, target_cp)

    # 生成车牌模型
    generator.generate_license_plates(image_paths)
    
    # 导出到USD文件（如果USD库可用）
    if USD_AVAILABLE:
        # 设置USD输出路径
        usd_output_path = os.path.join(Path(img_dir).parent, "license_plates_variants.usd")
        
        # 创建textures目录
        textures_dir = os.path.join(Path(img_dir).parent, "textures")
        os.makedirs(textures_dir, exist_ok=True)
        
        # 复制纹理文件到textures目录
        for image_path in image_paths:
            import shutil
            src_path = image_path
            dst_path = os.path.join(textures_dir, Path(image_path).name)
            try:
                shutil.copy2(src_path, dst_path)
            except Exception as e:
                print(f"复制纹理文件失败：{src_path} -> {dst_path}, 错误：{str(e)}")
        
        # 导出USD文件
        success = generator.export_to_usd_with_variants(usd_output_path)
        
        if success:
            show_message(f"USD文件已导出：{usd_output_path}\n您可以使用usdview查看并切换车牌变体", title="导出完成", icon='INFO')
        else:
            show_message("USD导出失败，请检查控制台输出", title="导出失败", icon='ERROR')
    else:
        show_message("USD库未安装，仅生成了Blender模型", title="提示", icon='INFO')

# 在Blender中运行时取消注释下面这行
main()