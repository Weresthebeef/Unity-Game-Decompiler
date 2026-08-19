"""
Mono PE/CLI parser for .NET assemblies.
Parses PE headers, CLI metadata, and method bodies.
"""
import struct
from typing import Dict, List, Optional, Any, Tuple, BinaryIO
from ..utils import Reader


# ============================================================
# PE Constants
# ============================================================

PE_MAGIC = 0x5A4D  # MZ
PE_SIGNATURE = b"PE\x00\x00"
COFF_MAGIC_32 = 0x010B
COFF_MAGIC_64 = 0x8664

# CLI header constants
CLI_HEADER_SIZE = 72

# Metadata stream names
STREAM_META = b"#~"
STREAM_STRINGS = b"#Strings"
STREAM_US = b"#US"
STREAM_GUID = b"#GUID"
STREAM_BLOB = b"#Blob"

# Metadata tables
TABLE_MODULE = 0
TABLE_TYPE_REF = 1
TABLE_TYPE_DEF = 2
TABLE_FIELD_PTR = 3
TABLE_FIELD = 4
TABLE_METHOD_PTR = 5
TABLE_METHOD = 6
TABLE_PARAM_PTR = 7
TABLE_PARAM = 8
TABLE_INTERFACE_IMPL = 9
TABLE_MEMBER_REF = 10
TABLE_CONSTANT = 11
TABLE_CUSTOM_ATTRIBUTE = 12
TABLE_FIELD_MARSHAL = 13
TABLE_DECL_SECURITY = 14
TABLE_CLASS_LAYOUT = 15
TABLE_FIELD_LAYOUT = 16
TABLE_STANDALONE_SIG = 17
TABLE_EVENT_MAP = 18
TABLE_EVENT_PTR = 19
TABLE_EVENT = 20
TABLE_PROPERTY_MAP = 21
TABLE_PROPERTY_PTR = 22
TABLE_PROPERTY = 23
TABLE_METHOD_SEMANTICS = 24
TABLE_METHOD_IMPL = 25
TABLE_MODULE_REF = 26
TABLE_TYPE_SPEC = 27
TABLE_IMPL_MAP = 28
TABLE_FIELD_RVA = 29
TABLE_ENC_LOG = 30
TABLE_ENC_MAP = 31
TABLE_ASSEMBLY = 32
TABLE_ASSEMBLY_OS = 33
TABLE_ASSEMBLY_REF = 34
TABLE_ASSEMBLY_REF_OS = 35
TABLE_FILE = 36
TABLE_EXPORTED_TYPE = 37
TABLE_MANIFEST_RESOURCE = 38
TABLE_NESTED_CLASS = 39
TABLE_GENERIC_PARAM = 40
TABLE_METHOD_SPEC = 41
TABLE_GENERIC_PARAM_CONSTRAINT = 42

TABLE_COUNT = 43

# Table column counts
TABLE_COLUMNS = [
    5,  # Module
    3,  # TypeRef
    5,  # TypeDef
    2,  # FieldPtr
    6,  # Field
    2,  # MethodPtr
    8,  # Method
    2,  # ParamPtr
    4,  # Param
    2,  # InterfaceImpl
    3,  # MemberRef
    3,  # Constant
    3,  # CustomAttribute
    2,  # FieldMarshal
    3,  # DeclSecurity
    6,  # ClassLayout
    2,  # FieldLayout
    1,  # StandAloneSig
    2,  # EventMap
    2,  # EventPtr
    5,  # Event
    2,  # PropertyMap
    2,  # PropertyPtr
    4,  # Property
    3,  # MethodSemantics
    3,  # MethodImpl
    1,  # ModuleRef
    3,  # TypeSpec
    2,  # ImplMap
    2,  # FieldRVA
    2,  # ENCLog
    2,  # ENCMap
    9,  # Assembly
    3,  # AssemblyOS
    5,  # AssemblyRef
    3,  # AssemblyRefOS
    4,  # File
    4,  # ExportedType
    4,  # ManifestResource
    2,  # NestedClass
    4,  # GenericParam
    3,  # MethodSpec
    2,  # GenericParamConstraint
]

# ============================================================
# PE/COFF Structures
# ============================================================

class DOSHeader:
    """DOS header structure."""
    __slots__ = ('e_magic', 'e_cblp', 'e_cp', 'e_crlc', 'e_cparhdr', 'e_minalloc',
                 'e_maxalloc', 'e_ss', 'e_sp', 'e_csum', 'e_ip', 'e_cs',
                 'e_lfarlc', 'e_ovno', 'e_res', 'e_oemid', 'e_oeminfo',
                 'e_res2', 'e_lfanew')
    
    def __init__(self):
        self.e_magic = 0
        self.e_lfanew = 0


class COFFHeader:
    """COFF header structure."""
    __slots__ = ('Machine', 'NumberOfSections', 'TimeDateStamp',
                 'PointerToSymbolTable', 'NumberOfSymbols',
                 'SizeOfOptionalHeader', 'Characteristics')
    
    def __init__(self):
        self.Machine = 0
        self.NumberOfSections = 0
        self.TimeDateStamp = 0
        self.PointerToSymbolTable = 0
        self.NumberOfSymbols = 0
        self.SizeOfOptionalHeader = 0
        self.Characteristics = 0


class PEOptionalHeader:
    """PE optional header structure."""
    __slots__ = (
        'Magic', 'MajorLinkerVersion', 'MinorLinkerVersion',
        'SizeOfCode', 'SizeOfInitializedData', 'SizeOfUninitializedData',
        'AddressOfEntryPoint', 'BaseOfCode', 'BaseOfData',
        'ImageBase', 'SectionAlignment', 'FileAlignment',
        'MajorOperatingSystemVersion', 'MinorOperatingSystemVersion',
        'MajorImageVersion', 'MinorImageVersion',
        'MajorSubsystemVersion', 'MinorSubsystemVersion',
        'Win32VersionValue', 'SizeOfImage', 'SizeOfHeaders',
        'CheckSum', 'Subsystem', 'DllCharacteristics',
        'SizeOfStackReserve', 'SizeOfStackCommit',
        'SizeOfHeapReserve', 'SizeOfHeapCommit',
        'LoaderFlags', 'NumberOfRvaAndSizes',
        'DataDirectories',
    )
    
    def __init__(self):
        self.Magic = 0
        self.ImageBase = 0
        self.SectionAlignment = 0
        self.FileAlignment = 0
        self.SizeOfImage = 0
        self.SizeOfHeaders = 0
        self.DataDirectories = []


class SectionHeader:
    """Section header structure."""
    __slots__ = (
        'Name', 'VirtualSize', 'VirtualAddress', 'SizeOfRawData',
        'PointerToRawData', 'PointerToRelocations',
        'PointerToLinenumbers', 'NumberOfRelocations',
        'NumberOfLinenumbers', 'Characteristics',
    )
    
    def __init__(self):
        self.Name = b''
        self.VirtualSize = 0
        self.VirtualAddress = 0
        self.SizeOfRawData = 0
        self.PointerToRawData = 0
        self.Characteristics = 0


class CLIHeader:
    """CLI header structure."""
    __slots__ = (
        'cb', 'MajorRuntimeVersion', 'MinorRuntimeVersion',
        'MetaData', 'Flags', 'EntryPointToken',
        'Resources', 'StrongNameSignature',
        'CodeManagerTable', 'VTableFixups',
        'ExportAddressTableJumps', 'ManagedNativeHeader',
    )
    
    def __init__(self):
        self.cb = 0
        self.MajorRuntimeVersion = 0
        self.MinorRuntimeVersion = 0
        self.MetaData = (0, 0)  # RVA, Size
        self.Flags = 0
        self.EntryPointToken = 0
        self.Resources = (0, 0)
        self.StrongNameSignature = (0, 0)


# ============================================================
# Metadata Tables
# ============================================================

class MetadataTables:
    """Metadata tables parser."""
    
    def __init__(self):
        self.tables: Dict[int, List[Dict[str, Any]]] = {}
        self.string_heap: bytes = b''
        self.guid_heap: bytes = b''
        self.blob_heap: bytes = b''
        self.us_heap: bytes = b''
    
    def parse(self, data: bytes, table_offsets: Dict[int, Tuple[int, int]], 
              string_offset: int, string_size: int,
              guid_offset: int, guid_size: int,
              blob_offset: int, blob_size: int,
              us_offset: int, us_size: int) -> None:
        """Parse metadata tables."""
        reader = Reader(data, '<')
        
        # Store heap references
        self.string_heap = data[string_offset:string_offset + string_size]
        self.guid_heap = data[guid_offset:guid_offset + guid_size]
        self.blob_heap = data[blob_offset:blob_offset + blob_size]
        self.us_heap = data[us_offset:us_offset + us_size]
        
        # Parse each table
        for table_idx, (offset, row_count) in table_offsets.items():
            if row_count == 0:
                self.tables[table_idx] = []
                continue
            
            column_count = TABLE_COLUMNS[table_idx]
            reader.pos = offset
            
            rows = []
            for _ in range(row_count):
                row = {}
                for col_idx in range(column_count):
                    col_name = self._get_column_name(table_idx, col_idx)
                    col_type = self._get_column_type(table_idx, col_idx)
                    
                    if col_type == 'u1':
                        row[col_name] = reader.read_u8()
                    elif col_type == 'i1':
                        row[col_name] = reader.read_i8()
                    elif col_type == 'u2':
                        row[col_name] = reader.read_u16()
                    elif col_type == 'i2':
                        row[col_name] = reader.read_i16()
                    elif col_type == 'u4':
                        row[col_name] = reader.read_u32()
                    elif col_type == 'i4':
                        row[col_name] = reader.read_i32()
                    elif col_type == 'r4':
                        row[col_name] = reader.read_float()
                    elif col_type == 'r8':
                        row[col_name] = reader.read_double()
                    elif col_type == 'string':
                        string_offset = reader.read_u32()
                        row[col_name] = self._get_string(string_offset)
                    elif col_type == 'guid':
                        guid_offset = reader.read_u32()
                        row[col_name] = self._get_guid(guid_offset)
                    elif col_type == 'blob':
                        blob_offset = reader.read_u32()
                        row[col_name] = self._get_blob(blob_offset)
                    elif col_type == 'table':
                        table_idx = reader.read_u32()
                        row[col_name] = table_idx
                
                rows.append(row)
            
            self.tables[table_idx] = rows
    
    def _get_column_name(self, table_idx: int, col_idx: int) -> str:
        """Get column name for a table."""
        column_names = {
            TABLE_MODULE: ['Generation', 'Name', 'Mvid', 'EncId', 'EncBaseId'],
            TABLE_TYPE_REF: ['ResolutionScope', 'TypeName', 'TypeNamespace'],
            TABLE_TYPE_DEF: ['Flags', 'TypeName', 'TypeNamespace', 'Extends', 'FieldList',
                           'MethodList'],
            TABLE_FIELD: ['Flags', 'Name', 'Signature'],
            TABLE_METHOD: ['RVA', 'ImplFlags', 'Flags', 'Name', 'Signature',
                         'ParamList', 'MethodDefOrRef', 'CodeSize'],
            TABLE_PARAM: ['Flags', 'Sequence', 'Name', 'Type'],
            TABLE_INTERFACE_IMPL: ['Class', 'Interface'],
            TABLE_MEMBER_REF: ['Class', 'Name', 'Signature'],
            TABLE_CONSTANT: ['Type', 'Parent', 'Value'],
            TABLE_CUSTOM_ATTRIBUTE: ['Parent', 'Type', 'Value'],
            TABLE_FIELD_MARSHAL: ['Parent', 'NativeType'],
            TABLE_ASSEMBLY: ['HashAlgId', 'MajorVersion', 'MinorVersion', 'BuildNumber',
                          'RevisionNumber', 'Flags', 'PublicKey', 'Name', 'Culture'],
            TABLE_ASSEMBLY_REF: ['MajorVersion', 'MinorVersion', 'BuildNumber',
                              'RevisionNumber', 'Flags', 'PublicKeyOrToken',
                              'Name', 'Culture', 'HashValue'],
            TABLE_FILE: ['Flags', 'Name', 'HashValue', 'Contents'],
            TABLE_EXPORTED_TYPE: ['Flags', 'TypeDefId', 'TypeName', 'TypeNamespace'],
            TABLE_MANIFEST_RESOURCE: ['Offset', 'Flags', 'Name', 'Implementation'],
            TABLE_NESTED_CLASS: ['NestedClass', 'EnclosingClass'],
            TABLE_GENERIC_PARAM: ['Number', 'Flags', 'Owner', 'Name'],
            TABLE_METHOD_SPEC: ['Method', 'Instantiation'],
            TABLE_GENERIC_PARAM_CONSTRAINT: ['Owner', 'Constraint'],
        }
        
        names = column_names.get(table_idx, [])
        if col_idx < len(names):
            return names[col_idx]
        return f'col_{col_idx}'
    
    def _get_column_type(self, table_idx: int, col_idx: int) -> str:
        """Get column type for a table."""
        # Simplified - all are u4 except strings
        if table_idx in [TABLE_TYPE_DEF, TABLE_TYPE_REF, TABLE_FIELD, TABLE_METHOD, 
                         TABLE_PARAM, TABLE_MEMBER_REF, TABLE_ASSEMBLY, 
                         TABLE_ASSEMBLY_REF, TABLE_FILE, TABLE_EXPORTED_TYPE,
                         TABLE_MANIFEST_RESOURCE, TABLE_NESTED_CLASS, 
                         TABLE_GENERIC_PARAM]:
            if col_idx == 1:  # Name column
                return 'string'
            elif col_idx == 2 and table_idx in [TABLE_TYPE_REF, TABLE_TYPE_DEF]:  # Namespace
                return 'string'
        
        return 'u4'
    
    def _get_string(self, offset: int) -> str:
        """Get a string from the string heap."""
        if offset == 0:
            return ''
        if offset >= len(self.string_heap):
            return f'<invalid_string_offset:{offset}>'
        
        # Find null terminator
        end = offset
        while end < len(self.string_heap) and self.string_heap[end] != 0:
            end += 1
        
        return self.string_heap[offset:end].decode('utf-8', errors='replace')
    
    def _get_guid(self, offset: int) -> str:
        """Get a GUID from the GUID heap."""
        if offset == 0:
            return ''
        if offset + 16 > len(self.guid_heap):
            return f'<invalid_guid_offset:{offset}>'
        
        guid_bytes = self.guid_heap[offset:offset + 16]
        return guid_bytes.hex()
    
    def _get_blob(self, offset: int) -> bytes:
        """Get a blob from the blob heap."""
        if offset == 0:
            return b''
        if offset >= len(self.blob_heap):
            return b''
        
        # Blob is prefixed with compressed size (4 bytes)
        reader = Reader(self.blob_heap, '<', offset)
        size = reader.read_u32()
        return reader.read_bytes(size)


# ============================================================
# PE Parser
# ============================================================

class MonoAssembly:
    """Mono/.NET assembly parser."""
    
    def __init__(self):
        self.data: bytes = b''
        self.dos_header: Optional[DOSHeader] = None
        self.coff_header: Optional[COFFHeader] = None
        self.optional_header: Optional[PEOptionalHeader] = None
        self.section_headers: List[SectionHeader] = []
        self.cli_header: Optional[CLIHeader] = None
        self.metadata: Optional[MetadataTables] = None
        self.types: Dict[str, Dict[str, Any]] = {}
        self.methods: Dict[str, Dict[str, Any]] = {}
    
    def parse(self, data: bytes) -> bool:
        """Parse a Mono assembly from bytes."""
        self.data = data
        reader = Reader(data, '<')
        
        # Parse DOS header
        self.dos_header = DOSHeader()
        self.dos_header.e_magic = reader.read_u16()
        if self.dos_header.e_magic != PE_MAGIC:
            return False
        
        reader.seek(0x3C)
        self.dos_header.e_lfanew = reader.read_u32()
        
        # Parse PE header
        reader.seek(self.dos_header.e_lfanew)
        pe_signature = reader.read_bytes(4)
        if pe_signature != PE_SIGNATURE:
            return False
        
        # Parse COFF header
        self.coff_header = COFFHeader()
        self.coff_header.Machine = reader.read_u16()
        self.coff_header.NumberOfSections = reader.read_u16()
        self.coff_header.TimeDateStamp = reader.read_u32()
        self.coff_header.PointerToSymbolTable = reader.read_u32()
        self.coff_header.NumberOfSymbols = reader.read_u32()
        self.coff_header.SizeOfOptionalHeader = reader.read_u16()
        self.coff_header.Characteristics = reader.read_u16()
        
        # Parse optional header
        self.optional_header = PEOptionalHeader()
        self.optional_header.Magic = reader.read_u16()
        
        if self.optional_header.Magic == COFF_MAGIC_32:
            # PE32
            reader.seek(4, 1)  # Skip linker version
            self.optional_header.SizeOfCode = reader.read_u32()
            self.optional_header.SizeOfInitializedData = reader.read_u32()
            self.optional_header.SizeOfUninitializedData = reader.read_u32()
            self.optional_header.AddressOfEntryPoint = reader.read_u32()
            self.optional_header.BaseOfCode = reader.read_u32()
            self.optional_header.BaseOfData = reader.read_u32()
            self.optional_header.ImageBase = reader.read_u32()
            self.optional_header.SectionAlignment = reader.read_u32()
            self.optional_header.FileAlignment = reader.read_u32()
            self.optional_header.MajorOperatingSystemVersion = reader.read_u16()
            self.optional_header.MinorOperatingSystemVersion = reader.read_u16()
            self.optional_header.MajorImageVersion = reader.read_u16()
            self.optional_header.MinorImageVersion = reader.read_u16()
            self.optional_header.MajorSubsystemVersion = reader.read_u16()
            self.optional_header.MinorSubsystemVersion = reader.read_u16()
            self.optional_header.Win32VersionValue = reader.read_u32()
            self.optional_header.SizeOfImage = reader.read_u32()
            self.optional_header.SizeOfHeaders = reader.read_u32()
            self.optional_header.CheckSum = reader.read_u32()
            self.optional_header.Subsystem = reader.read_u16()
            self.optional_header.DllCharacteristics = reader.read_u16()
            self.optional_header.SizeOfStackReserve = reader.read_u32()
            self.optional_header.SizeOfStackCommit = reader.read_u32()
            self.optional_header.SizeOfHeapReserve = reader.read_u32()
            self.optional_header.SizeOfHeapCommit = reader.read_u32()
            self.optional_header.LoaderFlags = reader.read_u32()
            self.optional_header.NumberOfRvaAndSizes = reader.read_u32()
        else:
            # PE32+ (64-bit)
            reader.seek(4, 1)  # Skip linker version
            self.optional_header.Magic = COFF_MAGIC_64
            self.optional_header.SizeOfCode = reader.read_u32()
            self.optional_header.SizeOfInitializedData = reader.read_u32()
            self.optional_header.SizeOfUninitializedData = reader.read_u32()
            self.optional_header.AddressOfEntryPoint = reader.read_u32()
            self.optional_header.BaseOfCode = reader.read_u32()
            self.optional_header.ImageBase = reader.read_u64()
            self.optional_header.SectionAlignment = reader.read_u32()
            self.optional_header.FileAlignment = reader.read_u32()
            self.optional_header.MajorOperatingSystemVersion = reader.read_u16()
            self.optional_header.MinorOperatingSystemVersion = reader.read_u16()
            self.optional_header.MajorImageVersion = reader.read_u16()
            self.optional_header.MinorImageVersion = reader.read_u16()
            self.optional_header.MajorSubsystemVersion = reader.read_u16()
            self.optional_header.MinorSubsystemVersion = reader.read_u16()
            self.optional_header.Win32VersionValue = reader.read_u32()
            self.optional_header.SizeOfImage = reader.read_u32()
            self.optional_header.SizeOfHeaders = reader.read_u32()
            self.optional_header.CheckSum = reader.read_u32()
            self.optional_header.Subsystem = reader.read_u16()
            self.optional_header.DllCharacteristics = reader.read_u16()
            self.optional_header.SizeOfStackReserve = reader.read_u64()
            self.optional_header.SizeOfStackCommit = reader.read_u64()
            self.optional_header.SizeOfHeapReserve = reader.read_u64()
            self.optional_header.SizeOfHeapCommit = reader.read_u64()
            self.optional_header.LoaderFlags = reader.read_u32()
            self.optional_header.NumberOfRvaAndSizes = reader.read_u32()
        
        # Read data directories
        for _ in range(self.optional_header.NumberOfRvaAndSizes):
            rva = reader.read_u32()
            size = reader.read_u32()
            self.optional_header.DataDirectories.append((rva, size))
        
        # Parse section headers
        for _ in range(self.coff_header.NumberOfSections):
            section = SectionHeader()
            section.Name = reader.read_bytes(8).rstrip(b'\x00')
            section.VirtualSize = reader.read_u32()
            section.VirtualAddress = reader.read_u32()
            section.SizeOfRawData = reader.read_u32()
            section.PointerToRawData = reader.read_u32()
            section.PointerToRelocations = reader.read_u32()
            section.PointerToLinenumbers = reader.read_u32()
            section.NumberOfRelocations = reader.read_u16()
            section.NumberOfLinenumbers = reader.read_u16()
            section.Characteristics = reader.read_u32()
            self.section_headers.append(section)
        
        # Find CLI header (in .text section or data directory)
        cli_rva, cli_size = self.optional_header.DataDirectories[14]  # CLI directory
        if cli_rva == 0 or cli_size < CLI_HEADER_SIZE:
            # Try to find in .text section
            for section in self.section_headers:
                if section.Name == b'.text':
                    # Scan for CLI signature
                    text_data = data[section.PointerToRawData:section.PointerToRawData + section.SizeOfRawData]
                    cli_offset = text_data.find(b'\x42\x53\x4A\x42')  # "BSJB"
                    if cli_offset != -1:
                        cli_rva = section.VirtualAddress + cli_offset
                        cli_size = len(text_data) - cli_offset
                        break
        
        if cli_rva == 0:
            return False
        
        # Parse CLI header
        cli_offset = self._rva_to_offset(cli_rva)
        if cli_offset == -1:
            return False
        
        reader.pos = cli_offset
        self.cli_header = CLIHeader()
        self.cli_header.cb = reader.read_u32()
        self.cli_header.MajorRuntimeVersion = reader.read_u16()
        self.cli_header.MinorRuntimeVersion = reader.read_u16()
        self.cli_header.MetaData = (reader.read_u32(), reader.read_u32())
        self.cli_header.Flags = reader.read_u32()
        self.cli_header.EntryPointToken = reader.read_u32()
        self.cli_header.Resources = (reader.read_u32(), reader.read_u32())
        self.cli_header.StrongNameSignature = (reader.read_u32(), reader.read_u32())
        
        # Parse metadata
        self._parse_metadata()
        
        # Extract types and methods
        self._extract_types()
        self._extract_methods()
        
        return True
    
    def _rva_to_offset(self, rva: int) -> int:
        """Convert RVA to file offset."""
        for section in self.section_headers:
            if (section.VirtualAddress <= rva < 
                section.VirtualAddress + max(section.SizeOfRawData, section.VirtualSize)):
                return section.PointerToRawData + (rva - section.VirtualAddress)
        return -1
    
    def _parse_metadata(self) -> None:
        """Parse CLI metadata."""
        if not self.cli_header:
            return
        
        metadata_rva, metadata_size = self.cli_header.MetaData
        metadata_offset = self._rva_to_offset(metadata_rva)
        if metadata_offset == -1:
            return
        
        reader = Reader(self.data, '<', metadata_offset)
        
        # Read metadata signature
        signature = reader.read_u32()
        if signature != 0x424A5342:  # "BSJB"
            return
        
        # Read version
        major_version = reader.read_u16()
        minor_version = reader.read_u16()
        
        # Read stream headers
        stream_count = reader.read_u16()
        reader.align(4)
        
        stream_offsets = {}
        stream_sizes = {}
        
        for _ in range(stream_count):
            offset = reader.read_u32()
            size = reader.read_u32()
            name_offset = metadata_offset + offset
            name_reader = Reader(self.data, '<', name_offset)
            name = name_reader.read_cstring()
            
            stream_offsets[name] = offset
            stream_sizes[name] = size
        
        # Parse tables stream
        if STREAM_META in stream_offsets:
            tables_offset = metadata_offset + stream_offsets[STREAM_META]
            tables_size = stream_sizes[STREAM_META]
            
            tables_reader = Reader(self.data, '<', tables_offset)
            
            # Read reserved (4 bytes)
            tables_reader.read_u32()
            
            # Read major version (1 byte)
            tables_reader.read_u8()
            
            # Read minor version (1 byte)
            tables_reader.read_u8()
            
            # Read heap sizes (5 u32)
            heap_sizes = [tables_reader.read_u32() for _ in range(5)]
            
            # Read mask valid (1 byte)
            mask_valid = tables_reader.read_u8()
            
            # Read mask sorted (1 byte)
            mask_sorted = tables_reader.read_u8()
            
            # Read table counts (43 u32)
            table_rows = [tables_reader.read_u32() for _ in range(TABLE_COUNT)]
            
            # Build table offsets
            table_offsets = {}
            current_offset = tables_offset + tables_reader.tell()
            
            for i in range(TABLE_COUNT):
                table_offsets[i] = (current_offset, table_rows[i])
                current_offset += table_rows[i] * TABLE_COLUMNS[i] * 4
            
            # Get stream offsets for heaps
            string_offset = metadata_offset + stream_offsets.get(STREAM_STRINGS, 0)
            string_size = stream_sizes.get(STREAM_STRINGS, 0)
            guid_offset = metadata_offset + stream_offsets.get(STREAM_GUID, 0)
            guid_size = stream_sizes.get(STREAM_GUID, 0)
            blob_offset = metadata_offset + stream_offsets.get(STREAM_BLOB, 0)
            blob_size = stream_sizes.get(STREAM_BLOB, 0)
            us_offset = metadata_offset + stream_offsets.get(STREAM_US, 0)
            us_size = stream_sizes.get(STREAM_US, 0)
            
            # Parse tables
            self.metadata = MetadataTables()
            self.metadata.parse(
                self.data, table_offsets,
                string_offset, string_size,
                guid_offset, guid_size,
                blob_offset, blob_size,
                us_offset, us_size
            )
    
    def _extract_types(self) -> None:
        """Extract type information from metadata."""
        if not self.metadata or TABLE_TYPE_DEF not in self.metadata.tables:
            return
        
        for row in self.metadata.tables[TABLE_TYPE_DEF]:
            type_name = row.get('TypeName', '')
            type_namespace = row.get('TypeNamespace', '')
            full_name = f"{type_namespace}.{type_name}" if type_namespace else type_name
            
            self.types[full_name] = {
                'name': type_name,
                'namespace': type_namespace,
                'flags': row.get('Flags', 0),
                'extends': row.get('Extends', 0),
                'field_list': row.get('FieldList', 0),
                'method_list': row.get('MethodList', 0),
            }
    
    def _extract_methods(self) -> None:
        """Extract method information from metadata."""
        if not self.metadata or TABLE_METHOD not in self.metadata.tables:
            return
        
        for row in self.metadata.tables[TABLE_METHOD]:
            method_name = row.get('Name', '')
            method_rva = row.get('RVA', 0)
            method_flags = row.get('Flags', 0)
            method_impl_flags = row.get('ImplFlags', 0)
            method_param_list = row.get('ParamList', 0)
            
            self.methods[method_name] = {
                'rva': method_rva,
                'flags': method_flags,
                'impl_flags': method_impl_flags,
                'param_list': method_param_list,
            }
    
    def get_method_body(self, rva: int) -> Optional[bytes]:
        """Get the method body (IL) for a given RVA."""
        for section in self.section_headers:
            if (section.VirtualAddress <= rva < 
                section.VirtualAddress + max(section.SizeOfRawData, section.VirtualSize)):
                offset = section.PointerToRawData + (rva - section.VirtualAddress)
                
                # Read method header
                reader = Reader(self.data, '<', offset)
                
                # Check for tiny method (1 byte)
                if reader.read_u8() == 0xFE:
                    # Tiny method - the byte is the opcode
                    return bytes([0xFE])
                
                reader.pos = offset
                
                # Read method header
                flags = reader.read_u8()
                size = reader.read_u16() if (flags & 0x80) == 0 else reader.read_u32()
                
                # Read IL code
                code_size = reader.read_u32()
                local_var_sig_token = reader.read_u32()
                
                # Read max stack
                max_stack = reader.read_u16()
                
                # Read code size again (should match)
                code_size_2 = reader.read_u32()
                
                # Read local var token
                local_var_token = reader.read_u32()
                
                # The IL code follows
                il_code = reader.read_bytes(code_size)
                
                return il_code
        
        return None
    
    def get_type_methods(self, type_name: str) -> List[Dict[str, Any]]:
        """Get all methods for a type."""
        if type_name not in self.types:
            return []
        
        type_info = self.types[type_name]
        method_list_idx = type_info.get('method_list', 0)
        
        # Find methods in method table that belong to this type
        methods = []
        if self.metadata and TABLE_METHOD in self.metadata.tables:
            for row in self.metadata.tables[TABLE_METHOD]:
                # Check if method belongs to this type
                # (In a full implementation, we'd check the declaring type)
                methods.append(row)
        
        return methods
