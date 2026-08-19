"""Asset extraction from Unity serialized files."""
import os
import struct
from typing import Dict, List, Optional, Any, Tuple
from .utils import Reader
from .serialized import SerializedFile, ObjectInfo, CLASS_IDS
from .textures import decode_texture, save_texture_as_png


# ============================================================
# PPtr (Pointer to serialized object)
# ============================================================

class PPtr:
    """Represents a pointer to another object in the serialized file."""
    __slots__ = ('file_id', 'path_id')
    
    def __init__(self, file_id: int = 0, path_id: int = 0):
        self.file_id = file_id
        self.path_id = path_id
    
    def __repr__(self):
        return f"PPtr(file_id={self.file_id}, path_id={self.path_id})"
    
    def __eq__(self, other):
        if not isinstance(other, PPtr):
            return False
        return self.file_id == other.file_id and self.path_id == other.path_id
    
    def __hash__(self):
        return hash((self.file_id, self.path_id))


# ============================================================
# Vector types
# ============================================================

class Vector2:
    __slots__ = ('x', 'y')
    
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y
    
    def __repr__(self):
        return f"Vector2({self.x}, {self.y})"
    
    @classmethod
    def from_reader(cls, reader: Reader) -> 'Vector2':
        return cls(reader.read_float(), reader.read_float())


class Vector3:
    __slots__ = ('x', 'y', 'z')
    
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = x
        self.y = y
        self.z = z
    
    def __repr__(self):
        return f"Vector3({self.x}, {self.y}, {self.z})"
    
    @classmethod
    def from_reader(cls, reader: Reader) -> 'Vector3':
        return cls(reader.read_float(), reader.read_float(), reader.read_float())


class Vector4:
    __slots__ = ('x', 'y', 'z', 'w')
    
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 0.0):
        self.x = x
        self.y = y
        self.z = z
        self.w = w
    
    def __repr__(self):
        return f"Vector4({self.x}, {self.y}, {self.z}, {self.w})"
    
    @classmethod
    def from_reader(cls, reader: Reader) -> 'Vector4':
        return cls(reader.read_float(), reader.read_float(), reader.read_float(), reader.read_float())


class Quaternion:
    __slots__ = ('x', 'y', 'z', 'w')
    
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 1.0):
        self.x = x
        self.y = y
        self.z = z
        self.w = w
    
    def __repr__(self):
        return f"Quaternion({self.x}, {self.y}, {self.z}, {self.w})"
    
    @classmethod
    def from_reader(cls, reader: Reader) -> 'Quaternion':
        return cls(reader.read_float(), reader.read_float(), reader.read_float(), reader.read_float())


class Color:
    __slots__ = ('r', 'g', 'b', 'a')
    
    def __init__(self, r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 1.0):
        self.r = r
        self.g = g
        self.b = b
        self.a = a
    
    def __repr__(self):
        return f"Color({self.r}, {self.g}, {self.b}, {self.a})"
    
    @classmethod
    def from_reader(cls, reader: Reader) -> 'Color':
        return cls(reader.read_float(), reader.read_float(), reader.read_float(), reader.read_float())


class Rect:
    __slots__ = ('x', 'y', 'width', 'height')
    
    def __init__(self, x: float = 0.0, y: float = 0.0, width: float = 0.0, height: float = 0.0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    @classmethod
    def from_reader(cls, reader: Reader) -> 'Rect':
        return cls(reader.read_float(), reader.read_float(), reader.read_float(), reader.read_float())


# ============================================================
# Asset Extractors
# ============================================================

class Texture2DExtractor:
    """Extract Texture2D assets."""
    
    @staticmethod
    def extract(obj: ObjectInfo, sf: SerializedFile) -> Optional[Dict[str, Any]]:
        """Extract Texture2D data from an object."""
        data = sf.get_object_data(obj)
        if not data:
            return None
        
        reader = Reader(data, sf.endian)
        
        result = {
            'class_id': obj.class_id,
            'path_id': obj.path_id,
            'name': '',
            'width': 0,
            'height': 0,
            'format': 0,
            'mip_count': 1,
            'image_data': b'',
            'stream_data': None,
        }
        
        try:
            # m_Name
            result['name'] = reader.read_al4string() if sf.version >= 21 else reader.read_cstring()
            
            # m_ForcedFallbackFormat (int32)
            _ = reader.read_i32()
            
            # m_DownscaleFallback (bool)
            _ = reader.read_bool()
            
            # m_Width (int32)
            result['width'] = reader.read_i32()
            
            # m_Height (int32)
            result['height'] = reader.read_i32()
            
            # m_CompleteImageSize (int32)
            _ = reader.read_i32()
            
            # m_TextureFormat (int32)
            result['format'] = reader.read_i32()
            
            # m_MipCount (int32)
            result['mip_count'] = reader.read_i32()
            
            # Skip various flags and settings
            for _ in range(10):
                if reader.remaining() <= 0:
                    break
                reader.read_i32()
            
            # m_ImageCount (int32) - for texture arrays
            image_count = reader.read_i32()
            
            # m_TextureDimension (int32)
            _ = reader.read_i32()
            
            # m_TextureSettings (struct)
            # Skip for now
            
            # m_LightmapFormat (int32)
            _ = reader.read_i32()
            
            # m_ColorSpace (int32)
            _ = reader.read_i32()
            
            # m_PlatformBlob (array) - skip
            # m_TextureData (array of bytes)
            data_size = reader.read_u32()
            if data_size > 0 and reader.remaining() >= data_size:
                result['image_data'] = reader.read_bytes(data_size)
            
            # m_StreamData (struct: size, offset, path)
            if reader.remaining() >= 12:
                stream_size = reader.read_u32()
                stream_offset = reader.read_u32()
                stream_path = reader.read_cstring()
                result['stream_data'] = {
                    'size': stream_size,
                    'offset': stream_offset,
                    'path': stream_path
                }
            
        except Exception as e:
            print(f"Error extracting Texture2D: {e}")
            return None
        
        return result


class SpriteExtractor:
    """Extract Sprite assets."""
    
    @staticmethod
    def extract(obj: ObjectInfo, sf: SerializedFile) -> Optional[Dict[str, Any]]:
        """Extract Sprite data from an object."""
        data = sf.get_object_data(obj)
        if not data:
            return None
        
        reader = Reader(data, sf.endian)
        
        result = {
            'class_id': obj.class_id,
            'path_id': obj.path_id,
            'name': '',
            'rect': None,
            'offset': None,
            'border': None,
            'pixels_to_units': 1.0,
            'texture': None,
        }
        
        try:
            result['name'] = reader.read_al4string() if sf.version >= 21 else reader.read_cstring()
            result['rect'] = Rect.from_reader(reader)
            result['offset'] = Vector2.from_reader(reader)
            result['border'] = Vector4.from_reader(reader)
            result['pixels_to_units'] = reader.read_float()
            
            # m_PixelsPerUnit (float) - 2021.2+
            if reader.remaining() >= 4:
                _ = reader.read_float()
            
            # m_AtlasTags (array of strings)
            tag_count = reader.read_u32()
            tags = []
            for _ in range(tag_count):
                tags.append(reader.read_al4string() if sf.version >= 21 else reader.read_cstring())
            result['tags'] = tags
            
            # m_Texture (PPtr)
            file_id = reader.read_i32()
            path_id = reader.read_u64() if sf.version >= 14 else reader.read_u32()
            result['texture'] = PPtr(file_id, path_id)
            
            # m_AtlasTexture (PPtr)
            file_id = reader.read_i32()
            path_id = reader.read_u64() if sf.version >= 14 else reader.read_u32()
            result['atlas_texture'] = PPtr(file_id, path_id)
            
            # m_SpriteID (GUID)
            if reader.remaining() >= 16:
                result['sprite_id'] = reader.read_bytes(16)
            
        except Exception as e:
            print(f"Error extracting Sprite: {e}")
            return None
        
        return result


class MeshExtractor:
    """Extract Mesh assets."""
    
    @staticmethod
    def extract(obj: ObjectInfo, sf: SerializedFile) -> Optional[Dict[str, Any]]:
        """Extract Mesh data from an object."""
        data = sf.get_object_data(obj)
        if not data:
            return None
        
        reader = Reader(data, sf.endian)
        
        result = {
            'class_id': obj.class_id,
            'path_id': obj.path_id,
            'name': '',
            'vertices': [],
            'normals': [],
            'tangents': [],
            'uv': [],
            'colors': [],
            'triangles': [],
            'bindposes': [],
            'bone_name_hashes': [],
            'submeshes': [],
        }
        
        try:
            result['name'] = reader.read_al4string() if sf.version >= 21 else reader.read_cstring()
            
            # m_SubMeshes (array)
            submesh_count = reader.read_u32()
            for _ in range(submesh_count):
                first_byte = reader.read_u32()
                index_count = reader.read_u32()
                topology = reader.read_u32()
                first_vertex = reader.read_u32()
                vertex_count = reader.read_u32()
                local_aabb = {
                    'center': Vector3.from_reader(reader),
                    'extent': Vector3.from_reader(reader),
                }
                result['submeshes'].append({
                    'first_byte': first_byte,
                    'index_count': index_count,
                    'topology': topology,
                    'first_vertex': first_vertex,
                    'vertex_count': vertex_count,
                    'local_aabb': local_aabb,
                })
            
            # Skip m_Shapes (BlendShapes) for now
            # Skip m_BindPose
            # Skip m_BoneNameHashes
            # Skip m_RootBoneNameHash
            
            # m_MeshCompression (uint8)
            _ = reader.read_u8()
            
            # m_IsReadable (bool)
            _ = reader.read_bool()
            
            # m_KeepVertices (bool)
            _ = reader.read_bool()
            
            # m_KeepIndices (bool)
            _ = reader.read_bool()
            
            # m_IndexFormat (uint8) - 2017.3+
            if sf.version >= 23:
                _ = reader.read_u8()
            
            # m_IndexBuffer (array of bytes)
            index_buffer_size = reader.read_u32()
            if index_buffer_size > 0:
                result['index_buffer'] = reader.read_bytes(index_buffer_size)
            
            # m_VertexData (struct)
            # m_CurrentChannels (uint32 bitmask)
            current_channels = reader.read_u32()
            
            # m_VertexCount (int32)
            vertex_count = reader.read_i32()
            
            # m_VertexStrides (array of uint32)
            stride_count = reader.read_u32()
            strides = [reader.read_u32() for _ in range(stride_count)]
            
            # m_Channels (array of ChannelInfo)
            channel_count = reader.read_u32()
            channels = []
            for _ in range(channel_count):
                stream = reader.read_u8()
                offset = reader.read_u8()
                format = reader.read_u8()
                dimension = reader.read_u8()
                channels.append({
                    'stream': stream,
                    'offset': offset,
                    'format': format,
                    'dimension': dimension,
                })
            
            result['vertex_data'] = {
                'current_channels': current_channels,
                'vertex_count': vertex_count,
                'strides': strides,
                'channels': channels,
            }
            
            # m_DataSize (uint32)
            data_size = reader.read_u32()
            if data_size > 0:
                result['vertex_buffer'] = reader.read_bytes(data_size)
            
        except Exception as e:
            print(f"Error extracting Mesh: {e}")
            return None
        
        return result


class AudioClipExtractor:
    """Extract AudioClip assets."""
    
    @staticmethod
    def extract(obj: ObjectInfo, sf: SerializedFile) -> Optional[Dict[str, Any]]:
        """Extract AudioClip data from an object."""
        data = sf.get_object_data(obj)
        if not data:
            return None
        
        reader = Reader(data, sf.endian)
        
        result = {
            'class_id': obj.class_id,
            'path_id': obj.path_id,
            'name': '',
            'load_type': 0,
            'channels': 0,
            'frequency': 0,
            'bits_per_sample': 0,
            'length': 0.0,
            'audio_data': b'',
            'stream_data': None,
        }
        
        try:
            result['name'] = reader.read_al4string() if sf.version >= 21 else reader.read_cstring()
            
            # m_LoadType (int32)
            result['load_type'] = reader.read_i32()
            
            # m_Channels (int32)
            result['channels'] = reader.read_i32()
            
            # m_Frequency (int32)
            result['frequency'] = reader.read_i32()
            
            # m_BitsPerSample (int32)
            result['bits_per_sample'] = reader.read_i32()
            
            # m_Length (float)
            result['length'] = reader.read_float()
            
            # m_IsTrackerFormat (bool)
            _ = reader.read_bool()
            
            # m_SubsoundIndex (int32)
            _ = reader.read_i32()
            
            # m_PreloadAudioData (bool)
            _ = reader.read_bool()
            
            # m_LoadInBackground (bool)
            _ = reader.read_bool()
            
            # m_Legacy3D (bool)
            _ = reader.read_bool()
            
            # m_Resource (PPtr)
            file_id = reader.read_i32()
            path_id = reader.read_u64() if sf.version >= 14 else reader.read_u32()
            result['resource'] = PPtr(file_id, path_id)
            
            # m_CompressionFormat (int32) - 2017.2+
            if sf.version >= 22:
                _ = reader.read_i32()
            
            # m_NonStreamableData (array of bytes)
            data_size = reader.read_u32()
            if data_size > 0:
                result['audio_data'] = reader.read_bytes(data_size)
            
            # m_StreamData (struct)
            if reader.remaining() >= 12:
                stream_size = reader.read_u32()
                stream_offset = reader.read_u32()
                stream_path = reader.read_cstring()
                result['stream_data'] = {
                    'size': stream_size,
                    'offset': stream_offset,
                    'path': stream_path
                }
            
        except Exception as e:
            print(f"Error extracting AudioClip: {e}")
            return None
        
        return result


class TextAssetExtractor:
    """Extract TextAsset assets."""
    
    @staticmethod
    def extract(obj: ObjectInfo, sf: SerializedFile) -> Optional[Dict[str, Any]]:
        """Extract TextAsset data from an object."""
        data = sf.get_object_data(obj)
        if not data:
            return None
        
        reader = Reader(data, sf.endian)
        
        result = {
            'class_id': obj.class_id,
            'path_id': obj.path_id,
            'name': '',
            'script': b'',
        }
        
        try:
            result['name'] = reader.read_al4string() if sf.version >= 21 else reader.read_cstring()
            
            # m_Script (array of bytes)
            script_size = reader.read_u32()
            if script_size > 0:
                result['script'] = reader.read_bytes(script_size)
            
        except Exception as e:
            print(f"Error extracting TextAsset: {e}")
            return None
        
        return result


class MonoBehaviourExtractor:
    """Extract MonoBehaviour assets."""
    
    @staticmethod
    def extract(obj: ObjectInfo, sf: SerializedFile) -> Optional[Dict[str, Any]]:
        """Extract MonoBehaviour data from an object."""
        data = sf.get_object_data(obj)
        if not data:
            return None
        
        reader = Reader(data, sf.endian)
        
        result = {
            'class_id': obj.class_id,
            'path_id': obj.path_id,
            'game_object': None,
            'enabled': True,
            'script': None,
            'name': '',
            'script_data': b'',
        }
        
        try:
            # m_GameObject (PPtr)
            file_id = reader.read_i32()
            path_id = reader.read_u64() if sf.version >= 14 else reader.read_u32()
            result['game_object'] = PPtr(file_id, path_id)
            
            # m_Enabled (bool)
            result['enabled'] = reader.read_bool()
            reader.align(4)
            
            # m_Script (PPtr)
            file_id = reader.read_i32()
            path_id = reader.read_u64() if sf.version >= 14 else reader.read_u32()
            result['script'] = PPtr(file_id, path_id)
            
            # m_Name (string)
            result['name'] = reader.read_al4string() if sf.version >= 21 else reader.read_cstring()
            
            # The rest is script-specific serialized data
            result['script_data'] = reader.read_bytes(reader.remaining())
            
        except Exception as e:
            print(f"Error extracting MonoBehaviour: {e}")
            return None
        
        return result


class MonoScriptExtractor:
    """Extract MonoScript assets."""
    
    @staticmethod
    def extract(obj: ObjectInfo, sf: SerializedFile) -> Optional[Dict[str, Any]]:
        """Extract MonoScript data from an object."""
        data = sf.get_object_data(obj)
        if not data:
            return None
        
        reader = Reader(data, sf.endian)
        
        result = {
            'class_id': obj.class_id,
            'path_id': obj.path_id,
            'name': '',
            'class_name': '',
            'namespace': '',
            'assembly_name': '',
            'is_editor_script': False,
            'execution_order': 0,
        }
        
        try:
            result['name'] = reader.read_al4string() if sf.version >= 21 else reader.read_cstring()
            result['class_name'] = reader.read_al4string() if sf.version >= 21 else reader.read_cstring()
            result['namespace'] = reader.read_al4string() if sf.version >= 21 else reader.read_cstring()
            result['assembly_name'] = reader.read_al4string() if sf.version >= 21 else reader.read_cstring()
            result['is_editor_script'] = reader.read_bool()
            reader.align(4)
            result['execution_order'] = reader.read_i32()
            
        except Exception as e:
            print(f"Error extracting MonoScript: {e}")
            return None
        
        return result


# ============================================================
# Extractor Registry
# ============================================================

EXTRACTORS = {
    1: None,  # GameObject - handled specially
    4: None,  # Transform - handled specially
    20: None,  # Camera
    21: None,  # Material
    23: None,  # MeshRenderer
    27: None,  # Texture
    28: Texture2DExtractor,
    33: None,  # MeshFilter
    43: MeshExtractor,
    48: None,  # Shader
    49: TextAssetExtractor,
    82: AudioClipExtractor,
    83: AudioClipExtractor,
    95: None,  # Animator
    111: None,  # Animation
    114: MonoBehaviourExtractor,
    115: MonoScriptExtractor,
    128: None,  # Font
    137: None,  # SkinnedMeshRenderer
    198: None,  # ParticleSystem
    212: SpriteExtractor,
    213: SpriteExtractor,
    223: None,  # Canvas
    224: None,  # RectTransform
}


# ============================================================
# Main Extraction Functions
# ============================================================

def extract_asset(obj: ObjectInfo, sf: SerializedFile) -> Optional[Dict[str, Any]]:
    """Extract an asset from a serialized object."""
    extractor = EXTRACTORS.get(obj.class_id)
    if extractor is None:
        # Generic extraction - just return raw data
        return {
            'class_id': obj.class_id,
            'class_name': sf.get_class_name(obj.class_id),
            'path_id': obj.path_id,
            'raw_data': sf.get_object_data(obj),
        }
    
    return extractor.extract(obj, sf)


def extract_all_assets(sf: SerializedFile) -> List[Dict[str, Any]]:
    """Extract all assets from a serialized file."""
    results = []
    for obj in sf.objects:
        asset = extract_asset(obj, sf)
        if asset is not None:
            results.append(asset)
    return results


def save_extracted_assets(sf: SerializedFile, output_dir: str) -> Dict[str, str]:
    """
    Extract and save all assets from a serialized file.
    
    Returns:
        Dictionary mapping path_id to saved file path
    """
    import os
    from .textures import save_texture_as_png
    
    os.makedirs(output_dir, exist_ok=True)
    saved_files = {}
    
    for obj in sf.objects:
        asset = extract_asset(obj, sf)
        if asset is None:
            continue
        
        class_name = sf.get_class_name(obj.class_id)
        
        # Handle textures
        if obj.class_id == 28:  # Texture2D
            if 'image_data' in asset and asset['image_data']:
                name = asset.get('name', f"texture_{obj.path_id}")
                if not name or name.startswith(' '):
                    name = f"texture_{obj.path_id}"
                
                # Clean name for filesystem
                clean_name = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in name)
                if not clean_name:
                    clean_name = f"texture_{obj.path_id}"
                
                png_path = os.path.join(output_dir, f"{clean_name}.png")
                if save_texture_as_png(
                    asset['image_data'],
                    asset.get('format', 3),
                    asset.get('width', 0),
                    asset.get('height', 0),
                    png_path
                ):
                    saved_files[obj.path_id] = png_path
        
        # Handle text assets
        elif obj.class_id == 49:  # TextAsset
            name = asset.get('name', f"text_{obj.path_id}")
            clean_name = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in name)
            if not clean_name:
                clean_name = f"text_{obj.path_id}"
            
            ext = '.txt'
            if name.lower().endswith('.json'):
                ext = '.json'
            elif name.lower().endswith('.csv'):
                ext = '.csv'
            elif name.lower().endswith('.xml'):
                ext = '.xml'
            
            text_path = os.path.join(output_dir, f"{clean_name}{ext}")
            with open(text_path, 'wb') as f:
                f.write(asset.get('script', b''))
            saved_files[obj.path_id] = text_path
        
        # Handle audio clips
        elif obj.class_id in (82, 83):  # AudioSource, AudioClip
            name = asset.get('name', f"audio_{obj.path_id}")
            clean_name = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in name)
            if not clean_name:
                clean_name = f"audio_{obj.path_id}"
            
            # Determine extension based on load type
            load_type = asset.get('load_type', 0)
            if load_type == 1:  # CompressedInMemory
                ext = '.ogg'
            elif load_type == 2:  # StreamFromDisc
                ext = '.ogg'
            else:
                ext = '.raw'
            
            audio_path = os.path.join(output_dir, f"{clean_name}{ext}")
            with open(audio_path, 'wb') as f:
                f.write(asset.get('audio_data', b''))
            saved_files[obj.path_id] = audio_path
    
    return saved_files
