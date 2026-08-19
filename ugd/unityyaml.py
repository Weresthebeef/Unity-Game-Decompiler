"""
Unity YAML format writer for creating reconstructable Unity project files.
"""
import os
import struct
from typing import Dict, List, Any, Optional, TextIO
from datetime import datetime


# ============================================================
# YAML Writing Utilities
# ============================================================

def _write_yaml_line(f: TextIO, indent: int, key: str, value: Any, is_last: bool = False):
    """Write a single YAML line."""
    prefix = '  ' * indent
    if isinstance(value, dict):
        f.write(f"{prefix}{key}:\n")
        items = list(value.items())
        for i, (k, v) in enumerate(items):
            _write_yaml_line(f, indent + 1, k, v, i == len(items) - 1)
    elif isinstance(value, list):
        f.write(f"{prefix}{key}:\n")
        for i, item in enumerate(value):
            if isinstance(item, dict):
                _write_yaml_line(f, indent + 1, '', item, i == len(value) - 1)
            else:
                f.write(f"{prefix}  - {_format_yaml_value(item)}\n")
    else:
        comma = '' if is_last else ','
        f.write(f"{prefix}{key}: {_format_yaml_value(value)}{comma}\n")


def _format_yaml_value(value: Any) -> str:
    """Format a value for YAML output."""
    if value is None:
        return ''
    elif isinstance(value, bool):
        return 'true' if value else 'false'
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, float):
        # Format float with reasonable precision
        return f"{value:.6g}"
    elif isinstance(value, str):
        # Escape special characters and quote if needed
        if any(c in value for c in ':{}[]&*?|->\\"\'\n'):
            return f'"{value}"'
        return value
    elif isinstance(value, bytes):
        return value.hex()
    else:
        return str(value)


def _write_yaml_dict(f: TextIO, data: Dict[str, Any], indent: int = 0):
    """Write a dictionary as YAML."""
    items = list(data.items())
    for i, (key, value) in enumerate(items):
        is_last = (i == len(items) - 1)
        _write_yaml_line(f, indent, key, value, is_last)


# ============================================================
# Unity YAML File Format
# ============================================================

class UnityYAMLWriter:
    """Writer for Unity YAML format files."""
    
    @staticmethod
    def write_scene(scene_path: str, objects: List[Dict[str, Any]]) -> None:
        """
        Write a Unity scene file (.unity) in YAML format.
        
        Args:
            scene_path: Output path for the scene file
            objects: List of scene objects to write
        """
        with open(scene_path, 'w', encoding='utf-8') as f:
            f.write("%YAML 1.1\n")
            f.write("---\n")
            f.write("FileID: 11010000\n")
            f.write("Guid: 0000000000000000f000000000000000\n")
            f.write("Type: 3\n")
            f.write("PathID: 11010000\n")
            f.write("\n")
            
            # Write each object
            for obj in objects:
                UnityYAMLWriter._write_object(f, obj)
    
    @staticmethod
    def _write_object(f: TextIO, obj: Dict[str, Any]) -> None:
        """Write a single Unity object in YAML format."""
        # Determine component type
        class_id = obj.get('class_id', 0)
        class_name = obj.get('class_name', '')
        
        # Write header
        file_id = obj.get('file_id', 0)
        guid = obj.get('guid', '00000000000000000000000000000000')
        path_id = obj.get('path_id', 0)
        
        f.write(f"--- !u!{class_id} &{path_id}\n")
        f.write(f"GameObject:\n")
        f.write(f"  m_ObjectHideFlags: 0\n")
        f.write(f"  m_CorrespondingSourceObject: {{fileID: 0}}\n")
        f.write(f"  m_PrefabInstance: {{fileID: 0}}\n")
        f.write(f"  m_Name: {obj.get('name', '')}\n")
        f.write(f"  serializedVersion: 6\n")
        f.write(f"  m_Component:\n")
        f.write(f"  - component: {{fileID: {file_id}}}\n")
        f.write(f"  m_Layer: {obj.get('layer', 0)}\n")
        f.write(f"  m_TagString: {obj.get('tag', '')}\n")
        f.write(f"  m_Icon: {{fileID: 0}}\n")
        f.write(f"  m_NavMeshLayer: 0\n")
        f.write(f"  m_StaticEditorFlags: 0\n")
        f.write(f"  m_IsActive: {obj.get('is_active', True)}\n")
        
        # Write component-specific data
        if class_id == 4:  # Transform
            UnityYAMLWriter._write_transform(f, obj)
        elif class_id == 224:  # RectTransform
            UnityYAMLWriter._write_rect_transform(f, obj)
        elif class_id == 23:  # MeshRenderer
            UnityYAMLWriter._write_mesh_renderer(f, obj)
        elif class_id == 33:  # MeshFilter
            UnityYAMLWriter._write_mesh_filter(f, obj)
        elif class_id == 212:  # SpriteRenderer
            UnityYAMLWriter._write_sprite_renderer(f, obj)
        elif class_id == 20:  # Camera
            UnityYAMLWriter._write_camera(f, obj)
        elif class_id == 108:  # Light
            UnityYAMLWriter._write_light(f, obj)
        
        f.write("\n")
    
    @staticmethod
    def _write_transform(f: TextIO, obj: Dict[str, Any]) -> None:
        """Write Transform component data."""
        f.write("  m_Transform:\n")
        f.write("    serializedVersion: 2\n")
        f.write("    m_LocalRotation:\n")
        rot = obj.get('local_rotation', {})
        f.write(f"      m_X: {rot.get('x', 0.0)}\n")
        f.write(f"      m_Y: {rot.get('y', 0.0)}\n")
        f.write(f"      m_Z: {rot.get('z', 0.0)}\n")
        f.write(f"      m_W: {rot.get('w', 1.0)}\n")
        f.write("    m_LocalPosition:\n")
        pos = obj.get('local_position', {})
        f.write(f"      m_X: {pos.get('x', 0.0)}\n")
        f.write(f"      m_Y: {pos.get('y', 0.0)}\n")
        f.write(f"      m_Z: {pos.get('z', 0.0)}\n")
        f.write("    m_LocalScale:\n")
        scale = obj.get('local_scale', {})
        f.write(f"      m_X: {scale.get('x', 1.0)}\n")
        f.write(f"      m_Y: {scale.get('y', 1.0)}\n")
        f.write(f"      m_Z: {scale.get('z', 1.0)}\n")
        f.write("    m_ConstrainProportionsScale: 0\n")
        f.write("    m_Children: []\n")
        f.write("    m_Father: {fileID: 0}\n")
        f.write("    m_LocalEulerAnglesHint: {x: 0, y: 0, z: 0}\n")
    
    @staticmethod
    def _write_rect_transform(f: TextIO, obj: Dict[str, Any]) -> None:
        """Write RectTransform component data."""
        f.write("  m_Transform:\n")
        f.write("    serializedVersion: 2\n")
        f.write("    m_LocalRotation:\n")
        rot = obj.get('local_rotation', {})
        f.write(f"      m_X: {rot.get('x', 0.0)}\n")
        f.write(f"      m_Y: {rot.get('y', 0.0)}\n")
        f.write(f"      m_Z: {rot.get('z', 0.0)}\n")
        f.write(f"      m_W: {rot.get('w', 1.0)}\n")
        f.write("    m_LocalPosition:\n")
        pos = obj.get('local_position', {})
        f.write(f"      m_X: {pos.get('x', 0.0)}\n")
        f.write(f"      m_Y: {pos.get('y', 0.0)}\n")
        f.write(f"      m_Z: {pos.get('z', 0.0)}\n")
        f.write("    m_LocalScale:\n")
        scale = obj.get('local_scale', {})
        f.write(f"      m_X: {scale.get('x', 1.0)}\n")
        f.write(f"      m_Y: {scale.get('y', 1.0)}\n")
        f.write(f"      m_Z: {scale.get('z', 1.0)}\n")
        f.write("    m_ConstrainProportionsScale: 0\n")
        f.write("    m_Children: []\n")
        f.write("    m_Father: {fileID: 0}\n")
        f.write("    m_LocalEulerAnglesHint: {x: 0, y: 0, z: 0}\n")
        f.write("  m_AnchorMin: {x: 0, y: 0}\n")
        f.write("  m_AnchorMax: {x: 1, y: 1}\n")
        f.write("  m_AnchoredPosition: {x: 0, y: 0}\n")
        f.write("  m_SizeDelta: {x: 0, y: 0}\n")
        f.write("  m_Pivot: {x: 0.5, y: 0.5}\n")
    
    @staticmethod
    def _write_mesh_filter(f: TextIO, obj: Dict[str, Any]) -> None:
        """Write MeshFilter component data."""
        mesh = obj.get('mesh', {})
        mesh_path_id = mesh.get('path_id', 0) if isinstance(mesh, dict) else 0
        f.write(f"  m_Mesh: {{fileID: 10754, guid: 0000000000000000f000000000000000, type: 0, pathID: {mesh_path_id}}}\n")
    
    @staticmethod
    def _write_mesh_renderer(f: TextIO, obj: Dict[str, Any]) -> None:
        """Write MeshRenderer component data."""
        materials = obj.get('materials', [])
        f.write("  m_Enabled: 1\n")
        f.write("  m_CastShadows: 1\n")
        f.write("  m_ReceiveShadows: 1\n")
        f.write("  m_DynamicOccludee: 1\n")
        f.write("  m_StaticShadowCaster: 0\n")
        f.write("  m_MotionVectors: 1\n")
        f.write("  m_LightProbeUsage: 1\n")
        f.write("  m_ReflectionProbeUsage: 1\n")
        f.write("  m_RayTracingMode: 0\n")
        f.write("  m_RayTraceProcedural: 0\n")
        f.write("  m_Materials:\n")
        for mat in materials:
            mat_path_id = mat.get('path_id', 0) if isinstance(mat, dict) else 0
            f.write(f"  - {fileID: 10754, guid: 0000000000000000f000000000000000, type: 0, pathID: {mat_path_id}}\n")
        f.write("  m_StaticBatchInfo:\n")
        f.write("    firstSubMesh: 0\n")
        f.write("    subMeshCount: 0\n")
        f.write("  m_StaticBatchRoot: {fileID: 0}\n")
        f.write("  m_ProbeAnchor: {fileID: 0}\n")
        f.write("  m_LightmapParameters: {fileID: 0}\n")
        f.write("  m_SortingLayerID: 0\n")
        f.write("  m_SortingLayer: 0\n")
        f.write("  m_SortingOrder: 0\n")
    
    @staticmethod
    def _write_sprite_renderer(f: TextIO, obj: Dict[str, Any]) -> None:
        """Write SpriteRenderer component data."""
        sprite = obj.get('sprite', {})
        sprite_path_id = sprite.get('path_id', 0) if isinstance(sprite, dict) else 0
        color = obj.get('color', {})
        
        f.write("  m_Enabled: 1\n")
        f.write("  m_CastShadows: 0\n")
        f.write("  m_ReceiveShadows: 0\n")
        f.write("  m_DynamicOccludee: 1\n")
        f.write("  m_StaticShadowCaster: 0\n")
        f.write("  m_MotionVectors: 1\n")
        f.write("  m_LightProbeUsage: 1\n")
        f.write("  m_ReflectionProbeUsage: 1\n")
        f.write(f"  m_Sprite: {{fileID: 10754, guid: 0000000000000000f000000000000000, type: 0, pathID: {sprite_path_id}}}\n")
        f.write(f"  m_Color: {{r: {color.get('r', 1.0)}, g: {color.get('g', 1.0)}, b: {color.get('b', 1.0)}, a: {color.get('a', 1.0)}}}\n")
        f.write("  m_FlipX: 0\n")
        f.write("  m_FlipY: 0\n")
        f.write("  m_DrawMode: 0\n")
        f.write("  m_Size: {x: 1, y: 1}\n")
        f.write("  m_AdaptiveModeThreshold: 0.5\n")
        f.write("  m_SpriteSortPoint: 0\n")
    
    @staticmethod
    def _write_camera(f: TextIO, obj: Dict[str, Any]) -> None:
        """Write Camera component data."""
        f.write("  m_Enabled: 1\n")
        f.write("  serializedVersion: 2\n")
        f.write("  m_GameObject: {fileID: 0}\n")
        f.write("  m_ClearFlags: 1\n")
        f.write("  m_BackGroundColor: {r: 0.19215686, g: 0.19215686, b: 0.19215686, a: 1}\n")
        f.write("  m_CullingMask: -1\n")
        f.write("  m_TargetDisplay: 0\n")
        f.write("  m_TargetTexture: {fileID: 0}\n")
        f.write("  m_FieldOfView: 60\n")
        f.write("  m_NearClipPlane: 0.3\n")
        f.write("  m_FarClipPlane: 1000\n")
        f.write("  m_RenderingPath: -1\n")
        f.write("  m_CameraType: 2\n")
    
    @staticmethod
    def _write_light(f: TextIO, obj: Dict[str, Any]) -> None:
        """Write Light component data."""
        light_type = obj.get('type', 0)  # 0 = Spot, 1 = Directional, 2 = Point, 3 = Area
        color = obj.get('color', {})
        
        f.write("  m_Enabled: 1\n")
        f.write(f"  m_Type: {light_type}\n")
        f.write(f"  m_Color: {{r: {color.get('r', 1.0)}, g: {color.get('g', 1.0)}, b: {color.get('b', 1.0)}, a: 1}}\n")
        f.write(f"  m_Intensity: {obj.get('intensity', 1.0)}\n")
        f.write(f"  m_Range: {obj.get('range', 10.0)}\n")
        f.write(f"  m_SpotAngle: {obj.get('spot_angle', 30.0)}\n")


# ============================================================
# Unity Project Structure
# ============================================================

class UnityProjectBuilder:
    """Build a reconstructable Unity project structure."""
    
    def __init__(self, output_dir: str, game_name: str = "DecompiledGame"):
        self.output_dir = os.path.abspath(output_dir)
        self.game_name = game_name
        self.assets_dir = os.path.join(self.output_dir, "Assets")
        self.scenes = []
        self.prefabs = []
        self.textures = []
        self.materials = []
        self.meshes = []
        self.scripts = []
        self.audio_clips = []
        self.fonts = []
        self.shaders = []
        self.other_assets = []
    
    def create_structure(self) -> None:
        """Create the basic Unity project structure."""
        # Create directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.assets_dir, exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "Scenes"), exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "Prefabs"), exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "Textures"), exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "Materials"), exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "Models"), exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "Scripts"), exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "Audio"), exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "Fonts"), exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "Shaders"), exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "Resources"), exist_ok=True)
        
        # Create ProjectSettings
        self._create_project_settings()
        
        # Create Assembly-CSharp
        self._create_assembly_csharp()
        
        # Create Packages manifest
        self._create_packages_manifest()
    
    def _create_project_settings(self) -> None:
        """Create ProjectSettings/ProjectSettings.asset file."""
        settings_dir = os.path.join(self.output_dir, "ProjectSettings")
        os.makedirs(settings_dir, exist_ok=True)
        settings_path = os.path.join(settings_dir, "ProjectSettings.asset")
        with open(settings_path, 'w', encoding='utf-8') as f:
            f.write("%YAML 1.1\n")
            f.write("---\n")
            f.write("FileID: 0\n")
            f.write("Guid: 0000000000000000f000000000000000\n")
            f.write("Type: 0\n")
            f.write("PathID: 0\n")
            f.write("\n")
    
    def _create_assembly_csharp(self) -> None:
        """Create Assembly-CSharp.csproj for Mono scripts."""
        csproj_path = os.path.join(self.assets_dir, "Scripts", "Assembly-CSharp.csproj")
        with open(csproj_path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            f.write('<Project ToolsVersion="4.0" DefaultTargets="Build" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">\n')
            f.write('  <PropertyGroup>\n')
            f.write('    <Configuration Condition=" \'$(Configuration)\' == \'\' ">Debug</Configuration>\n')
            f.write('    <Platform Condition=" \'$(Platform)\' == \'\' ">AnyCPU</Platform>\n')
            f.write('    <ProductVersion>10.0.0</ProductVersion>\n')
            f.write('    <SchemaVersion>2.0</SchemaVersion>\n')
            f.write('    <ProjectGuid>{00000000-0000-0000-0000-000000000000}</ProjectGuid>\n')
            f.write('    <OutputType>Library</OutputType>\n')
            f.write('    <AppDesignerFolder>Properties</AppDesignerFolder>\n')
            f.write('    <RootNamespace>\n')
            f.write('    </RootNamespace>\n')
            f.write('    <AssemblyName>Assembly-CSharp</AssemblyName>\n')
            f.write('    <TargetFrameworkVersion>v4.7.1</TargetFrameworkVersion>\n')
            f.write('    <LangVersion>latest</LangVersion>\n')
            f.write('  </PropertyGroup>\n')
            f.write('  <PropertyGroup Condition=" \'$(Configuration)\' == \'Debug\' ">\n')
            f.write('    <DebugSymbols>true</DebugSymbols>\n')
            f.write('    <DebugType>portable</DebugType>\n')
            f.write('    <Optimize>false</Optimize>\n')
            f.write('    <OutputPath>Temp\\bin\\Debug\\</OutputPath>\n')
            f.write('    <DefineConstants>DEBUG;UNITY_2021_3_OR_NEWER</DefineConstants>\n')
            f.write('  </PropertyGroup>\n')
            f.write('  <PropertyGroup Condition=" \'$(Configuration)\' == \'Release\' ">\n')
            f.write('    <DebugType>pdbonly</DebugType>\n')
            f.write('    <Optimize>true</Optimize>\n')
            f.write('    <OutputPath>Temp\\bin\\Release\\</OutputPath>\n')
            f.write('  </PropertyGroup>\n')
            f.write('  <ItemGroup>\n')
            f.write('    <Reference Include="UnityEngine">\n')
            f.write('      <HintPath>$(UNITY_INSTALL_PATH)\\Editor\\Data\\Managed\\UnityEngine.dll</HintPath>\n')
            f.write('    </Reference>\n')
            f.write('  </ItemGroup>\n')
            f.write('  <Import Project="$(MSBuildExtensionsPath32)\\Microsoft\\VisualStudio\\v$(VisualStudioVersion)\\DotNet\\Microsoft.DotNet.targets" />\n')
            f.write('</Project>\n')
    
    def _create_packages_manifest(self) -> None:
        """Create Packages/manifest.json."""
        packages_dir = os.path.join(self.output_dir, "Packages")
        os.makedirs(packages_dir, exist_ok=True)
        
        manifest_path = os.path.join(packages_dir, "manifest.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write('{\n')
            f.write('  "name": "' + self.game_name + '",\n')
            f.write('  "version": "1.0.0",\n')
            f.write('  "unity": "2021.3",\n')
            f.write('  "dependencies": {\n')
            f.write('    "com.unity.2d.sprite": "1.0.0",\n')
            f.write('    "com.unity.2d.animation": "1.0.0",\n')
            f.write('    "com.unity.2d.common": "1.0.0",\n')
            f.write('    "com.unity.2d.psdimporter": "1.0.0",\n')
            f.write('    "com.unity.2d.sprite": "1.0.0",\n')
            f.write('    "com.unity.2d.tilemap": "1.0.0",\n')
            f.write('    "com.unity.analytics": "3.5.6",\n')
            f.write('    "com.unity.collab-proxy": "1.15.1",\n')
            f.write('    "com.unity.ext.nunit": "1.0.6",\n')
            f.write('    "com.unity.ide.rider": "3.0.15",\n')
            f.write('    "com.unity.ide.vs": "2.0.19",\n')
            f.write('    "com.unity.ide.vscode": "1.2.5",\n')
            f.write('    "com.unity.inputsystem": "1.4.1",\n')
            f.write('    "com.unity.purchasing": "4.6.0",\n')
            f.write('    "com.unity.test-framework": "1.1.33",\n')
            f.write('    "com.unity.textmeshpro": "3.0.6",\n')
            f.write('    "com.unity.timeline": "1.6.5",\n')
            f.write('    "com.unity.ugui": "1.0.0",\n')
            f.write('    "com.unity.modules.ai": "1.0.0",\n')
            f.write('    "com.unity.modules.androidjni": "1.0.0",\n')
            f.write('    "com.unity.modules.animation": "1.0.0",\n')
            f.write('    "com.unity.modules.assetbundle": "1.0.0",\n')
            f.write('    "com.unity.modules.audio": "1.0.0",\n')
            f.write('    "com.unity.modules.cloth": "1.0.0",\n')
            f.write('    "com.unity.modules.director": "1.0.0",\n')
            f.write('    "com.unity.modules.imageconversion": "1.0.0",\n')
            f.write('    "com.unity.modules.imgui": "1.0.0",\n')
            f.write('    "com.unity.modules.js": "1.0.0",\n')
            f.write('    "com.unity.modules.particlesystem": "1.0.0",\n')
            f.write('    "com.unity.modules.physics": "1.0.0",\n')
            f.write('    "com.unity.modules.physics2d": "1.0.0",\n')
            f.write('    "com.unity.modules.screencapture": "1.0.0",\n')
            f.write('    "com.unity.modules.terrain": "1.0.0",\n')
            f.write('    "com.unity.modules.terrainphysics": "1.0.0",\n')
            f.write('    "com.unity.modules.tilemap": "1.0.0",\n')
            f.write('    "com.unity.modules.ui": "1.0.0",\n')
            f.write('    "com.unity.modules.uielements": "1.0.0",\n')
            f.write('    "com.unity.modules.umbra": "1.0.0",\n')
            f.write('    "com.unity.modules.unityanalytics": "1.0.0",\n')
            f.write('    "com.unity.modules.unitywebrequest": "1.0.0",\n')
            f.write('    "com.unity.modules.vegetation": "1.0.0",\n')
            f.write('    "com.unity.modules.video": "1.0.0",\n')
            f.write('    "com.unity.modules.vr": "1.0.0",\n')
            f.write('    "com.unity.modules.wind": "1.0.0",\n')
            f.write('    "com.unity.modules.xr": "1.0.0"\n')
            f.write('  }\n')
            f.write('}\n')
    
    def add_scene(self, name: str, objects: List[Dict[str, Any]]) -> str:
        """Add a scene to the project."""
        scene_name = name if name else f"Scene_{len(self.scenes)}"
        scene_path = os.path.join(self.assets_dir, "Scenes", f"{scene_name}.unity")
        
        UnityYAMLWriter.write_scene(scene_path, objects)
        self.scenes.append(scene_path)
        
        return scene_path
    
    def add_prefab(self, name: str, objects: List[Dict[str, Any]]) -> str:
        """Add a prefab to the project."""
        prefab_name = name if name else f"Prefab_{len(self.prefabs)}"
        prefab_path = os.path.join(self.assets_dir, "Prefabs", f"{prefab_name}.prefab")
        
        # Prefabs use the same YAML format as scenes
        UnityYAMLWriter.write_scene(prefab_path, objects)
        self.prefabs.append(prefab_path)
        
        return prefab_path
    
    def add_texture(self, name: str, data: bytes) -> str:
        """Add a texture to the project."""
        texture_name = name if name else f"Texture_{len(self.textures)}"
        texture_path = os.path.join(self.assets_dir, "Textures", f"{texture_name}.png")
        
        with open(texture_path, 'wb') as f:
            f.write(data)
        
        self.textures.append(texture_path)
        return texture_path
    
    def add_material(self, name: str, shader: str, properties: Dict[str, Any]) -> str:
        """Add a material to the project."""
        material_name = name if name else f"Material_{len(self.materials)}"
        material_path = os.path.join(self.assets_dir, "Materials", f"{material_name}.mat")
        
        with open(material_path, 'w', encoding='utf-8') as f:
            f.write("%YAML 1.1\n")
            f.write("---\n")
            f.write("FileID: 10754\n")
            f.write("Guid: 0000000000000000f000000000000000\n")
            f.write("Type: 21\n")
            f.write(f"PathID: {len(self.materials) + 1}\n")
            f.write("\n")
            f.write("--- !u!21 &1\n")
            f.write("Material:\n")
            f.write(f"  serializedVersion: 5\n")
            f.write(f"  m_ObjectHideFlags: 0\n")
            f.write(f"  m_CorrespondingSourceObject: {{fileID: 0}}\n")
            f.write(f"  m_PrefabInstance: {{fileID: 0}}\n")
            f.write(f"  m_Name: {material_name}\n")
            f.write(f"  m_Shader: {{fileID: 48, guid: 0000000000000000f000000000000000, type: 0, pathID: 0}}\n")
            f.write(f"  m_ShaderKeywords: []\n")
            f.write(f"  m_LightmapFlags: 4\n")
            f.write(f"  m_EnableInstancingVariants: 0\n")
            f.write(f"  m_CustomRenderQueue: -1\n")
            f.write(f"  m_SavedProperties:\n")
            f.write(f"    m_TexEnvs:\n")
            f.write(f"    - m_Name: \n")
            f.write(f"      m_Texture: {{fileID: 0}}\n")
            f.write(f"      m_Scale: {{x: 1, y: 1}}\n")
            f.write(f"      m_Offset: {{x: 0, y: 0}}\n")
            f.write(f"    m_Floats:\n")
            f.write(f"    - m_Name: \n")
            f.write(f"      m_Value: 0\n")
            f.write(f"    m_Colors:\n")
            f.write(f"    - m_Name: \n")
            f.write(f"      m_Value: {{r: 1, g: 1, b: 1, a: 1}}\n")
        
        self.materials.append(material_path)
        return material_path
    
    def add_script(self, name: str, source: str) -> str:
        """Add a C# script to the project."""
        script_name = name if name else f"Script_{len(self.scripts)}"
        if not script_name.endswith('.cs'):
            script_name += '.cs'
        script_path = os.path.join(self.assets_dir, "Scripts", script_name)
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(source)
        
        self.scripts.append(script_path)
        return script_path
    
    def save_project_version(self) -> None:
        """Save ProjectVersion.txt."""
        version_path = os.path.join(self.output_dir, "ProjectSettings", "ProjectVersion.txt")
        os.makedirs(os.path.dirname(version_path), exist_ok=True)
        
        with open(version_path, 'w', encoding='utf-8') as f:
            f.write("m_EditorVersion: 2021.3\n")
            f.write("m_EditorVersionWithRevision: 2021.3.0f1\n")
    
    def finalize(self) -> None:
        """Finalize the project by saving all necessary files."""
        self.save_project_version()
