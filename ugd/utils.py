"""Binary parsing helpers, compression, hashing, and image utilities."""
import struct
import zlib
import hashlib
import lzma
from typing import Optional, Union, IO, BinaryIO


# ============================================================
# Binary Reader
# ============================================================

class Reader:
    """Little-endian binary reader with alignment support."""
    __slots__ = ('data', 'pos', 'endian')
    
    def __init__(self, data: bytes, endian: str = '<', pos: int = 0):
        self.data = data
        self.pos = pos
        self.endian = endian
    
    def remaining(self) -> int:
        return len(self.data) - self.pos
    
    def tell(self) -> int:
        return self.pos
    
    def seek(self, offset: int, whence: int = 0):
        if whence == 0:
            self.pos = offset
        elif whence == 1:
            self.pos += offset
        elif whence == 2:
            self.pos = len(self.data) + offset
        else:
            raise ValueError("Invalid whence")
        if self.pos < 0:
            self.pos = 0
        if self.pos > len(self.data):
            self.pos = len(self.data)
    
    def align(self, alignment: int = 4):
        """Align position to the specified byte boundary."""
        self.pos = (self.pos + alignment - 1) & ~(alignment - 1)
        return self
    
    def read_bytes(self, n: int) -> bytes:
        if n < 0:
            raise ValueError(f"Cannot read {n} bytes")
        end = self.pos + n
        if end > len(self.data):
            raise EOFError(f"Cannot read {n} bytes at {self.pos}, only {self.remaining()} available")
        result = self.data[self.pos:end]
        self.pos = end
        return result
    
    def read_u8(self) -> int:
        return self.read_bytes(1)[0]
    
    def read_i8(self) -> int:
        b = self.read_u8()
        return b if b < 0x80 else b - 0x100
    
    def read_u16(self) -> int:
        return struct.unpack(self.endian + 'H', self.read_bytes(2))[0]
    
    def read_i16(self) -> int:
        return struct.unpack(self.endian + 'h', self.read_bytes(2))[0]
    
    def read_u24(self) -> int:
        b = self.read_bytes(3)
        return (b[0] | b[1] << 8 | b[2] << 16)
    
    def read_u32(self) -> int:
        return struct.unpack(self.endian + 'I', self.read_bytes(4))[0]
    
    def read_i32(self) -> int:
        return struct.unpack(self.endian + 'i', self.read_bytes(4))[0]
    
    def read_u64(self) -> int:
        return struct.unpack(self.endian + 'Q', self.read_bytes(8))[0]
    
    def read_i64(self) -> int:
        return struct.unpack(self.endian + 'q', self.read_bytes(8))[0]
    
    def read_float(self) -> float:
        return struct.unpack(self.endian + 'f', self.read_bytes(4))[0]
    
    def read_double(self) -> float:
        return struct.unpack(self.endian + 'd', self.read_bytes(8))[0]
    
    def read_cstring(self) -> str:
        """Read a null-terminated string."""
        end = self.pos
        while end < len(self.data) and self.data[end] != 0:
            end += 1
        result = self.data[self.pos:end].decode('utf-8', errors='replace')
        self.pos = end + 1  # skip null terminator
        return result
    
    def read_al4string(self) -> str:
        """Read a string prefixed with its length (4 bytes)."""
        length = self.read_u32()
        return self.read_bytes(length).decode('utf-8', errors='replace')
    
    def read_bool(self) -> bool:
        return self.read_u8() != 0
    
    def subreader(self, size: int) -> 'Reader':
        """Create a sub-reader for a portion of the data."""
        return Reader(self.data[self.pos:self.pos + size], self.endian)
    
    def at_end(self) -> bool:
        return self.pos >= len(self.data)


# ============================================================
# LZ4 Block Decompressor (pure Python)
# ============================================================

def lz4_decompress_block(compressed: bytes, uncompressed_size: int) -> bytes:
    """
    Decompress an LZ4-compressed block.
    LZ4 block format: sequences of literals and matches.
    Each sequence starts with a token byte:
      - bits 7:4 = literal length (0-15)
      - bits 3:0 = match length offset (0-15, actual match length = offset + 4)
    If literal length is 15, additional bytes follow (each adding 255) until a non-255 byte.
    If match length offset is 15, additional bytes follow similarly.
    Match offset is a 16-bit little-endian value.
    """
    if not compressed:
        return b''
    
    output = bytearray()
    pos = 0
    end = len(compressed)
    out_pos = 0
    
    while pos < end:
        token = compressed[pos]
        pos += 1
        
        # Literal length
        lit_len = token >> 4
        if lit_len == 15:
            while True:
                if pos >= end:
                    break
                b = compressed[pos]
                pos += 1
                lit_len += b
                if b != 255:
                    break
        
        # Copy literals
        if lit_len > 0:
            lit_end = pos + lit_len
            if lit_end > end:
                lit_end = end
            output.extend(compressed[pos:lit_end])
            pos = lit_end
            out_pos = len(output)
        
        if pos >= end:
            break
        
        # Match offset (16-bit LE)
        offset = compressed[pos] | (compressed[pos + 1] << 8)
        pos += 2
        
        # Match length
        match_len = (token & 0x0F) + 4
        if match_len == 19:
            while True:
                if pos >= end:
                    break
                b = compressed[pos]
                pos += 1
                match_len += b
                if b != 255:
                    break
        
        if offset == 0:
            break
        
        # Copy match
        start = out_pos - offset
        for i in range(match_len):
            output.append(output[start + i])
        out_pos = len(output)
    
    result = bytes(output)
    if len(result) != uncompressed_size:
        # Try to pad or truncate
        if len(result) < uncompressed_size:
            result += b'\x00' * (uncompressed_size - len(result))
        else:
            result = result[:uncompressed_size]
    return result


# ============================================================
# PNG Encoder
# ============================================================

def _png_crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def _png_pack(chunk_type: bytes, data: bytes) -> bytes:
    length = len(data)
    crc = _png_crc32(chunk_type + data)
    return struct.pack('>I', length) + chunk_type + data + struct.pack('>I', crc)


def write_png(path: str, width: int, height: int, data: bytes, row_stride: int = 0) -> None:
    """
    Write RGBA8 data to a PNG file.
    data: byte array of RGBA pixels, row-major, top-to-bottom
    row_stride: bytes per row (0 = width * 4)
    """
    if row_stride == 0:
        row_stride = width * 4
    
    # PNG signature
    signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr = _png_pack(b'IHDR', ihdr_data)
    
    # Filter and compress image data
    filtered = bytearray()
    for y in range(height):
        filtered.append(0)  # filter type 0 (none)
        row_start = y * row_stride
        row = data[row_start:row_start + width * 4]
        filtered.extend(row)
    
    compressed = zlib.compress(filtered, level=9)
    idat = _png_pack(b'IDAT', compressed)
    
    # IEND chunk
    iend = _png_pack(b'IEND', b'')
    
    with open(path, 'wb') as f:
        f.write(signature)
        f.write(ihdr)
        f.write(idat)
        f.write(iend)


# ============================================================
# Hashing
# ============================================================

def fnv1a_32(data: bytes) -> int:
    """FNV-1a 32-bit hash (used by Unity for script hashes)."""
    hash_val = 0x811C9DC5
    for byte in data:
        hash_val ^= byte
        hash_val = (hash_val * 0x01000193) & 0xFFFFFFFF
    return hash_val


def fnv1a_64(data: bytes) -> int:
    """FNV-1a 64-bit hash."""
    hash_val = 0xCBF29CE484222325
    for byte in data:
        hash_val ^= byte
        hash_val = (hash_val * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return hash_val


# ============================================================
# Compression helpers
# ============================================================

COMPRESSION_NONE = 0
COMPRESSION_LZMA = 1
COMPRESSION_LZ4 = 2
COMPRESSION_LZ4HC = 3


def decompress_data(data: bytes, compression_type: int, uncompressed_size: int) -> bytes:
    """Decompress data based on compression type."""
    if compression_type == COMPRESSION_NONE:
        return data
    elif compression_type == COMPRESSION_LZ4 or compression_type == COMPRESSION_LZ4HC:
        return lz4_decompress_block(data, uncompressed_size)
    elif compression_type == COMPRESSION_LZMA:
        # Unity uses LZMA with FORMAT_ALONE (5-byte properties + 8-byte size header)
        try:
            # LZMA alone format: properties (1 byte) + uncompressed size (8 bytes LE) + compressed data
            if len(data) >= 9:
                props = data[0]
                uncompressed_size_check = struct.unpack('<Q', data[1:9])[0]
                compressed_data = data[9:]
                decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                result = decompressor.decompress(compressed_data)
                if len(result) != uncompressed_size:
                    result = result[:uncompressed_size]
                return result
            else:
                # Try raw LZMA
                return lzma.decompress(data)
        except Exception:
            # Fallback: try with properties
            try:
                return lzma.decompress(data, format=lzma.FORMAT_ALONE)
            except Exception:
                return data
    else:
        return data


# ============================================================
# Human-readable size
# ============================================================

def human_size(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size) < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
