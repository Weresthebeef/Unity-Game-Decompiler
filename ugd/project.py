"""
Unity project reconstruction.
Creates a reconstructable Unity project from decompiled assets.
"""
import os
import json
from typing import Dict, List, Optional, Any, Tuple
from .serialized import SerializedFile
from .extract import extract_all_assets, save_extracted_assets
from .unityyaml import UnityProjectBuilder
from .il2cpp import Il2CppMetadataParser
from .mono.decompile import MonoDecompiler


class ProjectReconstructor:
    """Reconstructs a Unity project from game files."""
    
    def __init__(self, output_dir: str, game_name: str = "DecompiledGame"):
        self.output_dir = os.path.abspath(output_dir)
        self.game_name = game_name
        self.project_builder = UnityProjectBuilder(self.output_dir, self.game_name)
        self.assets: List[Dict[str, Any]] = []
        self.scripts: Dict[str, str] = {}
        self.is_mono = False
        self.is_il2cpp = False
        self.unity_version = "2021.3"

    def create_structure(self) -> None:
        """Create the base Unity project directory structure."""
        self.project_builder.create_structure()

    def finalize(self) -> None:
        """Finalize the project (write settings, manifests, etc.)."""
        self.project_builder.finalize()

    def add_script(self, name: str, source: str) -> None:
        """Register a decompiled script for later writing."""
        self.scripts[name] = source
    
    def detect_game_type(self, data_dir: str) -> None:
        """Detect if the game is Mono or IL2CPP."""
        # Check for Managed folder (Mono)
        managed_dir = os.path.join(data_dir, "Managed")
        if os.path.exists(managed_dir):
            self.is_mono = True
            return
        
        # Check for global-metadata.dat (IL2CPP)
        metadata_path = os.path.join(data_dir, "global-metadata.dat")
        if os.path.exists(metadata_path):
            self.is_il2cpp = True
            return
        
        # Check for libil2cpp.so (IL2CPP on Android)
        libil2cpp_path = os.path.join(data_dir, "libil2cpp.so")
        if os.path.exists(libil2cpp_path):
            self.is_il2cpp = True
            return
    
    def extract_from_directory(self, data_dir: str) -> None:
        """Extract assets from a game data directory."""
        self.detect_game_type(data_dir)
        
        # Create project structure
        self.project_builder.create_structure()
        
        # Extract assets from .assets files
        self._extract_assets(data_dir)
        
        # Extract from bundles
        self._extract_bundles(data_dir)
        
        # Handle Mono assemblies
        if self.is_mono:
            self._extract_mono_assemblies(data_dir)
        
        # Handle IL2CPP metadata
        if self.is_il2cpp:
            self._extract_il2cpp_metadata(data_dir)
        
        # Finalize project
        self.project_builder.finalize()
    
    def _extract_assets(self, data_dir: str) -> None:
        """Extract assets from .assets files."""
        import glob
        
        # Find all .assets files
        assets_pattern = os.path.join(data_dir, "**", "*.assets")
        assets_files = glob.glob(assets_pattern, recursive=True)
        
        for assets_file in assets_files:
            self._extract_single_assets(assets_file)
    
    def _extract_single_assets(self, assets_path: str) -> None:
        """Extract a single .assets file."""
        with open(assets_path, 'rb') as f:
            data = f.read()
        
        sf = SerializedFile()
        if sf.parse(data):
            # Extract assets
            assets = extract_all_assets(sf)
            self.assets.extend(assets)
            
            # Save extracted assets
            rel_path = os.path.relpath(assets_path, self.output_dir)
            output_dir = os.path.join(self.output_dir, "Assets", "Extracted", os.path.splitext(rel_path)[0])
            os.makedirs(output_dir, exist_ok=True)
            save_extracted_assets(sf, output_dir)
            
            # Reconstruct scenes/prefabs
            self._reconstruct_scene(sf, assets_path)
    
    def _extract_bundles(self, data_dir: str) -> None:
        """Extract assets from .unity3d bundles."""
        import glob
        from .unityfs import BundleFile
        
        # Find all .unity3d files
        bundle_pattern = os.path.join(data_dir, "**", "*.unity3d")
        bundle_files = glob.glob(bundle_pattern, recursive=True)
        
        for bundle_file in bundle_files:
            with open(bundle_file, 'rb') as f:
                data = f.read()
            
            bundle = BundleFile()
            if bundle.parse(data):
                # Extract all entries
                extracted = bundle.extract_all()
                
                # Save extracted files
                bundle_name = os.path.splitext(os.path.basename(bundle_file))[0]
                bundle_dir = os.path.join(self.output_dir, "Assets", "Bundles", bundle_name)
                os.makedirs(bundle_dir, exist_ok=True)
                
                for name, content in extracted.items():
                    output_path = os.path.join(bundle_dir, name)
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(content)
                    
                    # If it's an .assets file, process it
                    if name.endswith('.assets'):
                        sf = SerializedFile()
                        if sf.parse(content):
                            self._reconstruct_scene(sf, output_path)
    
    def _extract_mono_assemblies(self, data_dir: str) -> None:
        """Extract and decompile Mono assemblies."""
        import glob
        from .mono.pe import MonoAssembly
        
        # Find all .dll files in Managed folder
        managed_dir = os.path.join(data_dir, "Managed")
        if not os.path.exists(managed_dir):
            return
        
        dll_pattern = os.path.join(managed_dir, "*.dll")
        dll_files = glob.glob(dll_pattern)
        
        decompiler = MonoDecompiler()
        
        for dll_file in dll_files:
            assembly = decompiler.load_assembly(dll_file)
            if assembly:
                # Decompile all methods
                results = decompiler.decompile_assembly(assembly)
                
                # Save decompiled code
                dll_name = os.path.splitext(os.path.basename(dll_file))[0]
                output_dir = os.path.join(self.output_dir, "Assets", "Scripts", dll_name)
                os.makedirs(output_dir, exist_ok=True)
                
                for name, source in results.items():
                    output_path = os.path.join(output_dir, f"{name}.cs")
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(source)
                
                # Also copy the original DLL
                dll_output = os.path.join(self.output_dir, "Assets", "Plugins", f"{dll_name}.dll")
                os.makedirs(os.path.dirname(dll_output), exist_ok=True)
                with open(dll_file, 'rb') as src, open(dll_output, 'wb') as dst:
                    dst.write(src.read())
    
    def _extract_il2cpp_metadata(self, data_dir: str) -> None:
        """Extract IL2CPP metadata and generate C# skeletons."""
        metadata_path = os.path.join(data_dir, "global-metadata.dat")
        if not os.path.exists(metadata_path):
            return
        
        with open(metadata_path, 'rb') as f:
            data = f.read()
        
        parser = Il2CppMetadataParser()
        if parser.parse(data):
            # Generate C# skeletons
            skeletons = parser.generate_csharp_skeletons()
            
            # Save skeletons
            scripts_dir = os.path.join(self.output_dir, "Assets", "Scripts", "Il2CppSkeletons")
            os.makedirs(scripts_dir, exist_ok=True)
            
            for type_name, source in skeletons.items():
                safe_name = ''.join(c if c.isalnum() or c in ('_', '.') else '_' for c in type_name)
                if not safe_name or safe_name.startswith('.'):
                    safe_name = safe_name.lstrip('.') or 'Unknown'
                
                parts = safe_name.rsplit('.', 1)
                if len(parts) == 2:
                    namespace = parts[0]
                    class_name = parts[1]
                    ns_dir = os.path.join(scripts_dir, *namespace.split('.'))
                    os.makedirs(ns_dir, exist_ok=True)
                    output_path = os.path.join(ns_dir, f"{class_name}.cs")
                else:
                    output_path = os.path.join(scripts_dir, f"{safe_name}.cs")
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(source)
            
            # Dump metadata info
            parser.dump(os.path.join(self.output_dir, "Il2CppMetadata"))
    
    def _reconstruct_scene(self, sf: SerializedFile, source_path: str) -> None:
        """Reconstruct a Unity scene from a serialized file."""
        # This is a simplified reconstruction
        # A full implementation would parse all objects and their relationships
        
        scene_name = os.path.splitext(os.path.basename(source_path))[0]
        if scene_name == "globalgamemanagers":
            return  # Skip global game managers
        
        # Collect scene objects
        scene_objects = []
        
        for obj in sf.objects:
            class_id = obj.class_id
            class_name = sf.get_class_name(class_id)
            
            # Skip certain types
            if class_id in [0, 1, 2, 3, 4, 5, 6, 8, 9, 11, 13, 18, 19, 20]:
                # These are core types we want to include
                scene_objects.append({
                    'class_id': class_id,
                    'class_name': class_name,
                    'path_id': obj.path_id,
                    'name': f"{class_name}_{obj.path_id}",
                })
        
        if scene_objects:
            # Add as a scene
            self.project_builder.add_scene(scene_name, scene_objects)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a report of what was decompiled."""
        return {
            'game_name': self.game_name,
            'output_dir': self.output_dir,
            'is_mono': self.is_mono,
            'is_il2cpp': self.is_il2cpp,
            'unity_version': self.unity_version,
            'asset_count': len(self.assets),
            'script_count': len(self.scripts),
        }
