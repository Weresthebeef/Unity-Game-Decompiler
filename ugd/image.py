"""PNG and BMP image writers."""
import struct
import zlib


def _crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    length = len(data)
    crc = _crc32(chunk_type + data)
    return struct.pack('>I', length) + chunk_type + data + struct.pack('>I', crc)


def write_png(path: str, width: int, height: int, rgba_data: bytes, row_stride: int = 0) -> None:
    """
    Write RGBA8 image data to PNG file.
    
    Args:
        path: Output file path
        width: Image width in pixels
        height: Image height in pixels
        rgba_data: Byte array of RGBA pixels (4 bytes per pixel), row-major, top-to-bottom
        row_stride: Bytes per row (0 = width * 4)
    """
    if row_stride == 0:
        row_stride = width * 4
    
    # PNG signature
    signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR: width, height, 8-bit color, 6=RGBA, 0=deflate, 0=none, 0=none
    ihdr = _png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
    
    # Filter and compress
    filtered = bytearray()
    for y in range(height):
        filtered.append(0)  # filter type 0 (none)
        start = y * row_stride
        end = start + width * 4
        filtered.extend(rgba_data[start:end])
    
    compressed = zlib.compress(bytes(filtered), level=9)
    idat = _png_chunk(b'IDAT', compressed)
    iend = _png_chunk(b'IEND', b'')
    
    with open(path, 'wb') as f:
        f.write(signature)
        f.write(ihdr)
        f.write(idat)
        f.write(iend)


def write_bmp(path: str, width: int, height: int, rgba_data: bytes, row_stride: int = 0) -> None:
    """
    Write RGBA8 image data to BMP file (24-bit BGR + 1-bit alpha not supported, converts to 24-bit).
    BMP is simpler fallback if PNG fails.
    """
    if row_stride == 0:
        row_stride = width * 4
    
    # BMP header (14 bytes) + DIB header (40 bytes for BITMAPINFOHEADER)
    file_size = 54 + height * ((width * 3 + 3) & ~3)  # 24-bit BGR, padded to 4-byte boundary
    
    # BMP file header
    bf_type = b'BM'
    bf_size = struct.pack('<I', file_size)
    bf_reserved = struct.pack('<I', 0)
    bf_off_bits = struct.pack('<I', 54)
    
    # DIB header (BITMAPINFOHEADER)
    bi_size = struct.pack('<I', 40)
    bi_width = struct.pack('<i', width)
    bi_height = struct.pack('<i', height)  # positive = bottom-up
    bi_planes = struct.pack('<H', 1)
    bi_bit_count = struct.pack('<H', 24)  # 24 bits per pixel
    bi_compression = struct.pack('<I', 0)  # BI_RGB
    bi_size_image = struct.pack('<I', 0)
    bi_x_pels_per_meter = struct.pack('<i', 0)
    bi_y_pels_per_meter = struct.pack('<i', 0)
    bi_clr_used = struct.pack('<I', 0)
    bi_clr_important = struct.pack('<I', 0)
    
    header = (bf_type + bf_size + bf_reserved + bf_off_bits +
             bi_size + bi_width + bi_height + bi_planes + bi_bit_count +
             bi_compression + bi_size_image + bi_x_pels_per_meter + bi_y_pels_per_meter +
             bi_clr_used + bi_clr_important)
    
    # Row size with padding to 4-byte boundary
    row_size = (width * 3 + 3) & ~3
    padding = row_size - width * 3
    
    with open(path, 'wb') as f:
        f.write(header)
        
        for y in range(height):
            row_start = y * row_stride
            for x in range(width):
                idx = row_start + x * 4
                # Convert RGBA to BGR
                b = rgba_data[idx]
                g = rgba_data[idx + 1]
                r = rgba_data[idx + 2]
                f.write(bytes([b, g, r]))
            f.write(b'\x00' * padding)
