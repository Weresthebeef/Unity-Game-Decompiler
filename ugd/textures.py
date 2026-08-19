"""Texture format decoders for Unity textures."""
import struct
from typing import Optional, Tuple
from .utils import Reader
from .image import write_png


# ============================================================
# DXT/BCn Decoders
# ============================================================

def _dxt1_decompress_block(block: bytes, x: int, y: int, width: int, rgba: bytearray) -> None:
    """Decompress a single DXT1 (BC1) block."""
    c0 = struct.unpack('<H', block[0:2])[0]
    c1 = struct.unpack('<H', block[2:4])[0]
    
    # Unpack 565 colors
    r0 = (c0 >> 11) & 0x1F
    g0 = (c0 >> 5) & 0x3F
    b0 = c0 & 0x1F
    
    r1 = (c1 >> 11) & 0x1F
    g1 = (c1 >> 5) & 0x3F
    b1 = c1 & 0x1F
    
    # Scale to 8 bits
    r0 = (r0 * 255 + 15) // 31
    g0 = (g0 * 255 + 31) // 63
    b0 = (b0 * 255 + 15) // 31
    
    r1 = (r1 * 255 + 15) // 31
    g1 = (g1 * 255 + 31) // 63
    b1 = (b1 * 255 + 15) // 31
    
    # Generate color table
    if c0 <= c1:
        # 1-bit alpha
        colors = [
            (r0, g0, b0, 255),
            (r1, g1, b1, 255),
            ((2 * r0 + r1 + 1) // 3, (2 * g0 + g1 + 1) // 3, (2 * b0 + b1 + 1) // 3, 255),
            ((r0 + 2 * r1 + 1) // 3, (g0 + 2 * g1 + 1) // 3, (b0 + 2 * b1 + 1) // 3, 255),
        ]
    else:
        # Transparent
        colors = [
            (r0, g0, b0, 255),
            (r1, g1, b1, 255),
            ((2 * r0 + r1 + 1) // 3, (2 * g0 + g1 + 1) // 3, (2 * b0 + b1 + 1) // 3, 255),
            ((r0 + 2 * r1 + 1) // 3, (g0 + 2 * g1 + 1) // 3, (b0 + 2 * b1 + 1) // 3, 0),
        ]
    
    # Decode indices
    for j in range(4):
        for i in range(4):
            idx = (block[4 + j] >> (2 * (3 - i))) & 0x03
            color = colors[idx]
            px = x + i
            py = y + j
            if px < width:
                offset = (py * width + px) * 4
                rgba[offset] = color[0]
                rgba[offset + 1] = color[1]
                rgba[offset + 2] = color[2]
                rgba[offset + 3] = color[3]


def _dxt5_decompress_block(block: bytes, x: int, y: int, width: int, rgba: bytearray) -> None:
    """Decompress a single DXT5 (BC3) block."""
    # Alpha values
    a0 = block[0]
    a1 = block[1]
    
    alpha_table = [0] * 8
    alpha_table[0] = a0
    alpha_table[1] = a1
    if a0 <= a1:
        for i in range(2, 8):
            alpha_table[i] = ((8 - i) * a0 + (i - 1) * a1 + 3) // 7
    else:
        for i in range(2, 6):
            alpha_table[i] = ((6 - i) * a0 + (i - 1) * a1 + 3) // 5
        alpha_table[6] = 0
        alpha_table[7] = 255
    
    # Color data (same as DXT1)
    c0 = struct.unpack('<H', block[8:10])[0]
    c1 = struct.unpack('<H', block[10:12])[0]
    
    r0 = (c0 >> 11) & 0x1F
    g0 = (c0 >> 5) & 0x3F
    b0 = c0 & 0x1F
    
    r1 = (c1 >> 11) & 0x1F
    g1 = (c1 >> 5) & 0x3F
    b1 = c1 & 0x1F
    
    r0 = (r0 * 255 + 15) // 31
    g0 = (g0 * 255 + 31) // 63
    b0 = (b0 * 255 + 15) // 31
    
    r1 = (r1 * 255 + 15) // 31
    g1 = (g1 * 255 + 31) // 63
    b1 = (b1 * 255 + 15) // 31
    
    colors = [
        (r0, g0, b0),
        (r1, g1, b1),
        ((2 * r0 + r1 + 1) // 3, (2 * g0 + g1 + 1) // 3, (2 * b0 + b1 + 1) // 3),
        ((r0 + 2 * r1 + 1) // 3, (g0 + 2 * g1 + 1) // 3, (b0 + 2 * b1 + 1) // 3),
    ]
    
    # Decode alpha indices (3-bit)
    alpha_indices = block[2:8]
    # Decode color indices (2-bit)
    color_indices = block[12:16]
    
    for j in range(4):
        for i in range(4):
            # Alpha index (3 bits)
            ai = ((alpha_indices[j] >> (3 * (3 - i))) & 0x07)
            # Color index (2 bits)
            ci = ((color_indices[j] >> (2 * (3 - i))) & 0x03)
            
            px = x + i
            py = y + j
            if px < width:
                offset = (py * width + px) * 4
                rgba[offset] = colors[ci][0]
                rgba[offset + 1] = colors[ci][1]
                rgba[offset + 2] = colors[ci][2]
                rgba[offset + 3] = alpha_table[ai]


def decode_dxt1(data: bytes, width: int, height: int) -> bytes:
    """Decode DXT1 (BC1) texture data to RGBA8."""
    block_size = 8
    block_w = 4
    block_h = 4
    
    rgba = bytearray(width * height * 4)
    
    for y in range(0, height, block_h):
        for x in range(0, width, block_w):
            block_start = ((y // block_h) * (width // block_w) + (x // block_w)) * block_size
            block_data = data[block_start:block_start + block_size]
            _dxt1_decompress_block(block_data, x, y, width, rgba)
    
    return bytes(rgba)


def decode_dxt5(data: bytes, width: int, height: int) -> bytes:
    """Decode DXT5 (BC3) texture data to RGBA8."""
    block_size = 16
    block_w = 4
    block_h = 4
    
    rgba = bytearray(width * height * 4)
    
    for y in range(0, height, block_h):
        for x in range(0, width, block_w):
            block_start = ((y // block_h) * (width // block_w) + (x // block_w)) * block_size
            block_data = data[block_start:block_start + block_size]
            _dxt5_decompress_block(block_data, x, y, width, rgba)
    
    return bytes(rgba)


# ============================================================
# ETC1/ETC2 Decoders (per Khronos ETC2 specification)
# ============================================================

# Modifier tables for individual/differential modes (ETC1 + ETC2).
# Per spec, pixel index -> modifier: 0 -> +a, 1 -> +b, 2 -> -a, 3 -> -b.
ETC2_MODIFIER_TABLES = [
    (2, 8, -2, -8),
    (5, 17, -5, -17),
    (9, 29, -9, -29),
    (13, 42, -13, -42),
    (18, 60, -18, -60),
    (24, 80, -24, -80),
    (33, 106, -33, -106),
    (47, 183, -47, -183),
]

# Modifier tables for non-opaque punchthrough-alpha blocks (RGBA1):
# per spec, pixel indices 0 and 2 map to 0 instead of +/-a.
ETC2_PUNCHTHROUGH_MODIFIER_TABLES = [
    (0, 8, 0, -8),
    (0, 17, 0, -17),
    (0, 29, 0, -29),
    (0, 42, 0, -42),
    (0, 60, 0, -60),
    (0, 80, 0, -80),
    (0, 106, 0, -106),
    (0, 183, 0, -183),
]

# Distance table for T and H modes.
ETC2_DISTANCE_TABLE = (3, 6, 11, 16, 23, 32, 41, 64)

# Modifier tables for the alpha channel (EAC, 16 tables of 8 values).
ETC2_ALPHA_MODIFIER_TABLES = [
    (-3, -6, -9, -15, 2, 5, 8, 14),
    (-3, -7, -10, -13, 2, 6, 9, 12),
    (-2, -5, -8, -13, 1, 4, 7, 12),
    (-2, -4, -6, -13, 1, 3, 5, 12),
    (-3, -6, -8, -12, 2, 5, 7, 11),
    (-3, -7, -9, -11, 2, 6, 8, 10),
    (-4, -7, -8, -11, 3, 6, 7, 10),
    (-3, -5, -8, -11, 2, 4, 7, 10),
    (-2, -6, -8, -10, 1, 5, 7, 9),
    (-2, -5, -8, -10, 1, 4, 7, 9),
    (-2, -4, -8, -10, 1, 3, 7, 9),
    (-2, -5, -7, -10, 1, 4, 6, 9),
    (-3, -4, -7, -10, 2, 3, 6, 9),
    (-1, -2, -3, -10, 0, 1, 2, 9),
    (-4, -6, -8, -9, 3, 5, 7, 8),
    (-3, -5, -7, -9, 2, 4, 6, 8),
]


def _extend4to8(v: int) -> int:
    """Extend a 4-bit value to 8 bits by replicating the high nibble."""
    return (v << 4) | v


def _extend5to8(v: int) -> int:
    """Extend a 5-bit value to 8 bits by replicating the top 3 bits."""
    return (v << 3) | (v >> 2)


def _extend6to8(v: int) -> int:
    """Extend a 6-bit value to 8 bits by replicating the top 2 bits."""
    return (v << 2) | (v >> 4)


def _extend7to8(v: int) -> int:
    """Extend a 7-bit value to 8 bits by replicating the top bit."""
    return (v << 1) | (v >> 6)


def _pixel_index(word: int, col: int, row: int) -> int:
    """
    Extract the 2-bit pixel index for pixel (col, row) within a 4x4 block.
    Per spec: pixels are addressed column-major (pixel a = (0,0), b = (0,1),
    c = (0,2), d = (0,3), e = (1,0), ..., p = (3,3)); p = 4*col + row,
    with the index MSB at bit 16+p and LSB at bit p.
    """
    p = col * 4 + row
    msb = (word >> (16 + p)) & 1
    lsb = (word >> p) & 1
    return (msb << 1) | lsb


def _clamp255(v: int) -> int:
    if v < 0:
        return 0
    if v > 255:
        return 255
    return v


def _write_block_pixel(rgba: bytearray, width: int, px: int, py: int,
                       r: int, g: int, b: int, a: int) -> None:
    """Write one decoded pixel, skipping columns beyond the image width."""
    if px < width:
        offset = (py * width + px) * 4
        rgba[offset] = r
        rgba[offset + 1] = g
        rgba[offset + 2] = b
        rgba[offset + 3] = a


def _decode_etc2_block(block: bytes, x: int, y: int, width: int,
                       rgba: bytearray, punchthrough: bool = False) -> None:
    """
    Decode one 8-byte ETC2 (or ETC1) block to RGBA.

    Bit layout per the Khronos ETC2 specification (big-endian 64-bit word,
    byte 0 = bits 63-56):
      individual:   R=63-60 R2=59-56 G=55-52 G2=51-48 B=47-44 B2=43-40
                    cw1=39-37 cw2=36-34 D=33 flip=32
      differential: R=63-59 Rd=58-56 G=55-51 Gd=50-48 B=47-43 Bd=42-40
                    cw1=39-37 cw2=36-34 D=33 flip=32

    For RGBA1 (punchthrough alpha) there is no individual mode: the D bit
    marks opaque (1) vs punchthrough-capable (0) blocks, and the
    differential/T/H/planar mode selection always applies. In
    punchthrough-capable blocks pixel index 2 is transparent and the
    differential modifier tables are replaced by the non-opaque variants.
    """
    word = int.from_bytes(block[:8], 'big')

    diff = (word >> 33) & 1
    flip = (word >> 32) & 1
    cw1 = (word >> 37) & 0x07
    cw2 = (word >> 34) & 0x07

    if punchthrough:
        # RGBA1: no individual mode; D bit = opaque flag
        non_opaque = diff == 0
        mod1 = ETC2_PUNCHTHROUGH_MODIFIER_TABLES[cw1]
        mod2 = ETC2_PUNCHTHROUGH_MODIFIER_TABLES[cw2]
    else:
        if diff == 0:
            # Individual mode
            r1 = (word >> 60) & 0x0F
            r2 = (word >> 56) & 0x0F
            g1 = (word >> 52) & 0x0F
            g2 = (word >> 48) & 0x0F
            b1 = (word >> 44) & 0x0F
            b2 = (word >> 40) & 0x0F
            mod1 = ETC2_MODIFIER_TABLES[cw1]
            mod2 = ETC2_MODIFIER_TABLES[cw2]

            base1 = (_extend4to8(r1), _extend4to8(g1), _extend4to8(b1))
            base2 = (_extend4to8(r2), _extend4to8(g2), _extend4to8(b2))

            for j in range(4):
                for i in range(4):
                    idx = _pixel_index(word, i, j)
                    # Sub-block selection: flip=0 -> left/right halves,
                    # flip=1 -> top/bottom halves
                    if not flip:
                        sub = 0 if i < 2 else 1
                    else:
                        sub = 0 if j < 2 else 1
                    base = base1 if sub == 0 else base2
                    mod = mod1 if sub == 0 else mod2
                    # Index -> modifier: 0:+a 1:+b 2:-a 3:-b
                    modifier = mod[idx]
                    _write_block_pixel(rgba, width, x + i, y + j,
                                       _clamp255(base[0] + modifier),
                                       _clamp255(base[1] + modifier),
                                       _clamp255(base[2] + modifier), 255)
            return
        mod1 = ETC2_MODIFIER_TABLES[cw1]
        mod2 = ETC2_MODIFIER_TABLES[cw2]

    # Differential base color fields (also used for T/H/planar mode
    # selection, and for RGBA1 blocks regardless of the D bit)
    r = (word >> 59) & 0x1F
    rd = ((word >> 56) & 0x07)
    if rd & 0x04:
        rd -= 8
    g = (word >> 51) & 0x1F
    gd = ((word >> 48) & 0x07)
    if gd & 0x04:
        gd -= 8
    b = (word >> 43) & 0x1F
    bd = ((word >> 40) & 0x07)
    if bd & 0x04:
        bd -= 8

    r2 = r + rd
    g2 = g + gd
    b2 = b + bd

    transparent = punchthrough and non_opaque

    if r2 < 0 or r2 > 31:
        # T mode
        r1 = (((word >> 59) & 0x03) << 2) | ((word >> 56) & 0x03)
        g1 = (word >> 52) & 0x0F
        b1 = (word >> 48) & 0x0F
        r2c = (word >> 44) & 0x0F
        g2c = (word >> 40) & 0x0F
        b2c = (word >> 36) & 0x0F
        da = (word >> 34) & 0x03
        db = (word >> 32) & 1
        d = ETC2_DISTANCE_TABLE[(da << 1) | db]

        base1 = (_extend4to8(r1), _extend4to8(g1), _extend4to8(b1))
        base2 = (_extend4to8(r2c), _extend4to8(g2c), _extend4to8(b2c))
        paints = [
            base1,
            (_clamp255(base2[0] + d), _clamp255(base2[1] + d), _clamp255(base2[2] + d)),
            base2,
            (_clamp255(base2[0] - d), _clamp255(base2[1] - d), _clamp255(base2[2] - d)),
        ]

        for j in range(4):
            for i in range(4):
                idx = _pixel_index(word, i, j)
                color = paints[idx]
                if transparent and idx == 2:
                    _write_block_pixel(rgba, width, x + i, y + j, 0, 0, 0, 0)
                else:
                    _write_block_pixel(rgba, width, x + i, y + j,
                                       color[0], color[1], color[2], 255)
        return

    if g2 < 0 or g2 > 31:
        # H mode
        r1 = (word >> 59) & 0x0F
        g1 = (((word >> 56) & 0x07) << 1) | ((word >> 52) & 1)
        b1 = (((word >> 51) & 1) << 3) | (((word >> 48) & 0x03) << 1) | ((word >> 47) & 1)
        r2c = (word >> 43) & 0x0F
        g2c = (((word >> 40) & 0x07) << 1) | ((word >> 39) & 1)
        b2c = (word >> 35) & 0x0F
        da = (word >> 34) & 1
        db = (word >> 32) & 1

        base1 = (_extend4to8(r1), _extend4to8(g1), _extend4to8(b1))
        base2 = (_extend4to8(r2c), _extend4to8(g2c), _extend4to8(b2c))
        val1 = (r1 << 16) | (g1 << 8) | b1
        val2 = (r2c << 16) | (g2c << 8) | b2c
        cmp_bit = 1 if val1 >= val2 else 0
        d = ETC2_DISTANCE_TABLE[(da << 2) | (db << 1) | cmp_bit]

        paints = [
            (_clamp255(base1[0] + d), _clamp255(base1[1] + d), _clamp255(base1[2] + d)),
            (_clamp255(base1[0] - d), _clamp255(base1[1] - d), _clamp255(base1[2] - d)),
            (_clamp255(base2[0] + d), _clamp255(base2[1] + d), _clamp255(base2[2] + d)),
            (_clamp255(base2[0] - d), _clamp255(base2[1] - d), _clamp255(base2[2] - d)),
        ]

        for j in range(4):
            for i in range(4):
                idx = _pixel_index(word, i, j)
                color = paints[idx]
                if transparent and idx == 2:
                    _write_block_pixel(rgba, width, x + i, y + j, 0, 0, 0, 0)
                else:
                    _write_block_pixel(rgba, width, x + i, y + j,
                                       color[0], color[1], color[2], 255)
        return

    if b2 < 0 or b2 > 31:
        # Planar mode
        pr = (word >> 57) & 0x3F
        pg = (((word >> 56) & 1) << 6) | ((word >> 49) & 0x3F)
        pb = (((word >> 48) & 1) << 5) | (((word >> 43) & 0x03) << 3) | (((word >> 39) & 0x07))
        rh = (((word >> 34) & 0x1F) << 1) | ((word >> 32) & 1)
        gh = (word >> 25) & 0x7F
        bh = (((word >> 24) & 1) << 5) | ((word >> 19) & 0x1F)
        rv = (((word >> 16) & 0x07) << 3) | ((word >> 13) & 0x07)
        gv = (((word >> 8) & 0x1F) << 2) | ((word >> 6) & 0x03)
        bv = word & 0x3F

        c0 = (_extend6to8(pr), _extend7to8(pg), _extend6to8(pb))
        ch = (_extend6to8(rh), _extend7to8(gh), _extend6to8(bh))
        cv = (_extend6to8(rv), _extend7to8(gv), _extend6to8(bv))

        for j in range(4):
            for i in range(4):
                px = x + i
                py = y + j
                if px < width:
                    offset = (py * width + px) * 4
                    rgba[offset] = _clamp255((i * (ch[0] - c0[0]) + j * (cv[0] - c0[0]) + 4 * c0[0] + 2) >> 2)
                    rgba[offset + 1] = _clamp255((i * (ch[1] - c0[1]) + j * (cv[1] - c0[1]) + 4 * c0[1] + 2) >> 2)
                    rgba[offset + 2] = _clamp255((i * (ch[2] - c0[2]) + j * (cv[2] - c0[2]) + 4 * c0[2] + 2) >> 2)
                    rgba[offset + 3] = 255
        return

    # Differential mode
    base1 = (_extend5to8(r), _extend5to8(g), _extend5to8(b))
    base2 = (_extend5to8(r2), _extend5to8(g2), _extend5to8(b2))

    for j in range(4):
        for i in range(4):
            idx = _pixel_index(word, i, j)
            if not flip:
                sub = 0 if i < 2 else 1
            else:
                sub = 0 if j < 2 else 1
            base = base1 if sub == 0 else base2
            mod = mod1 if sub == 0 else mod2
            modifier = mod[idx]
            if transparent and idx == 2:
                _write_block_pixel(rgba, width, x + i, y + j, 0, 0, 0, 0)
            else:
                _write_block_pixel(rgba, width, x + i, y + j,
                                   _clamp255(base[0] + modifier),
                                   _clamp255(base[1] + modifier),
                                   _clamp255(base[2] + modifier), 255)


def decode_etc2_rgb(data: bytes, width: int, height: int) -> bytes:
    """Decode ETC1/ETC2_RGB texture data to RGBA8 (8 bytes per 4x4 block)."""
    block_size = 8
    block_w = 4
    block_h = 4

    rgba = bytearray(width * height * 4)

    for y in range(0, height, block_h):
        for x in range(0, width, block_w):
            block_start = ((y // block_h) * (width // block_w) + (x // block_w)) * block_size
            block_data = data[block_start:block_start + block_size]
            _decode_etc2_block(block_data, x, y, width, rgba)

    return bytes(rgba)


def decode_etc2_rgba8(data: bytes, width: int, height: int) -> bytes:
    """
    Decode ETC2_RGBA8 texture data to RGBA8 (16 bytes per 4x4 block).
    Per spec: first 8 bytes = alpha channel (EAC), next 8 bytes = color.
    """
    block_size = 16
    block_w = 4
    block_h = 4

    rgba = bytearray(width * height * 4)

    for y in range(0, height, block_h):
        for x in range(0, width, block_w):
            block_start = ((y // block_h) * (width // block_w) + (x // block_w)) * block_size
            alpha_block = data[block_start:block_start + 8]
            color_block = data[block_start + 8:block_start + 16]

            _decode_etc2_block(color_block, x, y, width, rgba)

            # EAC alpha: 8-bit base codeword, 4-bit multiplier,
            # 4-bit table index, 16 3-bit pixel indices (MSB-first)
            base = alpha_block[0]
            multiplier = alpha_block[1] >> 4
            table_idx = alpha_block[1] & 0x0F
            table = ETC2_ALPHA_MODIFIER_TABLES[table_idx]

            alpha_word = int.from_bytes(alpha_block[2:8], 'big')
            for j in range(4):
                for i in range(4):
                    p = i * 4 + j
                    shift = 45 - 3 * p
                    idx = (alpha_word >> shift) & 0x07
                    a = _clamp255(base + table[idx] * multiplier)
                    px = x + i
                    py = y + j
                    if px < width:
                        offset = (py * width + px) * 4
                        rgba[offset + 3] = a

    return bytes(rgba)


def decode_etc2_rgba1(data: bytes, width: int, height: int) -> bytes:
    """Decode ETC2_RGBA1 (punchthrough alpha) texture data to RGBA8."""
    block_size = 8
    block_w = 4
    block_h = 4

    rgba = bytearray(width * height * 4)

    for y in range(0, height, block_h):
        for x in range(0, width, block_w):
            block_start = ((y // block_h) * (width // block_w) + (x // block_w)) * block_size
            block_data = data[block_start:block_start + block_size]
            _decode_etc2_block(block_data, x, y, width, rgba, punchthrough=True)

    return bytes(rgba)


# ============================================================
# RGBA Decoders
# ============================================================

def decode_rgba32(data: bytes, width: int, height: int) -> bytes:
    """Decode RGBA32 texture data."""
    # Already in RGBA8 format
    return data


def decode_rgb24(data: bytes, width: int, height: int) -> bytes:
    """Decode RGB24 texture data to RGBA8."""
    rgba = bytearray(width * height * 4)
    for i in range(width * height):
        rgba[i * 4] = data[i * 3]
        rgba[i * 4 + 1] = data[i * 3 + 1]
        rgba[i * 4 + 2] = data[i * 3 + 2]
        rgba[i * 4 + 3] = 255
    return bytes(rgba)


def decode_argb32(data: bytes, width: int, height: int) -> bytes:
    """Decode ARGB32 texture data to RGBA8."""
    rgba = bytearray(width * height * 4)
    for i in range(width * height):
        rgba[i * 4] = data[i * 4 + 1]  # R
        rgba[i * 4 + 1] = data[i * 4 + 2]  # G
        rgba[i * 4 + 2] = data[i * 4 + 3]  # B
        rgba[i * 4 + 3] = data[i * 4]      # A
    return bytes(rgba)


def decode_argb4444(data: bytes, width: int, height: int) -> bytes:
    """Decode ARGB4444 texture data to RGBA8."""
    rgba = bytearray(width * height * 4)
    for i in range(width * height):
        pixel = struct.unpack('<H', data[i * 2:i * 2 + 2])[0]
        a = (pixel >> 12) & 0x0F
        r = (pixel >> 8) & 0x0F
        g = (pixel >> 4) & 0x0F
        b = pixel & 0x0F
        
        rgba[i * 4] = (r * 17)  # 0, 17, 34, ..., 255
        rgba[i * 4 + 1] = (g * 17)
        rgba[i * 4 + 2] = (b * 17)
        rgba[i * 4 + 3] = (a * 17)
    return bytes(rgba)


def decode_rgb565(data: bytes, width: int, height: int) -> bytes:
    """Decode RGB565 texture data to RGBA8."""
    rgba = bytearray(width * height * 4)
    for i in range(width * height):
        pixel = struct.unpack('<H', data[i * 2:i * 2 + 2])[0]
        r = (pixel >> 11) & 0x1F
        g = (pixel >> 5) & 0x3F
        b = pixel & 0x1F
        
        rgba[i * 4] = (r * 255 + 15) // 31
        rgba[i * 4 + 1] = (g * 255 + 31) // 63
        rgba[i * 4 + 2] = (b * 255 + 15) // 31
        rgba[i * 4 + 3] = 255
    return bytes(rgba)


# ============================================================
# Texture Decoder Dispatcher
# ============================================================

TEXTURE_DECODERS = {
    0: decode_rgba32,  # Alpha8 - treat as grayscale
    1: decode_argb4444,
    2: decode_rgb24,
    3: decode_rgba32,
    4: decode_argb32,
    5: decode_rgb565,
    7: None,  # R16 - not implemented
    8: decode_dxt1,  # DXT1
    9: decode_dxt5,  # DXT5
    10: decode_rgba32,  # RGBA4444 - approximate
    11: decode_rgba32,  # BGRA32 - same as RGBA32
    26: decode_etc2_rgb,  # ETC_RGB4
    27: decode_etc2_rgb,  # ETC2_RGB
    28: decode_etc2_rgba1,  # ETC2_RGBA1
    29: decode_etc2_rgba8,  # ETC2_RGBA8
}


def decode_texture(data: bytes, format: int, width: int, height: int) -> Optional[bytes]:
    """
    Decode texture data to RGBA8 format.
    
    Args:
        data: Raw texture data
        format: Unity TextureFormat enum value
        width: Texture width
        height: Texture height
    
    Returns:
        RGBA8 byte array or None if format not supported
    """
    decoder = TEXTURE_DECODERS.get(format)
    if decoder is None:
        return None
    
    try:
        return decoder(data, width, height)
    except Exception as e:
        print(f"Error decoding texture format {format}: {e}")
        return None


def save_texture_as_png(data: bytes, format: int, width: int, height: int, output_path: str) -> bool:
    """
    Decode and save texture as PNG.
    
    Returns:
        True if successful, False otherwise
    """
    rgba_data = decode_texture(data, format, width, height)
    if rgba_data is None:
        return False
    
    try:
        write_png(output_path, width, height, rgba_data)
        return True
    except Exception as e:
        print(f"Error saving PNG: {e}")
        return False
