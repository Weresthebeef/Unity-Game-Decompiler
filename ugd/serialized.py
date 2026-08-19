"""
SerializedFile parser for Unity .assets files.
Handles type trees, object data, and stripped files with hardcoded schemas.
"""
import struct
from typing import List, Dict, Optional, Any, Tuple
from .utils import Reader, fnv1a_32


# ============================================================
# Class ID Constants (from Unity ClassIDReference)
# ============================================================

CLASS_IDS = {
    0: "Object",
    1: "GameObject",
    2: "Component",
    3: "LevelGameManager",
    4: "Transform",
    5: "TimeManager",
    6: "GlobalGameManager",
    8: "Behaviour",
    9: "GameManager",
    11: "AudioManager",
    13: "InputManager",
    18: "EditorExtension",
    19: "Physics2DSettings",
    20: "Camera",
    21: "Material",
    23: "MeshRenderer",
    25: "Renderer",
    27: "Texture",
    28: "Texture2D",
    29: "OcclusionCullingSettings",
    30: "GraphicsSettings",
    33: "MeshFilter",
    41: "OcclusionPortal",
    43: "Mesh",
    45: "Skybox",
    47: "QualitySettings",
    48: "Shader",
    49: "TextAsset",
    50: "Rigidbody2D",
    53: "Collider2D",
    54: "Rigidbody",
    55: "PhysicsManager",
    56: "Collider",
    57: "Joint",
    58: "CircleCollider2D",
    59: "HingeJoint",
    60: "PolygonCollider2D",
    61: "BoxCollider2D",
    62: "PhysicsMaterial2D",
    64: "MeshCollider",
    65: "BoxCollider",
    66: "CompositeCollider2D",
    68: "EdgeCollider2D",
    70: "CapsuleCollider2D",
    72: "ComputeShader",
    74: "AnimationClip",
    75: "ConstantForce",
    78: "TagManager",
    81: "AudioListener",
    82: "AudioSource",
    83: "AudioClip",
    84: "RenderTexture",
    86: "CustomRenderTexture",
    89: "Cubemap",
    90: "Avatar",
    91: "AnimatorController",
    93: "RuntimeAnimatorController",
    94: "ShaderNameRegistry",
    95: "Animator",
    96: "TrailRenderer",
    98: "DelayedCallManager",
    102: "TextMesh",
    104: "RenderSettings",
    108: "Light",
    109: "ShaderInclude",
    110: "BaseAnimationTrack",
    111: "Animation",
    114: "MonoBehaviour",
    115: "MonoScript",
    116: "MonoManager",
    117: "Texture3D",
    118: "NewAnimationTrack",
    119: "Projector",
    120: "LineRenderer",
    121: "Flare",
    122: "Halo",
    123: "LensFlare",
    124: "FlareLayer",
    126: "NavMeshProjectSettings",
    128: "Font",
    129: "PlayerSettings",
    130: "NamedObject",
    134: "PhysicMaterial",
    135: "SphereCollider",
    136: "CapsuleCollider",
    137: "SkinnedMeshRenderer",
    138: "FixedJoint",
    141: "BuildSettings",
    142: "AssetBundle",
    143: "CharacterController",
    144: "CharacterJoint",
    145: "SpringJoint",
    146: "WheelCollider",
    147: "ResourceManager",
    150: "PreloadData",
    152: "MovieTexture",
    153: "ConfigurableJoint",
    154: "TerrainCollider",
    156: "TerrainData",
    157: "LightmapSettings",
    158: "WebCamTexture",
    159: "EditorSettings",
    162: "EditorUserSettings",
    164: "AudioReverbFilter",
    165: "AudioHighPassFilter",
    166: "AudioChorusFilter",
    167: "AudioReverbZone",
    168: "AudioEchoFilter",
    169: "AudioLowPassFilter",
    170: "AudioDistortionFilter",
    171: "SparseTexture",
    180: "AudioBehaviour",
    181: "AudioFilter",
    182: "WindZone",
    183: "Cloth",
    184: "SubstanceArchive",
    185: "ProceduralMaterial",
    186: "ProceduralTexture",
    187: "Texture2DArray",
    188: "CubemapArray",
    191: "OffMeshLink",
    192: "OcclusionArea",
    193: "Tree",
    195: "NavMeshAgent",
    196: "NavMeshSettings",
    198: "ParticleSystem",
    199: "ParticleSystemRenderer",
    200: "ShaderVariantCollection",
    205: "LODGroup",
    206: "BlendTree",
    207: "Motion",
    208: "NavMeshObstacle",
    210: "SortingGroup",
    212: "SpriteRenderer",
    213: "Sprite",
    214: "CachedSpriteAtlas",
    215: "ReflectionProbe",
    218: "Terrain",
    220: "LightProbeGroup",
    221: "AnimatorOverrideController",
    222: "CanvasRenderer",
    223: "Canvas",
    224: "RectTransform",
    225: "CanvasGroup",
    226: "BillboardAsset",
    227: "BillboardRenderer",
    228: "SpeedTreeWindAsset",
    229: "AnchoredJoint2D",
    230: "Joint2D",
    231: "SpringJoint2D",
    232: "DistanceJoint2D",
    233: "HingeJoint2D",
    234: "SliderJoint2D",
    235: "WheelJoint2D",
    236: "ClusterInputManager",
    237: "BaseVideoTexture",
    238: "NavMeshData",
    240: "AudioMixer",
    241: "AudioMixerController",
    243: "AudioMixerGroupController",
    244: "AudioMixerEffectController",
    245: "AudioMixerSnapshotController",
    246: "PhysicsUpdateBehaviour2D",
    247: "ConstantForce2D",
    248: "Effector2D",
    249: "AreaEffector2D",
    250: "PointEffector2D",
    251: "PlatformEffector2D",
    252: "SurfaceEffector2D",
    253: "BuoyancyEffector2D",
    254: "RelativeJoint2D",
    255: "FixedJoint2D",
    256: "FrictionJoint2D",
    257: "TargetJoint2D",
    258: "LightProbes",
    259: "LightProbeProxyVolume",
    271: "SampleClip",
    272: "AudioMixerSnapshot",
    273: "AudioMixerGroup",
    290: "AssetBundleManifest",
    300: "RuntimeInitializeOnLoadManager",
    310: "UnityConnectSettings",
    319: "AvatarMask",
    320: "PlayableDirector",
    328: "VideoPlayer",
    329: "VideoClip",
    330: "ParticleSystemForceField",
    331: "SpriteMask",
    363: "OcclusionCullingData",
    1001: "PrefabInstance",
    1002: "EditorExtensionImpl",
    1003: "AssetImporter",
    # Primitive types (100000+)
    100000: "int",
    100001: "bool",
    100002: "float",
    100003: "MonoObject",
    100004: "Collision",
    100005: "Vector3f",
    100006: "RootMotionData",
    100007: "Collision2D",
    100008: "AudioMixerLiveUpdateFloat",
    100009: "AudioMixerLiveUpdateBool",
    100010: "Polygon2D",
    100011: "void",
}


# Texture format IDs (from Unity TextureFormat enum)
TEXTURE_FORMATS = {
    0: "Alpha8",
    1: "ARGB4444",
    2: "RGB24",
    3: "RGBA32",
    4: "ARGB32",
    5: "RGB565",
    7: "R16",
    8: "DXT1",
    9: "DXT5",
    10: "RGBA4444",
    11: "BGRA32",
    12: "RHalf",
    13: "RGHalf",
    14: "RGBAHalf",
    15: "RFloat",
    16: "RGFloat",
    17: "RGBAFloat",
    18: "YUY2",
    19: "RGB9e5Float",
    20: "BC4",
    21: "BC5",
    22: "BC6H",
    23: "BC7",
    24: "DXT1Crunched",
    25: "DXT5Crunched",
    26: "ETC_RGB4",
    27: "ETC2_RGB",
    28: "ETC2_RGBA1",
    29: "ETC2_RGBA8",
    30: "EAC_R",
    31: "EAC_RG",
    32: "ETC_RGB4_3DS",
    33: "ETC_RGBA8_3DS",
    34: "RG16",
    35: "R8",
    36: "ETC_RGB4Crunched",
    37: "ETC2_RGBA8Crunched",
    41: "ASTC_4x4",
    42: "ASTC_5x5",
    43: "ASTC_6x6",
    44: "ASTC_8x8",
    45: "ASTC_10x10",
    46: "ASTC_12x12",
    47: "ASTC_HDR_4x4",
    48: "ASTC_HDR_5x5",
    49: "ASTC_HDR_6x6",
    50: "ASTC_HDR_8x8",
    51: "ASTC_HDR_10x10",
    52: "ASTC_HDR_12x12",
    62: "RG32",
    63: "RGB48",
    64: "RGBA64",
}


# ============================================================
# Type Tree Node
# ============================================================

class TypeTreeNode:
    """Represents a node in the Unity type tree."""
    __slots__ = ('version', 'base_class_id', 'class_id', 'type_name', 'var_name',
                 'byte_size', 'index', 'meta_flag', 'children', 'level', 'is_array')
    
    def __init__(self):
        self.version = 0
        self.base_class_id = 0
        self.class_id = 0
        self.type_name = ""
        self.var_name = ""
        self.byte_size = 0
        self.index = 0
        self.meta_flag = 0
        self.children: List['TypeTreeNode'] = []
        self.level = 0
        self.is_array = False
    
    def __repr__(self):
        return f"TypeTreeNode({self.type_name}, {self.var_name}, children={len(self.children)})"


# ============================================================
# SerializedFile Parser
# ============================================================

class SerializedType:
    """Represents a type definition in the serialized file."""
    __slots__ = ('class_id', 'type_name', 'script_type_index', 'nodes',
                 'script_hash', 'type_hash', 'type_dependencies')
    
    def __init__(self):
        self.class_id = 0
        self.type_name = ""
        self.script_type_index = -1
        self.nodes: List[TypeTreeNode] = []
        self.script_hash: Optional[bytes] = None
        self.type_hash: Optional[bytes] = None
        self.type_dependencies: List[int] = []


class ObjectInfo:
    """Represents an object in the serialized file."""
    __slots__ = ('path_id', 'byte_size', 'class_id', 'data_offset', 'data', 'type_info')
    
    def __init__(self):
        self.path_id = 0
        self.byte_size = 0
        self.class_id = 0
        self.data_offset = 0
        self.data: Optional[bytes] = None
        self.type_info: Optional[SerializedType] = None


class ExternalReference:
    """Represents an external reference."""
    __slots__ = ('asset_path', 'guid', 'type', 'file_name')
    
    def __init__(self):
        self.asset_path = ""
        self.guid: bytes = b''
        self.type = 0
        self.file_name = ""


class SerializedFile:
    """Parser for Unity .assets serialized files."""
    __slots__ = (
        'version', 'endian', 'enable_type_tree', 'metadata_size', 'file_size',
        'data_offset', 'types', 'objects', 'externals', 'preloads',
        'script_type_mapping', 'data', '_reader', '_object_data_cache'
    )
    
    def __init__(self):
        self.version = 0
        self.endian = '<'  # little-endian by default
        self.enable_type_tree = False
        self.metadata_size = 0
        self.file_size = 0
        self.data_offset = 0
        self.types: List[SerializedType] = []
        self.objects: List[ObjectInfo] = []
        self.externals: List[ExternalReference] = []
        self.preloads: List[Tuple[int, int]] = []
        self.script_type_mapping: Dict[int, int] = {}
        self.data: bytes = b''
        self._reader: Optional[Reader] = None
        self._object_data_cache: Dict[int, bytes] = {}
    
    def parse(self, data: bytes) -> bool:
        """Parse serialized file data."""
        self.data = data
        self._reader = Reader(data)
        
        try:
            self.metadata_size = self._reader.read_u32()
            self.file_size = self._reader.read_u32()
            self.version = self._reader.read_u32()
            self.data_offset = self._reader.read_u32()
            
            endian_byte = self._reader.read_u8()
            # 0 = little endian, 1 = big endian
            self.endian = '<' if endian_byte == 0 else '>'
            
            # Re-read with correct endianness
            self._reader = Reader(data, self.endian)
            self._reader.pos = 0
            self.metadata_size = self._reader.read_u32()
            self.file_size = self._reader.read_u32()
            self.version = self._reader.read_u32()
            self.data_offset = self._reader.read_u32()
            self._reader.read_u8()  # endian byte already read
            
            # Version >= 22 has additional bytes
            if self.version >= 22:
                unknown = self._reader.read_u8()
                self.enable_type_tree = self._reader.read_u8() != 0
            else:
                self.enable_type_tree = True  # Type tree present in older versions
            
            # Parse type tree if enabled
            if self.enable_type_tree:
                self._parse_type_tree()
            
            # Parse object infos
            self._parse_objects()
            
            # Parse script type mapping (for old versions)
            if self.version < 11:
                self._parse_script_type_mapping()
            
            # Parse external references
            self._parse_externals()
            
            # Parse preloads
            self._parse_preloads()
            
            return True
            
        except Exception as e:
            print(f"Error parsing serialized file: {e}")
            return False
    
    def _parse_type_tree(self):
        """Parse the type tree section."""
        type_count = self._reader.read_u32()
        
        for _ in range(type_count):
            type_info = SerializedType()
            type_info.class_id = self._reader.read_i32()
            
            # Type name: al4string in newer versions, cstring in older
            if self.version >= 21:
                type_info.type_name = self._reader.read_al4string()
            else:
                type_info.type_name = self._reader.read_cstring()
            
            # 16-byte hash
            type_info.type_hash = self._reader.read_bytes(16)
            
            # Parse type tree nodes
            type_info.nodes = self._parse_type_tree_nodes()
            
            # For version >= 19: script_type_index
            if self.version >= 19:
                type_info.script_type_index = self._reader.read_i32()
            
            # For MonoBehaviour (class_id == 114): script_hash and type_hash
            if type_info.class_id == 114:
                if self.version >= 19:
                    type_info.script_hash = self._reader.read_bytes(16)
                if self.version >= 20:
                    type_info.type_hash = self._reader.read_bytes(16)
            
            # Type dependencies (version >= 20)
            if self.version >= 20:
                dep_count = self._reader.read_u32()
                type_info.type_dependencies = [self._reader.read_i32() for _ in range(dep_count)]
            
            self.types.append(type_info)
    
    def _parse_type_tree_nodes(self) -> List[TypeTreeNode]:
        """Parse type tree nodes for a single type."""
        nodes: List[TypeTreeNode] = []
        
        # Read node count
        node_count = self._reader.read_u32()
        
        for _ in range(node_count):
            node = TypeTreeNode()
            
            if self.version >= 21:
                # New format: version u16, base_class_id u8, class_id u8
                node.version = self._reader.read_u16()
                node.base_class_id = self._reader.read_u8()
                node.class_id = self._reader.read_u8()
            else:
                # Old format: version u16, depth u8, is_array u8
                node.version = self._reader.read_u16()
                node.level = self._reader.read_u8()
                node.is_array = self._reader.read_u8() != 0
            
            node.type_name = self._reader.read_al4string() if self.version >= 21 else self._reader.read_cstring()
            node.var_name = self._reader.read_al4string() if self.version >= 21 else self._reader.read_cstring()
            node.byte_size = self._reader.read_i32()
            node.index = self._reader.read_i32()
            node.meta_flag = self._reader.read_i32()
            
            # Check if this is an array node
            if node.meta_flag & 0x4000:
                node.is_array = True
            
            nodes.append(node)
        
        # Build tree structure
        self._build_type_tree(nodes)
        
        return nodes
    
    def _build_type_tree(self, nodes: List[TypeTreeNode]):
        """Build parent-child relationships in the type tree."""
        # Sort nodes by index (they should be in preorder)
        nodes.sort(key=lambda n: n.index)
        
        # Build tree: children of node i are nodes[i+1:j] where j is the next sibling
        stack = []
        for i, node in enumerate(nodes):
            # Pop until we find parent
            while stack and stack[-1].index + len(stack[-1].children) + 1 <= node.index:
                stack.pop()
            
            if stack:
                parent = stack[-1]
                parent.children.append(node)
                node.level = parent.level + 1
            
            stack.append(node)
    
    def _parse_objects(self):
        """Parse object infos."""
        object_count = self._reader.read_u32()
        
        for _ in range(object_count):
            obj = ObjectInfo()
            
            # Path ID: u64 for version >= 14, u32 for older
            if self.version >= 14:
                obj.path_id = self._reader.read_u64()
            else:
                obj.path_id = self._reader.read_u32()
            
            obj.byte_size = self._reader.read_u32()
            obj.class_id = self._reader.read_i32()
            obj.data_offset = self._reader.read_u32()
            
            # Find type info for this class
            for t in self.types:
                if t.class_id == obj.class_id:
                    obj.type_info = t
                    break
            
            self.objects.append(obj)
    
    def _parse_script_type_mapping(self):
        """Parse script type mapping (for old versions)."""
        count = self._reader.read_u32()
        for _ in range(count):
            script_id = self._reader.read_u16()
            type_id = self._reader.read_u32()
            self.script_type_mapping[script_id] = type_id
    
    def _parse_externals(self):
        """Parse external references."""
        count = self._reader.read_u32()
        for _ in range(count):
            ext = ExternalReference()
            
            if self.version >= 21:
                ext.asset_path = self._reader.read_al4string()
            else:
                ext.asset_path = self._reader.read_cstring()
            
            ext.guid = self._reader.read_bytes(16)
            ext.type = self._reader.read_u32()
            
            if self.version >= 6:
                ext.file_name = self._reader.read_cstring()
            
            self.externals.append(ext)
    
    def _parse_preloads(self):
        """Parse preloads."""
        count = self._reader.read_u32()
        for _ in range(count):
            file_id = self._reader.read_i32()
            
            if self.version >= 14:
                path_id = self._reader.read_u64()
            else:
                path_id = self._reader.read_u32()
            
            self.preloads.append((file_id, path_id))
    
    def get_object_data(self, obj: ObjectInfo) -> bytes:
        """Get the raw data for an object."""
        if obj.data is not None:
            return obj.data
        
        if obj.data_offset == 0 and obj.byte_size == 0:
            return b''
        
        # Calculate actual offset in file
        actual_offset = self.data_offset + obj.data_offset
        
        if obj.byte_size > 0:
            obj.data = self.data[actual_offset:actual_offset + obj.byte_size]
        else:
            obj.data = b''
        
        return obj.data
    
    def get_object_by_path_id(self, path_id: int) -> Optional[ObjectInfo]:
        """Get an object by its path ID."""
        for obj in self.objects:
            if obj.path_id == path_id:
                return obj
        return None
    
    def get_class_name(self, class_id: int) -> str:
        """Get the class name for a given class ID."""
        return CLASS_IDS.get(class_id, f"Unknown_{class_id}")
    
    def get_type_by_class_id(self, class_id: int) -> Optional[SerializedType]:
        """Get type info by class ID."""
        for t in self.types:
            if t.class_id == class_id:
                return t
        return None
