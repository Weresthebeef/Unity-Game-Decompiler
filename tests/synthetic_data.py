# Test data for self-tests
# From-scratch implementation - NO stolen code
# MIT License - Copyright (c) 2026 Gc.idk

"""
Synthetic test data generators for the Unity Game Decompiler self-tests.

This module creates realistic synthetic Unity data files for testing:
- Serialized files (.assets)
- UnityFS bundles (.unity3d)
- Mono assemblies (.dll)
- IL2CPP metadata (global-metadata.dat)

All data is generated from scratch based on the file format specifications.
"""

import struct
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def create_synthetic_serialized_file(version=19, endian='<', objects_count=10):
    """
    Create a synthetic Unity serialized file (.assets).
    
    Args:
        version: Unity version for the file format
        endian: Endianness ('<' for little, '>' for big)
        objects_count: Number of objects to include
    
    Returns:
        bytes: The serialized file data
    """
    # Header structure (20 bytes):
    # m_MetadataSize: uint32
    # m_FileSize: uint64
    # m_DataOffset: uint32
    # m_Endianess: uint8
    # m_Reserved: uint8[3]
    
    metadata_size = 0
    data_offset = 20  # Right after header
    
    # For simplicity, we'll create a minimal file
    # In a real implementation, we'd need proper metadata and object data
    
    header = struct.pack(
        endian + 'IQI',
        metadata_size,
        0,  # file_size - will be calculated later
        data_offset
    )
    
    # Endianness and reserved
    header += struct.pack(endian + 'c', endian.encode('ascii'))
    header += b'\x00\x00\x00'
    
    # For now, return just the header
    # A full implementation would add:
    # - Type tree
    # - Global type index
    # - Objects
    # - Externals
    # - Preloads
    
    return header


def create_synthetic_unityfs_bundle(entries=3):
    """
    Create a synthetic UnityFS bundle (.unity3d).
    
    Args:
        entries: Number of entries to include
    
    Returns:
        bytes: The UnityFS bundle data
    """
    # UnityFS header (24 bytes):
    # m_Signature: char[6] - "UnityFS"
    # m_Version: uint32
    # m_PlayerVersion: char[24]
    # m_EngineVersion: char[24]
    
    signature = b'UnityFS'
    version = 4  # UnityFS version 4
    player_version = b'5.6.0f3\x00' + b'\x00' * 15  # Padded to 24 bytes
    engine_version = b'2019.4.0f1\x00' + b'\x00' * 13  # Padded to 24 bytes
    
    header = signature
    header += struct.pack('<I', version)
    header += player_version
    header += engine_version
    
    # For now, return just the header
    # A full implementation would add:
    # - Bundle size
    # - Compression type
    # - Block info
    # - Directory info
    # - File entries
    
    return header


def create_synthetic_mono_assembly(methods_count=5):
    """
    Create a synthetic Mono assembly (.dll) with simple methods.
    
    Args:
        methods_count: Number of methods to include
    
    Returns:
        bytes: The PE/COFF file data
    """
    # This would create a minimal PE file with CLI metadata
    # For testing purposes, we'll create a very basic structure
    
    # DOS header
    dos_header = struct.pack('<H58s', 0x5A4D, b'\x00' * 58)  # MZ
    
    # PE offset at 0x3C
    pe_offset = len(dos_header)
    dos_header = dos_header[:0x3C] + struct.pack('<I', pe_offset) + dos_header[0x3C+4:]
    
    # PE signature
    pe_signature = b'PE\x00\x00'
    
    # COFF header
    coff_header = struct.pack('<HHIHHHH',
        0x014C,  # Machine (x86)
        1,       # Number of sections
        0,       # TimeDateStamp
        0,       # PointerToSymbolTable
        0,       # NumberOfSymbols
        0xE0,    # SizeOfOptionalHeader
        0x10F    # Characteristics
    )
    
    # Combine
    pe_data = dos_header + pe_signature + coff_header
    
    # For now, return this basic structure
    # A full implementation would add:
    # - Optional header
    # - Section headers
    # - Section data
    # - CLI metadata tables
    # - Method bodies
    
    return pe_data


def create_synthetic_il2cpp_metadata(types_count=10, methods_count=20):
    """
    Create a synthetic IL2CPP global-metadata.dat file.
    
    Args:
        types_count: Number of type definitions
        methods_count: Number of method definitions
    
    Returns:
        bytes: The metadata file data
    """
    # IL2CPP metadata header (24 bytes for v24+):
    # m_Magic: uint32 - 0x6D657461 ("meta")
    # m_Version: uint32
    # m_StringOffset: uint32
    # m_StringSize: uint32
    # m_TableOffsets: various
    
    magic = 0x6D657461  # "meta"
    version = 24  # Version 24
    
    header = struct.pack('<II', magic, version)
    
    # For now, return just the header
    # A full implementation would add:
    # - String literal data
    # - Type definitions
    # - Method definitions
    # - Field definitions
    # - Parameter definitions
    # - And more...
    
    return header


def create_synthetic_texture(width=4, height=4, format='RGBA32'):
    """
    Create a synthetic texture in Unity format.
    
    Args:
        width: Texture width
        height: Texture height
        format: Texture format (RGBA32, RGB24, etc.)
    
    Returns:
        bytes: The texture data
    """
    if format == 'RGBA32':
        # 4 bytes per pixel: R, G, B, A
        data = bytearray(width * height * 4)
        for i in range(width * height):
            offset = i * 4
            # Simple gradient
            r = int((i % width) / width * 255)
            g = int((i // width) / height * 255)
            b = 128
            a = 255
            data[offset] = r
            data[offset+1] = g
            data[offset+2] = b
            data[offset+3] = a
        return bytes(data)
    
    elif format == 'RGB24':
        # 3 bytes per pixel: R, G, B
        data = bytearray(width * height * 3)
        for i in range(width * height):
            offset = i * 3
            r = int((i % width) / width * 255)
            g = int((i // width) / height * 255)
            b = 128
            data[offset] = r
            data[offset+1] = g
            data[offset+2] = b
        return bytes(data)
    
    else:
        raise ValueError(f"Unsupported texture format: {format}")


def create_synthetic_scene():
    """
    Create a synthetic Unity scene file.
    
    Returns:
        bytes: The scene data
    """
    # A scene is just a serialized file with specific content
    # For now, return an empty serialized file header
    return create_synthetic_serialized_file()


def create_synthetic_prefab():
    """
    Create a synthetic Unity prefab file.
    
    Returns:
        bytes: The prefab data
    """
    # A prefab is also a serialized file
    return create_synthetic_serialized_file()


def create_test_game_structure(output_dir):
    """
    Create a complete synthetic game structure for testing.
    
    Args:
        output_dir: Directory to create the structure in
    
    Returns:
        dict: Information about the created structure
    """
    info = {
        'directories': [],
        'files': []
    }
    
    # Create directory structure
    dirs = [
        os.path.join(output_dir, 'Assets'),
        os.path.join(output_dir, 'Assets', 'Scripts'),
        os.path.join(output_dir, 'Assets', 'Textures'),
        os.path.join(output_dir, 'Assets', 'Scenes'),
        os.path.join(output_dir, 'Assets', 'Prefabs'),
        os.path.join(output_dir, 'Assets', 'Plugins'),
        os.path.join(output_dir, 'ProjectSettings'),
    ]
    
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        info['directories'].append(d)
    
    # Create synthetic files
    files = {
        'Assets/Scripts/TestScript.cs': b'// Test script\npublic class TestScript : MonoBehaviour { }',
        'Assets/Textures/test.png': create_synthetic_texture(),
        'Assets/Scenes/test.unity': create_synthetic_scene(),
        'Assets/Prefabs/test.prefab': create_synthetic_prefab(),
        'ProjectSettings/ProjectVersion.txt': b'm_EditorVersion: 2019.4.0f1\n',
    }
    
    for file_path, content in files.items():
        full_path = os.path.join(output_dir, file_path)
        with open(full_path, 'wb') as f:
            f.write(content)
        info['files'].append(full_path)
    
    return info


if __name__ == '__main__':
    # Demo: create a test game structure
    import tempfile
    import shutil
    
    print("Creating synthetic test game structure...")
    
    tmpdir = tempfile.mkdtemp()
    try:
        info = create_test_game_structure(tmpdir)
        print(f"Created {len(info['directories'])} directories")
        print(f"Created {len(info['files'])} files")
        print(f"Test structure at: {tmpdir}")
    finally:
        shutil.rmtree(tmpdir)
        print("Cleaned up temporary directory")
