"""
Hardcoded schemas for Unity types when type trees are stripped.
Used for parsing serialized objects without type information.
"""
from typing import Dict, List, Tuple, Any, Optional, Callable
from .utils import Reader


# Schema field types
SCHEMA_INT = 'i'
SCHEMA_UINT = 'u'
SCHEMA_BOOL = 'b'
SCHEMA_FLOAT = 'f'
SCHEMA_STRING = 's'
SCHEMA_PPTR = 'p'
SCHEMA_ARRAY = 'a'
SCHEMA_VECTOR2 = 'v2'
SCHEMA_VECTOR3 = 'v3'
SCHEMA_VECTOR4 = 'v4'
SCHEMA_QUATERNION = 'q'
SCHEMA_COLOR = 'c'
SCHEMA_RECT = 'r'
SCHEMA_BYTES = 'by'
SCHEMA_SKIP = 'skip'


class SchemaField:
    """A field in a type schema."""
    __slots__ = ('name', 'type', 'count', 'element_type', 'version_min', 'version_max', 'condition')
    
    def __init__(
        self,
        name: str,
        type: str,
        count: Optional[int] = None,
        element_type: Optional[str] = None,
        version_min: int = 0,
        version_max: int = 999,
        condition: Optional[Callable[[int], bool]] = None
    ):
        self.name = name
        self.type = type
        self.count = count
        self.element_type = element_type
        self.version_min = version_min
        self.version_max = version_max
        self.condition = condition
    
    def is_applicable(self, version: int) -> bool:
        if self.version_min > version or version > self.version_max:
            return False
        if self.condition is not None:
            return self.condition(version)
        return True


class TypeSchema:
    """Schema for a Unity type."""
    __slots__ = ('class_id', 'name', 'fields', 'version_min', 'version_max')
    
    def __init__(self, class_id: int, name: str, version_min: int = 0, version_max: int = 999):
        self.class_id = class_id
        self.name = name
        self.fields: List[SchemaField] = []
        self.version_min = version_min
        self.version_max = version_max
    
    def add_field(self, *args, **kwargs) -> 'TypeSchema':
        self.fields.append(SchemaField(*args, **kwargs))
        return self
    
    def is_applicable(self, version: int) -> bool:
        return self.version_min <= version <= self.version_max


# ============================================================
# Schema Definitions
# ============================================================

# Helper to create version condition
def version_ge(min_ver: int) -> Callable[[int], bool]:
    return lambda v: v >= min_ver


def version_lt(max_ver: int) -> Callable[[int], bool]:
    return lambda v: v < max_ver


def version_range(min_ver: int, max_ver: int) -> Callable[[int], bool]:
    return lambda v: min_ver <= v <= max_ver


# Build schemas
SCHEMAS: Dict[int, TypeSchema] = {}


def register_schema(schema: TypeSchema) -> TypeSchema:
    SCHEMAS[schema.class_id] = schema
    return schema


# --- GameObject ---
@register_schema
class GameObjectSchema(TypeSchema):
    def __init__(self):
        super().__init__(1, "GameObject")
        self.add_field('m_Component', SCHEMA_ARRAY, element_type=SCHEMA_PPTR)
        self.add_field('m_Layer', SCHEMA_INT)
        self.add_field('m_Name', SCHEMA_STRING)
        self.add_field('m_TagString', SCHEMA_STRING)
        self.add_field('m_IsActive', SCHEMA_BOOL)


# --- Component ---
@register_schema
class ComponentSchema(TypeSchema):
    def __init__(self):
        super().__init__(2, "Component")
        self.add_field('m_GameObject', SCHEMA_PPTR)


# --- Transform ---
@register_schema
class TransformSchema(TypeSchema):
    def __init__(self):
        super().__init__(4, "Transform")
        self.add_field('m_GameObject', SCHEMA_PPTR)
        self.add_field('m_LocalRotation', SCHEMA_QUATERNION)
        self.add_field('m_LocalPosition', SCHEMA_VECTOR3)
        self.add_field('m_LocalScale', SCHEMA_VECTOR3)
        self.add_field('m_ConstrainProportionsScale', SCHEMA_BOOL, version_min=5)
        self.add_field('m_Children', SCHEMA_ARRAY, element_type=SCHEMA_PPTR)
        self.add_field('m_Father', SCHEMA_PPTR)
        self.add_field('m_LocalEulerAnglesHint', SCHEMA_VECTOR3, version_min=5)


# --- RectTransform ---
@register_schema
class RectTransformSchema(TypeSchema):
    def __init__(self):
        super().__init__(224, "RectTransform", version_min=20)
        self.add_field('m_GameObject', SCHEMA_PPTR)
        self.add_field('m_LocalRotation', SCHEMA_QUATERNION)
        self.add_field('m_LocalPosition', SCHEMA_VECTOR3)
        self.add_field('m_LocalScale', SCHEMA_VECTOR3)
        self.add_field('m_ConstrainProportionsScale', SCHEMA_BOOL)
        self.add_field('m_Children', SCHEMA_ARRAY, element_type=SCHEMA_PPTR)
        self.add_field('m_Father', SCHEMA_PPTR)
        self.add_field('m_LocalEulerAnglesHint', SCHEMA_VECTOR3)
        self.add_field('m_AnchorMin', SCHEMA_VECTOR2)
        self.add_field('m_AnchorMax', SCHEMA_VECTOR2)
        self.add_field('m_AnchoredPosition', SCHEMA_VECTOR2)
        self.add_field('m_SizeDelta', SCHEMA_VECTOR2)
        self.add_field('m_Pivot', SCHEMA_VECTOR2)


# --- Camera ---
@register_schema
class CameraSchema(TypeSchema):
    def __init__(self):
        super().__init__(20, "Camera")
        self.add_field('m_GameObject', SCHEMA_PPTR)
        self.add_field('m_Enabled', SCHEMA_BOOL)
        self.add_field('m_ClearFlags', SCHEMA_INT)
        self.add_field('m_BackGroundColor', SCHEMA_COLOR)
        self.add_field('m_CullingMask', SCHEMA_UINT)
        self.add_field('m_TargetDisplay', SCHEMA_INT)
        self.add_field('m_TargetTexture', SCHEMA_PPTR)


# --- MeshRenderer ---
@register_schema
class MeshRendererSchema(TypeSchema):
    def __init__(self):
        super().__init__(23, "MeshRenderer")
        self.add_field('m_GameObject', SCHEMA_PPTR)
        self.add_field('m_Enabled', SCHEMA_BOOL)
        self.add_field('m_CastShadows', SCHEMA_INT)
        self.add_field('m_ReceiveShadows', SCHEMA_BOOL)
        self.add_field('m_DynamicOccludee', SCHEMA_BOOL)
        self.add_field('m_StaticShadowCaster', SCHEMA_BOOL)
        self.add_field('m_MotionVectors', SCHEMA_BOOL)
        self.add_field('m_LightProbeUsage', SCHEMA_INT)
        self.add_field('m_ReflectionProbeUsage', SCHEMA_INT)
        self.add_field('m_RayTracingMode', SCHEMA_INT, version_min=30)
        self.add_field('m_RayTraceProcedural', SCHEMA_BOOL, version_min=30)
        self.add_field('m_Materials', SCHEMA_ARRAY, element_type=SCHEMA_PPTR)
        self.add_field('m_StaticBatchInfo', 'struct', version_min=20)  # Skip
        self.add_field('m_StaticBatchRoot', SCHEMA_PPTR, version_min=20)
        self.add_field('m_ProbeAnchor', SCHEMA_PPTR, version_min=25)
        self.add_field('m_LightmapParameters', SCHEMA_PPTR, version_min=20)
        self.add_field('m_SortingLayerID', SCHEMA_INT, version_min=25)
        self.add_field('m_SortingLayer', SCHEMA_INT, version_min=25)
        self.add_field('m_SortingOrder', SCHEMA_INT, version_min=25)


# --- MeshFilter ---
@register_schema
class MeshFilterSchema(TypeSchema):
    def __init__(self):
        super().__init__(33, "MeshFilter")
        self.add_field('m_GameObject', SCHEMA_PPTR)
        self.add_field('m_Mesh', SCHEMA_PPTR)


# --- Texture2D ---
@register_schema
class Texture2DSchema(TypeSchema):
    def __init__(self):
        super().__init__(28, "Texture2D")
        self.add_field('m_Name', SCHEMA_STRING)
        self.add_field('m_ForcedFallbackFormat', SCHEMA_INT)
        self.add_field('m_DownscaleFallback', SCHEMA_BOOL)
        self.add_field('m_Width', SCHEMA_INT)
        self.add_field('m_Height', SCHEMA_INT)
        self.add_field('m_CompleteImageSize', SCHEMA_INT)
        self.add_field('m_TextureFormat', SCHEMA_INT)
        self.add_field('m_MipCount', SCHEMA_INT)
        self.add_field('m_IsReadable', SCHEMA_BOOL)
        self.add_field('m_StreamingMipmaps', SCHEMA_BOOL)
        self.add_field('m_StreamingMipmapsPriority', SCHEMA_INT, version_min=25)
        self.add_field('m_ImageCount', SCHEMA_INT, version_min=25)
        self.add_field('m_TextureDimension', SCHEMA_INT, version_min=25)
        self.add_field('m_LightmapFormat', SCHEMA_INT, version_min=20)
        self.add_field('m_ColorSpace', SCHEMA_INT, version_min=20)
        self.add_field('m_TextureSettings', 'struct', version_min=22)  # Skip
        self.add_field('m_PlatformBlob', SCHEMA_BYTES, version_min=25)  # Skip
        self.add_field('m_TextureData', SCHEMA_BYTES)
        self.add_field('m_StreamData', 'struct')  # Skip


# --- Sprite ---
@register_schema
class SpriteSchema(TypeSchema):
    def __init__(self):
        super().__init__(213, "Sprite")
        self.add_field('m_Name', SCHEMA_STRING)
        self.add_field('m_Rect', SCHEMA_RECT)
        self.add_field('m_Offset', SCHEMA_VECTOR2)
        self.add_field('m_Border', SCHEMA_VECTOR4)
        self.add_field('m_PixelsToUnits', SCHEMA_FLOAT)
        self.add_field('m_PixelsPerUnit', SCHEMA_FLOAT, version_min=25)
        self.add_field('m_AtlasTags', SCHEMA_ARRAY, element_type=SCHEMA_STRING)
        self.add_field('m_Texture', SCHEMA_PPTR)
        self.add_field('m_AtlasTexture', SCHEMA_PPTR, version_min=25)
        self.add_field('m_SecondaryTextures', SCHEMA_ARRAY, version_min=25)  # Skip
        self.add_field('m_SpriteID', SCHEMA_BYTES, version_min=25)  # GUID


# --- Material ---
@register_schema
class MaterialSchema(TypeSchema):
    def __init__(self):
        super().__init__(21, "Material")
        self.add_field('m_Name', SCHEMA_STRING)
        self.add_field('m_Shader', SCHEMA_PPTR)
        self.add_field('m_ShaderKeywords', SCHEMA_ARRAY, element_type=SCHEMA_STRING)
        self.add_field('m_LightmapFlags', SCHEMA_INT)
        self.add_field('m_EnableInstancingVariants', SCHEMA_BOOL, version_min=25)
        self.add_field('m_CustomRenderQueue', SCHEMA_INT)
        self.add_field('m_SavedProperties', 'struct')  # Skip


# --- Shader ---
@register_schema
class ShaderSchema(TypeSchema):
    def __init__(self):
        super().__init__(48, "Shader")
        self.add_field('m_Name', SCHEMA_STRING)
        self.add_field('m_Path', SCHEMA_STRING)
        self.add_field('m_SubShader', SCHEMA_ARRAY)  # Skip
        self.add_field('m_DefaultPropertyValues', 'struct')  # Skip


# --- TextAsset ---
@register_schema
class TextAssetSchema(TypeSchema):
    def __init__(self):
        super().__init__(49, "TextAsset")
        self.add_field('m_Name', SCHEMA_STRING)
        self.add_field('m_Script', SCHEMA_BYTES)


# --- AudioClip ---
@register_schema
class AudioClipSchema(TypeSchema):
    def __init__(self):
        super().__init__(83, "AudioClip")
        self.add_field('m_Name', SCHEMA_STRING)
        self.add_field('m_LoadType', SCHEMA_INT)
        self.add_field('m_Channels', SCHEMA_INT)
        self.add_field('m_Frequency', SCHEMA_INT)
        self.add_field('m_BitsPerSample', SCHEMA_INT)
        self.add_field('m_Length', SCHEMA_FLOAT)
        self.add_field('m_IsTrackerFormat', SCHEMA_BOOL)
        self.add_field('m_SubsoundIndex', SCHEMA_INT)
        self.add_field('m_PreloadAudioData', SCHEMA_BOOL)
        self.add_field('m_LoadInBackground', SCHEMA_BOOL)
        self.add_field('m_Legacy3D', SCHEMA_BOOL)
        self.add_field('m_Resource', SCHEMA_PPTR)
        self.add_field('m_CompressionFormat', SCHEMA_INT, version_min=22)
        self.add_field('m_NonStreamableData', SCHEMA_BYTES)
        self.add_field('m_StreamData', 'struct')  # Skip


# --- AudioSource ---
@register_schema
class AudioSourceSchema(TypeSchema):
    def __init__(self):
        super().__init__(82, "AudioSource")
        self.add_field('m_GameObject', SCHEMA_PPTR)
        self.add_field('m_Enabled', SCHEMA_BOOL)
        self.add_field('m_PlayOnAwake', SCHEMA_BOOL)
        self.add_field('m_Volume', SCHEMA_FLOAT)
        self.add_field('m_Pitch', SCHEMA_FLOAT)
        self.add_field('m_TimeStretchAmount', SCHEMA_FLOAT, version_min=25)
        self.add_field('m_Clip', SCHEMA_PPTR)
        self.add_field('m_OutputAudioMixerGroup', SCHEMA_PPTR)


# --- MonoBehaviour ---
@register_schema
class MonoBehaviourSchema(TypeSchema):
    def __init__(self):
        super().__init__(114, "MonoBehaviour")
        self.add_field('m_GameObject', SCHEMA_PPTR)
        self.add_field('m_Enabled', SCHEMA_BOOL)
        self.add_field('m_Script', SCHEMA_PPTR)
        self.add_field('m_Name', SCHEMA_STRING)
        # Script-specific data follows


# --- MonoScript ---
@register_schema
class MonoScriptSchema(TypeSchema):
    def __init__(self):
        super().__init__(115, "MonoScript")
        self.add_field('m_Name', SCHEMA_STRING)
        self.add_field('m_ClassName', SCHEMA_STRING)
        self.add_field('m_Namespace', SCHEMA_STRING)
        self.add_field('m_AssemblyName', SCHEMA_STRING)
        self.add_field('m_IsEditorScript', SCHEMA_BOOL)
        self.add_field('m_ExecutionOrder', SCHEMA_INT)


# --- Font ---
@register_schema
class FontSchema(TypeSchema):
    def __init__(self):
        super().__init__(128, "Font")
        self.add_field('m_Name', SCHEMA_STRING)
        self.add_field('m_FontData', SCHEMA_BYTES)
        self.add_field('m_Texture', SCHEMA_PPTR)


# --- Animator ---
@register_schema
class AnimatorSchema(TypeSchema):
    def __init__(self):
        super().__init__(95, "Animator")
        self.add_field('m_GameObject', SCHEMA_PPTR)
        self.add_field('m_Enabled', SCHEMA_BOOL)
        self.add_field('m_Avatar', SCHEMA_PPTR)
        self.add_field('m_Controller', SCHEMA_PPTR)
        self.add_field('m_CullingMode', SCHEMA_INT)
        self.add_field('m_UpdateMode', SCHEMA_INT)
        self.add_field('m_ApplyRootMotion', SCHEMA_BOOL)
        self.add_field('m_LinearVelocityBlending', SCHEMA_BOOL, version_min=25)


# --- AnimationClip ---
@register_schema
class AnimationClipSchema(TypeSchema):
    def __init__(self):
        super().__init__(74, "AnimationClip")
        self.add_field('m_Name', SCHEMA_STRING)
        self.add_field('m_EditorTime', SCHEMA_FLOAT)
        self.add_field('m_AnimationType', SCHEMA_INT)
        self.add_field('m_IsLooping', SCHEMA_BOOL)
        self.add_field('m_PlayAutomatically', SCHEMA_BOOL)
        self.add_field('m_WrapMode', SCHEMA_INT)
        self.add_field('m_Length', SCHEMA_FLOAT)
        self.add_field('m_FrameRate', SCHEMA_FLOAT)
        # Complex animation data follows


# --- Rigidbody ---
@register_schema
class RigidbodySchema(TypeSchema):
    def __init__(self):
        super().__init__(54, "Rigidbody")
        self.add_field('m_GameObject', SCHEMA_PPTR)
        self.add_field('m_Mass', SCHEMA_FLOAT)
        self.add_field('m_Drag', SCHEMA_FLOAT)
        self.add_field('m_AngularDrag', SCHEMA_FLOAT)
        self.add_field('m_UseGravity', SCHEMA_BOOL)
        self.add_field('m_IsKinematic', SCHEMA_BOOL)
        self.add_field('m_Interpolate', SCHEMA_INT)
        self.add_field('m_Constraints', SCHEMA_INT)
        self.add_field('m_CollisionDetection', SCHEMA_INT)


# --- Light ---
@register_schema
class LightSchema(TypeSchema):
    def __init__(self):
        super().__init__(108, "Light")
        self.add_field('m_GameObject', SCHEMA_PPTR)
        self.add_field('m_Enabled', SCHEMA_BOOL)
        self.add_field('m_Type', SCHEMA_INT)
        self.add_field('m_Color', SCHEMA_COLOR)
        self.add_field('m_Intensity', SCHEMA_FLOAT)
        self.add_field('m_Range', SCHEMA_FLOAT)
        self.add_field('m_SpotAngle', SCHEMA_FLOAT)
        self.add_field('m_CookieSize', SCHEMA_FLOAT)
        self.add_field('m_Cookie', SCHEMA_PPTR)


# --- Canvas ---
@register_schema
class CanvasSchema(TypeSchema):
    def __init__(self):
        super().__init__(223, "Canvas", version_min=20)
        self.add_field('m_GameObject', SCHEMA_PPTR)
        self.add_field('m_Enabled', SCHEMA_BOOL)
        self.add_field('m_RenderMode', SCHEMA_INT)
        self.add_field('m_Camera', SCHEMA_PPTR)
        self.add_field('m_PlaneDistance', SCHEMA_FLOAT)


# --- CanvasRenderer ---
@register_schema
class CanvasRendererSchema(TypeSchema):
    def __init__(self):
        super().__init__(222, "CanvasRenderer", version_min=20)
        self.add_field('m_GameObject', SCHEMA_PPTR)
        self.add_field('m_Enabled', SCHEMA_BOOL)
        self.add_field('m_Cull', SCHEMA_BOOL)
        self.add_field('m_StaticBatchInfo', 'struct')  # Skip
        self.add_field('m_StaticBatchRoot', SCHEMA_PPTR)


# ============================================================
# Schema-based Object Parser
# ============================================================

class SchemaParser:
    """Parse serialized objects using hardcoded schemas."""
    
    @staticmethod
    def get_schema(class_id: int, version: int) -> Optional[TypeSchema]:
        """Get the best matching schema for a class ID and version."""
        schema = SCHEMAS.get(class_id)
        if schema is None:
            return None
        if not schema.is_applicable(version):
            return None
        return schema
    
    @staticmethod
    def parse_object(data: bytes, class_id: int, version: int, endian: str = '<') -> Dict[str, Any]:
        """Parse an object using its schema."""
        schema = SchemaParser.get_schema(class_id, version)
        if schema is None:
            return {'_raw_data': data}
        
        reader = Reader(data, endian)
        result = {}
        
        for field in schema.fields:
            if not field.is_applicable(version):
                continue
            
            try:
                value = SchemaParser._read_field(reader, field, version)
                result[field.name] = value
            except Exception as e:
                result[f'{field.name}_error'] = str(e)
        
        # Add remaining data
        if reader.remaining() > 0:
            result['_remaining'] = reader.read_bytes(reader.remaining())
        
        return result
    
    @staticmethod
    def _read_field(reader: Reader, field: SchemaField, version: int) -> Any:
        """Read a single field based on its type."""
        if field.type == SCHEMA_INT:
            return reader.read_i32()
        elif field.type == SCHEMA_UINT:
            return reader.read_u32()
        elif field.type == SCHEMA_BOOL:
            return reader.read_bool()
        elif field.type == SCHEMA_FLOAT:
            return reader.read_float()
        elif field.type == SCHEMA_STRING:
            if version >= 21:
                return reader.read_al4string()
            else:
                return reader.read_cstring()
        elif field.type == SCHEMA_PPTR:
            file_id = reader.read_i32()
            if version >= 14:
                path_id = reader.read_u64()
            else:
                path_id = reader.read_u32()
            return {'file_id': file_id, 'path_id': path_id}
        elif field.type == SCHEMA_VECTOR2:
            return {'x': reader.read_float(), 'y': reader.read_float()}
        elif field.type == SCHEMA_VECTOR3:
            return {'x': reader.read_float(), 'y': reader.read_float(), 'z': reader.read_float()}
        elif field.type == SCHEMA_VECTOR4:
            return {
                'x': reader.read_float(),
                'y': reader.read_float(),
                'z': reader.read_float(),
                'w': reader.read_float()
            }
        elif field.type == SCHEMA_QUATERNION:
            return {
                'x': reader.read_float(),
                'y': reader.read_float(),
                'z': reader.read_float(),
                'w': reader.read_float()
            }
        elif field.type == SCHEMA_COLOR:
            return {
                'r': reader.read_float(),
                'g': reader.read_float(),
                'b': reader.read_float(),
                'a': reader.read_float()
            }
        elif field.type == SCHEMA_RECT:
            return {
                'x': reader.read_float(),
                'y': reader.read_float(),
                'width': reader.read_float(),
                'height': reader.read_float()
            }
        elif field.type == SCHEMA_BYTES:
            size = reader.read_u32()
            return reader.read_bytes(size)
        elif field.type == SCHEMA_ARRAY:
            count = reader.read_u32()
            elements = []
            if field.element_type:
                for _ in range(count):
                    elem_schema = SchemaField('', field.element_type)
                    elements.append(SchemaParser._read_field(reader, elem_schema, version))
            return elements
        elif field.type == SCHEMA_SKIP:
            size = field.count if field.count else 4
            return reader.read_bytes(size)
        else:
            # Unknown type - skip 4 bytes
            return reader.read_bytes(4)
