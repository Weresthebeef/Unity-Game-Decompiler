"""UnityFS bundle parser for .unity3d files."""
import struct
from typing import List, Optional, Dict, Any
from .utils import Reader, decompress_data, COMPRESSION_LZ4, COMPRESSION_LZ4HC, COMPRESSION_LZMA, COMPRESSION_NONE


SIGNATURE_UNITYFS = b"UnityFS\x00"
SIGNATURE_UNITYWEB = b"UnityWeb"
SIGNATURE_UNITYRAW = b"UnityRaw"


class BundleEntry:
    """Represents a file entry in a UnityFS bundle."""
    __slots__ = ('name', 'path', 'offset', 'size', 'flags', 'data')
    
    def __init__(self, name: str, path: str, offset: int, size: int, flags: int):
        self.name = name
        self.path = path
        self.offset = offset
        self.size = size
        self.flags = flags
        self.data: Optional[bytes] = None


class BundleFile:
    """Parser for UnityFS bundle files."""
    __slots__ = (
        'signature', 'version', 'unity_version', 'unity_revision', 'flags',
        'blocks', 'entries', 'data', '_decompressed_data'
    )
    
    def __init__(self):
        self.signature = b''
        self.version = 0
        self.unity_version = ''
        self.unity_revision = ''
        self.flags = 0
        self.blocks: List[dict] = []
        self.entries: List[BundleEntry] = []
        self.data: bytes = b''
        self._decompressed_data: Optional[bytes] = None
    
    def parse(self, data: bytes) -> bool:
        """Parse a UnityFS bundle from bytes."""
        self.data = data
        reader = Reader(data)
        
        # Read signature
        self.signature = reader.read_bytes(8)
        
        if self.signature == SIGNATURE_UNITYFS:
            return self._parse_unityfs(reader)
        elif self.signature.startswith(SIGNATURE_UNITYWEB):
            return self._parse_unityweb(reader)
        elif self.signature.startswith(SIGNATURE_UNITYRAW):
            return self._parse_unityraw(reader)
        else:
            return False
    
    def _parse_unityfs(self, reader: Reader) -> bool:
        """Parse UnityFS format bundle."""
        self.version = reader.read_u32()
        self.unity_version = reader.read_cstring()
        self.unity_revision = reader.read_cstring()
        file_size = reader.read_u64()
        blocks_info_size = reader.read_u32()
        blocks_info_compressed = reader.read_bytes(blocks_info_size)
        self.flags = reader.read_u32()
        
        header_size = reader.tell()
        
        # Parse blocks info
        blocks_info = self._decompress_blocks_info(blocks_info_compressed)
        if not blocks_info:
            return False
        
        blocks_info_reader = Reader(blocks_info)
        blocks_info_uncompressed_size = blocks_info_reader.read_u32()
        blocks_info_compressed_size = blocks_info_reader.read_u32()
        blocks_info_flags = blocks_info_reader.read_u16()
        
        # Parse blocks
        while blocks_info_reader.remaining() >= 12:
            block_uncompressed_size = blocks_info_reader.read_u32()
            block_compressed_size = blocks_info_reader.read_u32()
            block_flags = blocks_info_reader.read_u16()
            
            if block_uncompressed_size == 0 and block_compressed_size == 0:
                break
            
            block_data = reader.read_bytes(block_compressed_size)
            compression = block_flags & 0x3F
            is_directory = (block_flags & 0x40) != 0
            
            self.blocks.append({
                'uncompressed_size': block_uncompressed_size,
                'compressed_size': block_compressed_size,
                'flags': block_flags,
                'compression': compression,
                'data': block_data,
                'is_directory': is_directory
            })
        
        # Concatenate and decompress all blocks
        self._decompressed_data = b''
        for block in self.blocks:
            decompressed = decompress_data(
                block['data'],
                block['compression'],
                block['uncompressed_size']
            )
            self._decompressed_data += decompressed
        
        # Parse directory if present
        if self._decompressed_data:
            dir_reader = Reader(self._decompressed_data)
            
            # Directory header
            dir_uncompressed_size = dir_reader.read_u32()
            dir_compressed_size = dir_reader.read_u32()
            dir_flags = dir_reader.read_u16()
            
            # Directory entries
            while dir_reader.remaining() >= 16:
                offset = dir_reader.read_u64()
                size = dir_reader.read_u64()
                flags = dir_reader.read_u32()
                path = dir_reader.read_cstring()
                
                # Extract name from path (remove "archive:/" prefix)
                if path.startswith('archive:/'):
                    name = path[9:]
                else:
                    name = path
                
                self.entries.append(BundleEntry(name, path, offset, size, flags))
        
        return True
    
    def _decompress_blocks_info(self, data: bytes) -> Optional[bytes]:
        """Decompress the blocks info data."""
        if len(data) < 10:
            return None
        
        reader = Reader(data)
        uncompressed_size = reader.read_u32()
        compressed_size = reader.read_u32()
        flags = reader.read_u16()
        
        compression = flags & 0x3F
        return decompress_data(data[10:], compression, uncompressed_size)
    
    def _parse_unityweb(self, reader: Reader) -> bool:
        """Parse UnityWeb format bundle."""
        self.version = reader.read_u32()
        self.unity_version = reader.read_cstring()
        self.unity_revision = reader.read_cstring()
        _ = reader.read_cstring()  # minimum Unity version
        file_size = reader.read_u64()
        
        # The rest is directory data (LZMA compressed)
        dir_data = reader.read_bytes(reader.remaining())
        
        try:
            decompressed = lzma.decompress(dir_data, format=lzma.FORMAT_ALONE)
        except Exception:
            decompressed = dir_data
        
        dir_reader = Reader(decompressed)
        entry_count = dir_reader.read_u32()
        
        self._decompressed_data = b''
        
        for _ in range(entry_count):
            offset = dir_reader.read_u32()
            size = dir_reader.read_u32()
            type_ = dir_reader.read_u32()
            name = dir_reader.read_cstring()
            
            self.entries.append(BundleEntry(name, name, offset, size, type_))
        
        # Data starts after directory
        data_start = header_size = reader.tell() - len(dir_data) + len(decompressed)
        for entry in self.entries:
            entry.offset += data_start
        
        # Read all remaining data
        self._decompressed_data = reader.data[data_start:]
        
        return True
    
    def _parse_unityraw(self, reader: Reader) -> bool:
        """Parse UnityRaw format bundle."""
        self.version = reader.read_u32()
        self.unity_version = reader.read_cstring()
        self.unity_revision = reader.read_cstring()
        _ = reader.read_cstring()  # minimum Unity version
        file_size = reader.read_u64()
        
        # Directory is uncompressed
        entry_count = reader.read_u32()
        
        self._decompressed_data = b''
        
        for _ in range(entry_count):
            offset = reader.read_u32()
            size = reader.read_u32()
            type_ = reader.read_u32()
            name = reader.read_cstring()
            
            self.entries.append(BundleEntry(name, name, offset, size, type_))
        
        # Data starts after directory
        data_start = reader.tell()
        self._decompressed_data = reader.data[data_start:]
        
        for entry in self.entries:
            entry.offset += data_start
        
        return True
    
    def extract_entry(self, entry: BundleEntry) -> bytes:
        """Extract the data for a specific entry."""
        if entry.data is not None:
            return entry.data
        
        if self._decompressed_data is None:
            return b''
        
        start = entry.offset
        end = start + entry.size
        
        if end > len(self._decompressed_data):
            end = len(self._decompressed_data)
        
        entry.data = self._decompressed_data[start:end]
        return entry.data
    
    def extract_all(self) -> Dict[str, bytes]:
        """Extract all entries as a dictionary."""
        result = {}
        for entry in self.entries:
            result[entry.name] = self.extract_entry(entry)
        return result
    
    def get_entry_by_name(self, name: str) -> Optional[BundleEntry]:
        """Get an entry by name."""
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None
    
    def get_entries_by_extension(self, ext: str) -> List[BundleEntry]:
        """Get all entries with a specific extension."""
        ext = ext.lower()
        if ext.startswith('.'):
            ext = ext[1:]
        return [e for e in self.entries if e.name.lower().endswith(f'.{ext}')]
