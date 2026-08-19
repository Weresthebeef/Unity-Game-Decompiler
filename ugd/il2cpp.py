"""
IL2CPP global-metadata.dat parser.
Parses Unity IL2CPP metadata to extract type definitions, methods, fields, etc.
"""
import struct
from typing import Dict, List, Optional, Any, Tuple, BinaryIO
from .utils import Reader


# ============================================================
# IL2CPP Metadata Constants
# ============================================================

IL2CPP_MAGIC = 0xFAB11BAF

# Metadata versions
VERSION_24 = 24
VERSION_27 = 27
VERSION_29 = 29


# ============================================================
# Metadata Structures
# ============================================================

class Il2CppGlobalMetadataHeader:
    """Global metadata header structure."""
    __slots__ = (
        'sanity', 'version', 'string_literal_offset', 'string_literal_size',
        'string_literal_data_offset', 'string_literal_data_size',
        'string_offset', 'string_size',
        'events_offset', 'events_size',
        'properties_offset', 'properties_size',
        'methods_offset', 'methods_size',
        'parameter_default_values_offset', 'parameter_default_values_size',
        'field_default_values_offset', 'field_default_values_size',
        'field_and_parameter_default_value_data_offset', 'field_and_parameter_default_value_data_size',
        'field_marshaled_sizes_offset', 'field_marshaled_sizes_size',
        'parameters_offset', 'parameters_size',
        'fields_offset', 'fields_size',
        'generic_parameters_offset', 'generic_parameters_size',
        'generic_parameter_constraints_offset', 'generic_parameter_constraints_size',
        'generic_containers_offset', 'generic_containers_size',
        'nested_types_offset', 'nested_types_size',
        'interfaces_offset', 'interfaces_size',
        'vtable_methods_offset', 'vtable_methods_size',
        'interface_offsets_offset', 'interface_offsets_size',
        'type_definitions_offset', 'type_definitions_size',
        'rgctx_entries_offset', 'rgctx_entries_count',
        'images_offset', 'images_size',
        'assemblies_offset', 'assemblies_size',
        # Version-specific fields
        'metadata_usage_lists_offset', 'metadata_usage_lists_count',
        'metadata_usage_pairs_offset', 'metadata_usage_pairs_count',
        'field_refs_offset', 'field_refs_size',
        'type_definition_hashes_offset', 'type_definition_hashes_size',
        'field_definition_hashes_offset', 'field_definition_hashes_size',
        'method_definition_hashes_offset', 'method_definition_hashes_size',
        'parameter_definition_hashes_offset', 'parameter_definition_hashes_size',
        'generic_container_hashes_offset', 'generic_container_hashes_size',
        'generic_parameter_hashes_offset', 'generic_parameter_hashes_size',
        'generic_parameter_constraint_hashes_offset', 'generic_parameter_constraint_hashes_size',
        'nested_type_hashes_offset', 'nested_type_hashes_size',
        'interface_impl_hashes_offset', 'interface_impl_hashes_size',
        'attribute_type_ranges_offset', 'attribute_type_ranges_count',
        'attribute_types_offset', 'attribute_types_count',
        'attribute_data_ranges_offset', 'attribute_data_ranges_size',
        'attribute_data_offset', 'attribute_data_size',
    )
    
    def __init__(self):
        self.sanity = 0
        self.version = 0
        # Initialize all offsets to 0
        for attr in self.__slots__:
            if attr != 'sanity' and attr != 'version':
                setattr(self, attr, 0)


class Il2CppStringLiteral:
    """String literal entry."""
    __slots__ = ('length', 'data_index')
    
    def __init__(self):
        self.length = 0
        self.data_index = 0


class Il2CppTypeDefinition:
    """Type definition."""
    __slots__ = (
        'name_index', 'namespace_index', 'byval_type_index', 'declaring_type_index',
        'element_type_index', 'generic_container_index', 'pack_size',
        'method_start', 'method_count', 'field_start', 'field_count',
        'property_start', 'property_count', 'event_start', 'event_count',
        'nested_type_start', 'nested_type_count', 'interfaces_start', 'interface_count',
        'vtable_start', 'vtable_count', 'interfaces_index', 'interfaces_count',
        'bitfield', 'token',
        # Additional fields for newer versions
        'type_hash', 'script_type_index',
    )
    
    def __init__(self):
        self.name_index = 0
        self.namespace_index = 0
        self.byval_type_index = -1
        self.declaring_type_index = -1
        self.element_type_index = -1
        self.generic_container_index = -1
        self.pack_size = 0
        self.method_start = 0
        self.method_count = 0
        self.field_start = 0
        self.field_count = 0
        self.property_start = 0
        self.property_count = 0
        self.event_start = 0
        self.event_count = 0
        self.nested_type_start = 0
        self.nested_type_count = 0
        self.interfaces_start = 0
        self.interface_count = 0
        self.vtable_start = 0
        self.vtable_count = 0
        self.interfaces_index = 0
        self.interfaces_count = 0
        self.bitfield = 0
        self.token = 0
        self.type_hash = 0
        self.script_type_index = -1


class Il2CppMethodDefinition:
    """Method definition."""
    __slots__ = (
        'name_index', 'declaring_type', 'return_type',
        'parameter_start', 'parameter_count', 'generic_container_index',
        'token', 'flags', 'iflags', 'slot', 'parameter_end',
    )
    
    def __init__(self):
        self.name_index = 0
        self.declaring_type = 0
        self.return_type = -1
        self.parameter_start = 0
        self.parameter_count = 0
        self.generic_container_index = -1
        self.token = 0
        self.flags = 0
        self.iflags = 0
        self.slot = 0
        self.parameter_end = 0


class Il2CppFieldDefinition:
    """Field definition."""
    __slots__ = ('name_index', 'type_index', 'token')
    
    def __init__(self):
        self.name_index = 0
        self.type_index = -1
        self.token = 0


class Il2CppParameterDefinition:
    """Parameter definition."""
    __slots__ = ('name_index', 'token', 'type_index')
    
    def __init__(self):
        self.name_index = 0
        self.token = 0
        self.type_index = -1


class Il2CppImageDefinition:
    """Image (module) definition."""
    __slots__ = (
        'name_index', 'type_start', 'type_count',
        'export_type_start', 'export_type_count',
        'entry_point_index', 'token',
        'custom_attribute_start', 'custom_attribute_count',
    )
    
    def __init__(self):
        self.name_index = 0
        self.type_start = 0
        self.type_count = 0
        self.export_type_start = 0
        self.export_type_count = 0
        self.entry_point_index = 0
        self.token = 0
        self.custom_attribute_start = 0
        self.custom_attribute_count = 0


# ============================================================
# Metadata Parser
# ============================================================

class Il2CppMetadataParser:
    """Parser for IL2CPP global-metadata.dat files."""
    
    def __init__(self):
        self.version = 0
        self.header: Optional[Il2CppGlobalMetadataHeader] = None
        self.string_literals: List[Il2CppStringLiteral] = []
        self.string_data: bytes = b''
        self.type_definitions: List[Il2CppTypeDefinition] = []
        self.method_definitions: List[Il2CppMethodDefinition] = []
        self.field_definitions: List[Il2CppFieldDefinition] = []
        self.parameter_definitions: List[Il2CppParameterDefinition] = []
        self.image_definitions: List[Il2CppImageDefinition] = []
        self.generic_containers: List[Dict[str, Any]] = []
        self.generic_parameters: List[Dict[str, Any]] = []
        self.nested_types: List[int] = []
        self.interfaces: List[int] = []
        self.vtable_methods: List[int] = []
        self.type_hashes: Dict[int, bytes] = {}
        self.field_hashes: Dict[int, bytes] = {}
        self.method_hashes: Dict[int, bytes] = {}
        self.string_cache: Dict[int, str] = {}
    
    def parse(self, data: bytes) -> bool:
        """Parse metadata from bytes."""
        reader = Reader(data, '<')
        
        # Read magic
        magic = reader.read_u32()
        if magic != IL2CPP_MAGIC:
            print(f"Invalid IL2CPP metadata: bad magic {hex(magic)}")
            return False
        
        # Read version
        self.version = reader.read_i32()
        print(f"IL2CPP metadata version: {self.version}")
        
        # Parse header based on version
        if self.version == VERSION_24:
            self._parse_v24(reader)
        elif self.version >= VERSION_27 and self.version < VERSION_29:
            self._parse_v27(reader)
        elif self.version >= VERSION_29:
            self._parse_v29(reader)
        else:
            print(f"Unsupported IL2CPP metadata version: {self.version}")
            return False
        
        return True
    
    def _parse_v24(self, reader: Reader) -> None:
        """Parse version 24 metadata."""
        self.header = Il2CppGlobalMetadataHeader()
        self.header.sanity = IL2CPP_MAGIC
        self.header.version = self.version
        
        # Read header fields
        self.header.string_literal_offset = reader.read_u32()
        self.header.string_literal_size = reader.read_i32()
        self.header.string_literal_data_offset = reader.read_u32()
        self.header.string_literal_data_size = reader.read_i32()
        self.header.string_offset = reader.read_u32()
        self.header.string_size = reader.read_i32()
        self.header.events_offset = reader.read_u32()
        self.header.events_size = reader.read_i32()
        self.header.properties_offset = reader.read_u32()
        self.header.properties_size = reader.read_i32()
        self.header.methods_offset = reader.read_u32()
        self.header.methods_size = reader.read_i32()
        self.header.parameter_default_values_offset = reader.read_u32()
        self.header.parameter_default_values_size = reader.read_i32()
        self.header.field_default_values_offset = reader.read_u32()
        self.header.field_default_values_size = reader.read_i32()
        self.header.field_and_parameter_default_value_data_offset = reader.read_u32()
        self.header.field_and_parameter_default_value_data_size = reader.read_i32()
        self.header.field_marshaled_sizes_offset = reader.read_u32()
        self.header.field_marshaled_sizes_size = reader.read_i32()
        self.header.parameters_offset = reader.read_u32()
        self.header.parameters_size = reader.read_i32()
        self.header.fields_offset = reader.read_u32()
        self.header.fields_size = reader.read_i32()
        self.header.generic_parameters_offset = reader.read_u32()
        self.header.generic_parameters_size = reader.read_i32()
        self.header.generic_parameter_constraints_offset = reader.read_u32()
        self.header.generic_parameter_constraints_size = reader.read_i32()
        self.header.generic_containers_offset = reader.read_u32()
        self.header.generic_containers_size = reader.read_i32()
        self.header.nested_types_offset = reader.read_u32()
        self.header.nested_types_size = reader.read_i32()
        self.header.interfaces_offset = reader.read_u32()
        self.header.interfaces_size = reader.read_i32()
        self.header.vtable_methods_offset = reader.read_u32()
        self.header.vtable_methods_size = reader.read_i32()
        self.header.interface_offsets_offset = reader.read_u32()
        self.header.interface_offsets_size = reader.read_i32()
        self.header.type_definitions_offset = reader.read_u32()
        self.header.type_definitions_size = reader.read_i32()
        self.header.rgctx_entries_offset = reader.read_u32()
        self.header.rgctx_entries_count = reader.read_i32()
        self.header.images_offset = reader.read_u32()
        self.header.images_size = reader.read_i32()
        self.header.assemblies_offset = reader.read_u32()
        self.header.assemblies_size = reader.read_i32()
        self.header.metadata_usage_lists_offset = reader.read_u32()
        self.header.metadata_usage_lists_count = reader.read_i32()
        self.header.metadata_usage_pairs_offset = reader.read_u32()
        self.header.metadata_usage_pairs_count = reader.read_i32()
        
        # Parse sections
        self._parse_string_literals()
        self._parse_type_definitions()
        self._parse_method_definitions()
        self._parse_field_definitions()
        self._parse_parameter_definitions()
        self._parse_images()
    
    def _parse_v27(self, reader: Reader) -> None:
        """Parse version 27+ metadata."""
        self._parse_v24(reader)
        
        # Version 27+ has additional hash sections
        self.header.type_definition_hashes_offset = reader.read_u32()
        self.header.type_definition_hashes_size = reader.read_i32()
        self.header.field_definition_hashes_offset = reader.read_u32()
        self.header.field_definition_hashes_size = reader.read_i32()
        self.header.method_definition_hashes_offset = reader.read_u32()
        self.header.method_definition_hashes_size = reader.read_i32()
        self.header.parameter_definition_hashes_offset = reader.read_u32()
        self.header.parameter_definition_hashes_size = reader.read_i32()
        self.header.generic_container_hashes_offset = reader.read_u32()
        self.header.generic_container_hashes_size = reader.read_i32()
        self.header.generic_parameter_hashes_offset = reader.read_u32()
        self.header.generic_parameter_hashes_size = reader.read_i32()
        self.header.generic_parameter_constraint_hashes_offset = reader.read_u32()
        self.header.generic_parameter_constraint_hashes_size = reader.read_i32()
        self.header.nested_type_hashes_offset = reader.read_u32()
        self.header.nested_type_hashes_size = reader.read_i32()
        self.header.interface_impl_hashes_offset = reader.read_u32()
        self.header.interface_impl_hashes_size = reader.read_i32()
        
        # Parse hash sections
        self._parse_type_hashes()
        self._parse_field_hashes()
        self._parse_method_hashes()
    
    def _parse_v29(self, reader: Reader) -> None:
        """Parse version 29+ metadata."""
        self._parse_v27(reader)
        
        # Version 29+ has attribute data sections
        self.header.attribute_data_ranges_offset = reader.read_u32()
        self.header.attribute_data_ranges_size = reader.read_i32()
        self.header.attribute_data_offset = reader.read_u32()
        self.header.attribute_data_size = reader.read_i32()
    
    def _parse_string_literals(self) -> None:
        """Parse string literals section."""
        if not self.header or self.header.string_literal_offset == 0:
            return
        
        reader = Reader(self.data, '<', self.header.string_literal_offset)
        
        # Read string literal count from header
        count = self.header.string_literal_size // 8  # Each entry is 8 bytes (2 u32)
        
        self.string_literals = []
        for _ in range(count):
            lit = Il2CppStringLiteral()
            lit.length = reader.read_u32()
            lit.data_index = reader.read_i32()
            self.string_literals.append(lit)
    
    def _parse_type_definitions(self) -> None:
        """Parse type definitions section."""
        if not self.header or self.header.type_definitions_offset == 0:
            return
        
        reader = Reader(self.data, '<', self.header.type_definitions_offset)
        
        # Type definition size varies by version
        type_def_size = 0
        if self.version >= VERSION_27:
            type_def_size = 84  # With byval_type_index and declaring_type_index
        else:
            type_def_size = 72  # Without
        
        count = self.header.type_definitions_size // type_def_size
        
        self.type_definitions = []
        for _ in range(count):
            type_def = Il2CppTypeDefinition()
            
            if self.version >= VERSION_27:
                type_def.name_index = reader.read_u32()
                type_def.namespace_index = reader.read_u32()
                type_def.byval_type_index = reader.read_i32()
                type_def.declaring_type_index = reader.read_i32()
            else:
                type_def.name_index = reader.read_u32()
                type_def.namespace_index = reader.read_u32()
            
            type_def.element_type_index = reader.read_i32()
            type_def.generic_container_index = reader.read_i32()
            type_def.pack_size = reader.read_u32()
            type_def.method_start = reader.read_u32()
            type_def.method_count = reader.read_u32()
            type_def.field_start = reader.read_u32()
            type_def.field_count = reader.read_u32()
            type_def.property_start = reader.read_u32()
            type_def.property_count = reader.read_u32()
            type_def.event_start = reader.read_u32()
            type_def.event_count = reader.read_u32()
            type_def.nested_type_start = reader.read_u32()
            type_def.nested_type_count = reader.read_u32()
            type_def.interfaces_start = reader.read_u32()
            type_def.interface_count = reader.read_u32()
            type_def.vtable_start = reader.read_u32()
            type_def.vtable_count = reader.read_u32()
            type_def.interfaces_index = reader.read_u32()
            type_def.interfaces_count = reader.read_u32()
            type_def.bitfield = reader.read_u32()
            type_def.token = reader.read_u32()
            
            # Version 24+ has additional fields
            if self.version >= VERSION_24:
                type_def.type_hash = reader.read_u64()
            
            if self.version >= VERSION_27:
                type_def.script_type_index = reader.read_i32()
            
            self.type_definitions.append(type_def)
    
    def _parse_method_definitions(self) -> None:
        """Parse method definitions section."""
        if not self.header or self.header.methods_offset == 0:
            return
        
        reader = Reader(self.data, '<', self.header.methods_offset)
        
        # Method definition size
        method_def_size = 32  # Standard size
        
        count = self.header.methods_size // method_def_size
        
        self.method_definitions = []
        for _ in range(count):
            method = Il2CppMethodDefinition()
            method.name_index = reader.read_u32()
            method.declaring_type = reader.read_u32()
            method.return_type = reader.read_i32()
            method.parameter_start = reader.read_u32()
            method.parameter_count = reader.read_u32()
            method.generic_container_index = reader.read_i32()
            method.token = reader.read_u32()
            method.flags = reader.read_u16()
            method.iflags = reader.read_u16()
            method.slot = reader.read_u16()
            method.parameter_end = reader.read_u16()
            
            self.method_definitions.append(method)
    
    def _parse_field_definitions(self) -> None:
        """Parse field definitions section."""
        if not self.header or self.header.fields_offset == 0:
            return
        
        reader = Reader(self.data, '<', self.header.fields_offset)
        
        # Field definition size
        field_def_size = 12  # 3 u32
        
        count = self.header.fields_size // field_def_size
        
        self.field_definitions = []
        for _ in range(count):
            field = Il2CppFieldDefinition()
            field.name_index = reader.read_u32()
            field.type_index = reader.read_i32()
            field.token = reader.read_u32()
            
            self.field_definitions.append(field)
    
    def _parse_parameter_definitions(self) -> None:
        """Parse parameter definitions section."""
        if not self.header or self.header.parameters_offset == 0:
            return
        
        reader = Reader(self.data, '<', self.header.parameters_offset)
        
        # Parameter definition size
        param_def_size = 12  # 3 u32
        
        count = self.header.parameters_size // param_def_size
        
        self.parameter_definitions = []
        for _ in range(count):
            param = Il2CppParameterDefinition()
            param.name_index = reader.read_u32()
            param.token = reader.read_u32()
            param.type_index = reader.read_i32()
            
            self.parameter_definitions.append(param)
    
    def _parse_images(self) -> None:
        """Parse image definitions section."""
        if not self.header or self.header.images_offset == 0:
            return
        
        reader = Reader(self.data, '<', self.header.images_offset)
        
        # Image definition size varies by version
        image_def_size = 32  # Standard size
        
        count = self.header.images_size // image_def_size
        
        self.image_definitions = []
        for _ in range(count):
            image = Il2CppImageDefinition()
            image.name_index = reader.read_u32()
            image.type_start = reader.read_u32()
            image.type_count = reader.read_u32()
            image.export_type_start = reader.read_u32()
            image.export_type_count = reader.read_u32()
            image.entry_point_index = reader.read_u32()
            image.token = reader.read_u32()
            
            # Version 24.1+ has custom attribute fields
            if self.version >= 24:
                image.custom_attribute_start = reader.read_u32()
                image.custom_attribute_count = reader.read_u32()
            
            self.image_definitions.append(image)
    
    def _parse_type_hashes(self) -> None:
        """Parse type definition hashes."""
        if not self.header or self.header.type_definition_hashes_offset == 0:
            return
        
        reader = Reader(self.data, '<', self.header.type_definition_hashes_offset)
        
        count = self.header.type_definition_hashes_size // 8  # Each hash is 8 bytes
        
        for i in range(count):
            if i < len(self.type_definitions):
                self.type_hashes[i] = reader.read_bytes(8)
    
    def _parse_field_hashes(self) -> None:
        """Parse field definition hashes."""
        if not self.header or self.header.field_definition_hashes_offset == 0:
            return
        
        reader = Reader(self.data, '<', self.header.field_definition_hashes_offset)
        
        count = self.header.field_definition_hashes_size // 8
        
        for i in range(count):
            if i < len(self.field_definitions):
                self.field_hashes[i] = reader.read_bytes(8)
    
    def _parse_method_hashes(self) -> None:
        """Parse method definition hashes."""
        if not self.header or self.header.method_definition_hashes_offset == 0:
            return
        
        reader = Reader(self.data, '<', self.header.method_definition_hashes_offset)
        
        count = self.header.method_definition_hashes_size // 8
        
        for i in range(count):
            if i < len(self.method_definitions):
                self.method_hashes[i] = reader.read_bytes(8)
    
    def get_string(self, index: int) -> str:
        """Get a string from the string literal pool."""
        if index >= len(self.string_literals):
            return f"<invalid_string_index:{index}>"
        
        if index in self.string_cache:
            return self.string_cache[index]
        
        lit = self.string_literals[index]
        
        # Get string data
        if self.header and self.header.string_literal_data_offset > 0:
            data_reader = Reader(self.data, '<', self.header.string_literal_data_offset + lit.data_index)
            string_data = data_reader.read_bytes(lit.length)
            
            # Remove null terminator if present
            if string_data.endswith(b'\x00'):
                string_data = string_data[:-1]
            
            result = string_data.decode('utf-8', errors='replace')
            self.string_cache[index] = result
            return result
        
        return f"<string:{index}>"
    
    def get_type_name(self, type_index: int) -> str:
        """Get the full name of a type."""
        if type_index < 0 or type_index >= len(self.type_definitions):
            return f"<type:{type_index}>"
        
        type_def = self.type_definitions[type_index]
        namespace = self.get_string(type_def.namespace_index)
        name = self.get_string(type_def.name_index)
        
        if namespace:
            return f"{namespace}.{name}"
        return name
    
    def get_method_info(self, method_index: int) -> Dict[str, Any]:
        """Get information about a method."""
        if method_index < 0 or method_index >= len(self.method_definitions):
            return {}
        
        method = self.method_definitions[method_index]
        return {
            'name': self.get_string(method.name_index),
            'declaring_type': self.get_type_name(method.declaring_type),
            'return_type': method.return_type,
            'parameter_count': method.parameter_count,
            'flags': method.flags,
            'token': method.token,
        }
    
    def get_field_info(self, field_index: int) -> Dict[str, Any]:
        """Get information about a field."""
        if field_index < 0 or field_index >= len(self.field_definitions):
            return {}
        
        field = self.field_definitions[field_index]
        return {
            'name': self.get_string(field.name_index),
            'type_index': field.type_index,
            'type_name': self.get_type_name(field.type_index) if field.type_index >= 0 else '<unknown>',
            'token': field.token,
        }
    
    def generate_csharp_skeletons(self) -> Dict[str, str]:
        """
        Generate C# class skeletons from the metadata.
        
        Returns:
            Dictionary mapping type names to C# source code
        """
        skeletons = {}
        
        for type_def in self.type_definitions:
            type_name = self.get_type_name(type_def.index if hasattr(type_def, 'index') else len(skeletons))
            
            # Skip if we already have this type
            if type_name in skeletons:
                continue
            
            # Get base type
            base_type = ""
            if type_def.declaring_type_index >= 0:
                base_type = self.get_type_name(type_def.declaring_type_index)
            elif type_def.byval_type_index >= 0:
                base_type = self.get_type_name(type_def.byval_type_index)
            
            # Build class skeleton
            lines = []
            lines.append(f"// Auto-generated from IL2CPP metadata")
            lines.append(f"// Type: {type_name}")
            lines.append(f"// Token: 0x{type_def.token:08X}")
            lines.append("")
            
            # Check if it's a value type
            if type_def.bitfield & 0x10:  # TYPE_ATTRIBUTE_VALUE_TYPE
                lines.append(f"public struct {type_name.split('.')[-1]}")
            else:
                lines.append(f"public class {type_name.split('.')[-1]}")
            
            if base_type:
                lines[-1] += f" : {base_type.split('.')[-1]}"
            
            lines.append("{")
            
            # Add fields
            for i in range(type_def.field_start, type_def.field_start + type_def.field_count):
                if i < len(self.field_definitions):
                    field = self.field_definitions[i]
                    field_name = self.get_string(field.name_index)
                    field_type = self.get_type_name(field.type_index) if field.type_index >= 0 else "object"
                    
                    # Clean up field name for C#
                    clean_name = field_name
                    if not clean_name or clean_name[0].isdigit():
                        clean_name = f"_{clean_name}"
                    
                    lines.append(f"    public {field_type.split('.')[-1]} {clean_name}; // Token: 0x{field.token:08X}")
            
            # Add methods
            for i in range(type_def.method_start, type_def.method_start + type_def.method_count):
                if i < len(self.method_definitions):
                    method = self.method_definitions[i]
                    method_name = self.get_string(method.name_index)
                    return_type = self.get_type_name(method.return_type) if method.return_type >= 0 else "void"
                    
                    # Clean up method name
                    clean_name = method_name
                    if not clean_name or clean_name[0].isdigit():
                        clean_name = f"_{clean_name}"
                    
                    # Build parameter list
                    params = []
                    for j in range(method.parameter_start, method.parameter_start + method.parameter_count):
                        if j < len(self.parameter_definitions):
                            param = self.parameter_definitions[j]
                            param_name = self.get_string(param.name_index)
                            param_type = self.get_type_name(param.type_index) if param.type_index >= 0 else "object"
                            
                            if not param_name or param_name[0].isdigit():
                                param_name = f"_{param_name}"
                            
                            params.append(f"{param_type.split('.')[-1]} {param_name}")
                    
                    lines.append(f"    public {return_type.split('.')[-1]} {clean_name}({', '.join(params)}) {{ /* Token: 0x{method.token:08X} */ }}")
            
            lines.append("}")
            lines.append("")
            
            skeletons[type_name] = '\n'.join(lines)
        
        return skeletons
    
    def dump(self, output_dir: str) -> None:
        """Dump metadata to files."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Dump type definitions
        with open(os.path.join(output_dir, 'types.txt'), 'w', encoding='utf-8') as f:
            for i, type_def in enumerate(self.type_definitions):
                type_name = self.get_type_name(i)
                f.write(f"Type {i}: {type_name}\n")
                f.write(f"  Methods: {type_def.method_count}\n")
                f.write(f"  Fields: {type_def.field_count}\n")
                f.write(f"  Token: 0x{type_def.token:08X}\n")
                f.write("\n")
        
        # Dump string literals
        with open(os.path.join(output_dir, 'strings.txt'), 'w', encoding='utf-8') as f:
            for i, s in enumerate(self.string_literals[:1000]):  # Limit to first 1000
                try:
                    string_value = self.get_string(i)
                    f.write(f"{i}: {string_value}\n")
                except:
                    pass
        
        # Generate C# skeletons
        skeletons = self.generate_csharp_skeletons()
        scripts_dir = os.path.join(output_dir, 'Scripts')
        os.makedirs(scripts_dir, exist_ok=True)
        
        for type_name, source in skeletons.items():
            safe_name = ''.join(c if c.isalnum() or c in ('_', '.') else '_' for c in type_name)
            if not safe_name:
                safe_name = 'Unknown'
            
            # Split namespace and class name
            parts = safe_name.rsplit('.', 1)
            if len(parts) == 2:
                namespace = parts[0]
                class_name = parts[1]
                subdir = os.path.join(scripts_dir, *namespace.split('.'))
                os.makedirs(subdir, exist_ok=True)
                file_path = os.path.join(subdir, f"{class_name}.cs")
            else:
                file_path = os.path.join(scripts_dir, f"{safe_name}.cs")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(source)
