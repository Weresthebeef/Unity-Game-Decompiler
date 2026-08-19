# Unity Game Decompiler - Self Tests
# From-scratch implementation - NO stolen code
# MIT License - Copyright (c) 2026 Gc.idk

"""
Self-test suite for the Unity Game Decompiler.

Tests cover:
- Binary Reader utilities
- LZ4 block decompression
- FNV-1a hashing (official test vectors)
- PNG/BMP image writers
- Texture decoders (RGBA/RGB24/RGB565/DXT1/ETC1)
- Mono PE parsing
- IL disassembly
- Project reconstruction
- CLI detection logic
"""

import os
import sys
import struct
import tempfile
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ugd import utils
from ugd import image as ugd_image
from ugd import textures
from ugd import serialized
from ugd import unityfs
from ugd.mono import pe, il
from ugd.project import ProjectReconstructor


class TestReader(unittest.TestCase):
    """Test binary Reader functionality."""

    def test_basic(self):
        data = struct.pack('<I', 0xDEADBEEF)
        reader = utils.Reader(data)
        self.assertEqual(reader.read_u32(), 0xDEADBEEF)

    def test_endianness(self):
        data = struct.pack('>I', 0x12345678)
        reader = utils.Reader(data, endian='>')
        self.assertEqual(reader.read_u32(), 0x12345678)

        data_le = struct.pack('<I', 0x12345678)
        reader_le = utils.Reader(data_le, endian='<')
        self.assertEqual(reader_le.read_u32(), 0x12345678)

    def test_signed(self):
        data = struct.pack('<i', -42)
        reader = utils.Reader(data)
        self.assertEqual(reader.read_i32(), -42)

    def test_strings(self):
        data = b"Hello\x00World"
        reader = utils.Reader(data)
        self.assertEqual(reader.read_cstring(), "Hello")
        self.assertEqual(reader.read_cstring(), "World")

        data = struct.pack('<I', 5) + b"Hello"
        reader = utils.Reader(data)
        self.assertEqual(reader.read_al4string(), "Hello")

    def test_align(self):
        data = b'\x00' * 16
        reader = utils.Reader(data)
        reader.seek(5)
        reader.align(4)
        self.assertEqual(reader.tell(), 8)

    def test_eof_error(self):
        reader = utils.Reader(b'\x00\x00\x00')
        with self.assertRaises(EOFError):
            reader.read_u32()

    def test_u24(self):
        data = b'\x01\x02\x03'
        reader = utils.Reader(data)
        self.assertEqual(reader.read_u24(), 0x030201)

    def test_subreader(self):
        data = b'\x00\x00\x00\x00\x2a\x00\x00\x00'
        reader = utils.Reader(data)
        sub = reader.subreader(4)
        self.assertEqual(len(sub.data), 4)


class TestLZ4(unittest.TestCase):
    """Test LZ4 block decompression."""

    def test_empty(self):
        self.assertEqual(utils.lz4_decompress_block(b'', 0), b'')

    def test_handcrafted_block(self):
        # Hand-crafted LZ4 block that decompresses to b"HelloHello"
        # Token 0x51: literal length 5, match length 1 (+4 = 5)
        # Literals: "Hello"  Match offset: 5, length 5
        compressed = b'\x51Hello\x05\x00'
        result = utils.lz4_decompress_block(compressed, 10)
        self.assertEqual(result, b"HelloHello")

    def test_pure_literals(self):
        # Token 0x50: literal length 5, match length 0 (last sequence)
        compressed = b'\x50Hello'
        result = utils.lz4_decompress_block(compressed, 5)
        self.assertEqual(result, b"Hello")

    def test_size_padding(self):
        compressed = b'\x50Hello'
        result = utils.lz4_decompress_block(compressed, 8)
        self.assertEqual(result, b"Hello\x00\x00\x00")


class TestHashing(unittest.TestCase):
    """Test FNV-1a hashing against official test vectors."""

    def test_fnv1a_32_empty(self):
        self.assertEqual(utils.fnv1a_32(b''), 0x811C9DC5)

    def test_fnv1a_32_a(self):
        self.assertEqual(utils.fnv1a_32(b'a'), 0xE40C292C)

    def test_fnv1a_64_empty(self):
        self.assertEqual(utils.fnv1a_64(b''), 0xCBF29CE484222325)

    def test_fnv1a_64_a(self):
        self.assertEqual(utils.fnv1a_64(b'a'), 0xAF63DC4C8601EC8C)

    def test_deterministic(self):
        self.assertEqual(utils.fnv1a_32(b'unity'), utils.fnv1a_32(b'unity'))


class TestImageWriters(unittest.TestCase):
    """Test PNG and BMP writers."""

    def test_png_encoder(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'test.png')
            width, height = 2, 2
            data = bytes([255, 0, 0, 255,
                          0, 255, 0, 255,
                          0, 0, 255, 255,
                          255, 255, 255, 255])
            ugd_image.write_png(path, width, height, data)
            with open(path, 'rb') as f:
                png = f.read()
            # PNG signature
            self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
            # IHDR chunk
            length = struct.unpack('>I', png[8:12])[0]
            self.assertEqual(length, 13)
            self.assertEqual(png[12:16], b'IHDR')
            # IHDR fields: width, height, bit depth 8, color type 6 (RGBA)
            self.assertEqual(struct.unpack('>II', png[16:24]), (2, 2))
            self.assertEqual(png[24], 8)
            self.assertEqual(png[25], 6)
            # IEND at the end: 4-byte length, 'IEND', 4-byte CRC
            self.assertEqual(struct.unpack('>I', png[-12:-8])[0], 0)
            self.assertEqual(png[-8:-4], b'IEND')

    def test_bmp_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'test.bmp')
            width, height = 2, 2
            data = bytes([255, 0, 0, 255,
                          0, 255, 0, 255,
                          0, 0, 255, 255,
                          255, 255, 255, 255])
            ugd_image.write_bmp(path, width, height, data)
            with open(path, 'rb') as f:
                bmp = f.read()
            self.assertEqual(bmp[:2], b'BM')
            # BITMAPINFOHEADER size
            self.assertEqual(struct.unpack('<I', bmp[14:18])[0], 40)
            self.assertEqual(struct.unpack('<i', bmp[18:22])[0], 2)
            self.assertEqual(struct.unpack('<i', bmp[22:26])[0], 2)
            self.assertEqual(struct.unpack('<H', bmp[28:30])[0], 24)


class TestTextureDecoders(unittest.TestCase):
    """Test texture decoding functions."""

    def test_decode_rgba32(self):
        width, height = 2, 2
        data = bytes([255, 0, 0, 255,
                      0, 255, 0, 255,
                      0, 0, 255, 255,
                      255, 255, 255, 255])
        decoded = textures.decode_texture(data, 3, width, height)  # 3 = RGBA32
        self.assertEqual(len(decoded), width * height * 4)
        self.assertEqual(decoded, data)

    def test_decode_rgb24(self):
        width, height = 2, 2
        data = bytes([255, 0, 0,
                      0, 255, 0,
                      0, 0, 255,
                      255, 255, 255])
        decoded = textures.decode_texture(data, 2, width, height)  # 2 = RGB24
        self.assertEqual(len(decoded), width * height * 4)
        # Alpha should be 255 everywhere
        for i in range(3, len(decoded), 4):
            self.assertEqual(decoded[i], 255)

    def test_decode_rgb565(self):
        width, height = 2, 2
        data = struct.pack('<HHHH', 0xF800, 0x07E0, 0x001F, 0xFFFF)
        decoded = textures.decode_texture(data, 5, width, height)  # 5 = RGB565
        self.assertEqual(len(decoded), width * height * 4)
        # First pixel is pure red
        self.assertEqual(decoded[0], 255)
        self.assertEqual(decoded[1], 0)
        self.assertEqual(decoded[2], 0)

    def test_decode_dxt1(self):
        width, height = 4, 4
        # One 4x4 block: color0 = 0xFFFF (white), color1 = 0x0000 (black),
        # indices = 0 for all pixels
        data = struct.pack('<HH', 0xFFFF, 0x0000) + b'\x00' * 4
        decoded = textures.decode_texture(data, 8, width, height)  # 8 = DXT1
        self.assertEqual(len(decoded), width * height * 4)
        # Since c0 > c1, index 0 = white opaque
        self.assertEqual(decoded[:4], bytes([255, 255, 255, 255]))

    def test_decode_etc1(self):
        width, height = 4, 4
        data = b'\x00' * 8
        decoded = textures.decode_texture(data, 26, width, height)  # 26 = ETC_RGB4
        self.assertEqual(len(decoded), width * height * 4)

    def test_decode_etc2_differential_known_answer(self):
        # Differential mode block: R=29 dR=-4 G=26 dG=-3 B=8 dB=3,
        # cw1=2 cw2=3, D=1, flip=0, all pixel indices 0.
        # cols 0-1: base1 (239,214,66) + table2[0]=+9  -> (248,223,75)
        # cols 2-3: base2 (206,189,90) + table3[0]=+13 -> (219,202,103)
        data = bytes([0xEC, 0xD5, 0x43, 0x4E, 0x00, 0x00, 0x00, 0x00])
        decoded = textures.decode_texture(data, 26, 4, 4)
        expected = [
            (248, 223, 75), (248, 223, 75), (219, 202, 103), (219, 202, 103),
            (248, 223, 75), (248, 223, 75), (219, 202, 103), (219, 202, 103),
            (248, 223, 75), (248, 223, 75), (219, 202, 103), (219, 202, 103),
            (248, 223, 75), (248, 223, 75), (219, 202, 103), (219, 202, 103),
        ]
        for i, (r, g, b) in enumerate(expected):
            self.assertEqual(tuple(decoded[i * 4:i * 4 + 3]), (r, g, b), f"pixel {i}")
            self.assertEqual(decoded[i * 4 + 3], 255)

    def test_decode_etc2_individual_known_answer(self):
        # Individual mode block: base1 (4,11,9) table4, base2 (14,3,8)
        # table0, D=0, flip=0. Pixel indices (column-major) encode:
        # (1,0)=3, (1,1)=2, (1,3)=2, (2,0)=3, (3,0)=1, rest 0.
        data = bytes([0x4E, 0xB3, 0x98, 0x80, 0x01, 0x00, 0x13, 0x00])
        decoded = textures.decode_texture(data, 26, 4, 4)
        expected = [
            (86, 205, 171), (86, 205, 171), (230, 43, 128), (246, 59, 144),
            (86, 205, 171), (86, 205, 171), (246, 59, 144), (240, 53, 138),
            (86, 205, 171), (86, 205, 171), (240, 53, 138), (240, 53, 138),
            (86, 205, 171), (86, 205, 171), (240, 53, 138), (240, 53, 138),
        ]
        for i, (r, g, b) in enumerate(expected):
            self.assertEqual(tuple(decoded[i * 4:i * 4 + 3]), (r, g, b), f"pixel {i}")
            self.assertEqual(decoded[i * 4 + 3], 255)

    def test_unsupported_format(self):
        result = textures.decode_texture(b'\x00' * 16, 62, 2, 2)  # 62 = RG32 (unsupported)
        self.assertIsNone(result)


class TestSerializedFile(unittest.TestCase):
    """Test serialized file basics."""

    def test_class_ids(self):
        self.assertIn(4, serialized.CLASS_IDS)  # Transform
        self.assertIn(1, serialized.CLASS_IDS)  # GameObject
        self.assertIn(28, serialized.CLASS_IDS)  # Texture2D

    def test_texture_formats(self):
        self.assertEqual(serialized.TEXTURE_FORMATS[3], "RGBA32")
        self.assertEqual(serialized.TEXTURE_FORMATS[8], "DXT1")
        self.assertEqual(serialized.TEXTURE_FORMATS[26], "ETC_RGB4")


class TestUnityFS(unittest.TestCase):
    """Test UnityFS bundle basics."""

    def test_defaults(self):
        bf = unityfs.BundleFile()
        self.assertEqual(bf.signature, b'')
        self.assertEqual(bf.version, 0)
        self.assertEqual(len(bf.entries), 0)

    def test_reject_garbage(self):
        bf = unityfs.BundleFile()
        self.assertFalse(bf.parse(b'\x00\x01\x02\x03\x04\x05\x06\x07'))


class TestMonoPE(unittest.TestCase):
    """Test Mono PE/CLI parsing."""

    @staticmethod
    def _create_simple_pe():
        """Create a minimal but structurally-valid PE32 file."""
        # DOS header (64 bytes)
        dos = bytearray(64)
        dos[0:2] = b'MZ'
        dos[0x3C:0x40] = struct.pack('<I', 0x80)  # e_lfanew

        # PE signature
        pe_sig = b'PE\x00\x00'

        # COFF header
        coff = struct.pack('<HHIHHHH',
            0x014C,   # Machine: x86
            1,        # NumberOfSections
            0,        # TimeDateStamp
            0,        # PointerToSymbolTable
            0,        # NumberOfSymbols
            0xE0,     # SizeOfOptionalHeader
            0x010F)   # Characteristics

        # Optional header PE32 (224 bytes total = 96 fields + 16 data dirs)
        opt = bytearray()
        opt += struct.pack('<H', 0x10B)                    # Magic PE32
        opt += struct.pack('<B', 0)                        # MajorLinkerVersion
        opt += struct.pack('<B', 0)                        # MinorLinkerVersion
        opt += struct.pack('<I', 0x200)                    # SizeOfCode
        opt += struct.pack('<I', 0x200)                    # SizeOfInitializedData
        opt += struct.pack('<I', 0)                        # SizeOfUninitializedData
        opt += struct.pack('<I', 0x1000)                   # AddressOfEntryPoint
        opt += struct.pack('<I', 0x1000)                   # BaseOfCode
        opt += struct.pack('<I', 0x2000)                   # BaseOfData
        opt += struct.pack('<I', 0x400000)                 # ImageBase
        opt += struct.pack('<I', 0x1000)                   # SectionAlignment
        opt += struct.pack('<I', 0x200)                    # FileAlignment
        opt += struct.pack('<HHHHHH', 6, 0, 0, 0, 4, 0)    # OS/Image/Subsystem versions
        opt += struct.pack('<I', 0)                        # Win32VersionValue
        opt += struct.pack('<I', 0x3000)                   # SizeOfImage
        opt += struct.pack('<I', 0x200)                    # SizeOfHeaders
        opt += struct.pack('<I', 0)                        # CheckSum
        opt += struct.pack('<HH', 2, 0)                    # Subsystem (GUI), DllCharacteristics
        opt += struct.pack('<IIII', 0x100000, 0x1000,      # Stack reserve/commit
                                    0x100000, 0x1000)      # Heap reserve/commit
        opt += struct.pack('<I', 0)                        # LoaderFlags
        opt += struct.pack('<I', 16)                       # NumberOfRvaAndSizes
        for _ in range(16):                                # Data directories
            opt += struct.pack('<II', 0, 0)
        assert len(opt) == 0xE0

        # Section header
        sec = struct.pack('<8sIIIIHHHII',
            b'.text\x00\x00\x00',
            0x200, 0x1000,          # VirtualSize, VirtualAddress
            0x200, 0x200,           # SizeOfRawData, PointerToRawData
            0, 0, 0, 0,             # relocs, line numbers, counts
            0x60000020)             # Characteristics

        # Section data
        body = b'\x00' * 0x200

        return bytes(dos) + pe_sig + coff + bytes(opt) + sec + body

    def test_parse_simple_pe(self):
        pe_data = self._create_simple_pe()
        assembly = pe.MonoAssembly()
        # Parsing a PE without CLI data should not crash; returns False or object
        result = assembly.parse(pe_data)
        self.assertIsNotNone(assembly)
        # No CLI header on this synthetic file
        self.assertIn('dos_header', dir(assembly))
        if result:
            self.assertEqual(assembly.dos_header.e_magic, 0x5A4D)

    def test_reject_garbage(self):
        assembly = pe.MonoAssembly()
        self.assertFalse(assembly.parse(b'\x00' * 16))


class TestMonoIL(unittest.TestCase):
    """Test IL disassembly."""

    def test_opcode_table_populated(self):
        self.assertGreater(len(il.IL_OPCODES), 100)

    def test_known_opcodes(self):
        names = {name for name, _, _, _ in il.IL_OPCODES}
        self.assertIn('nop', names)
        self.assertIn('ret', names)
        self.assertIn('ldarg.0', names)
        self.assertIn('ldc.i4.0', names)

    def test_disassemble_ret(self):
        disassembler = il.ILDisassembler(b'\x29')  # ret
        instructions = disassembler.disassemble()
        self.assertEqual(len(instructions), 1)
        self.assertEqual(instructions[0].opcode, 'ret')


class TestProjectReconstructor(unittest.TestCase):
    """Test project reconstruction."""

    def test_create_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            reconstructor = ProjectReconstructor(tmp, "TestGame")
            reconstructor.create_structure()
            self.assertTrue(os.path.exists(os.path.join(tmp, "Assets")))
            self.assertTrue(os.path.exists(os.path.join(tmp, "Assets", "Scripts")))
            self.assertTrue(os.path.exists(os.path.join(tmp, "ProjectSettings")))
            self.assertTrue(os.path.exists(os.path.join(tmp, "Packages")))
            reconstructor.finalize()

    def test_generate_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            reconstructor = ProjectReconstructor(tmp, "TestGame")
            report = reconstructor.generate_report()
            self.assertEqual(report['game_name'], "TestGame")
            self.assertEqual(report['output_dir'], os.path.abspath(tmp))


class TestCLIIntegration(unittest.TestCase):
    """Test CLI module integration."""

    def test_import_and_detect(self):
        from ugd import cli
        with tempfile.TemporaryDirectory() as tmp:
            # Empty directory -> unknown
            info = cli.detect_game_type(tmp)
            self.assertFalse(info['is_mono'])
            self.assertFalse(info['is_il2cpp'])
        with tempfile.TemporaryDirectory() as tmp:
            # Mono layout
            os.makedirs(os.path.join(tmp, 'Managed'))
            info = cli.detect_game_type(tmp)
            self.assertTrue(info['is_mono'])
        with tempfile.TemporaryDirectory() as tmp:
            # IL2CPP layout
            metadata = os.path.join(tmp, 'il2cpp_data', 'Metadata')
            os.makedirs(metadata)
            with open(os.path.join(metadata, 'global-metadata.dat'), 'wb') as f:
                f.write(b'')
            info = cli.detect_game_type(tmp)
            self.assertTrue(info['is_il2cpp'])

    def test_main_help(self):
        from ugd import cli
        try:
            code = cli.main(['--help'])
        except SystemExit as e:
            code = e.code
        self.assertEqual(code, 0)


def run_all_tests():
    """Run all self-tests and print results."""
    print("=" * 60)
    print("Unity Game Decompiler - Self Tests")
    print("=" * 60)
    print()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestReader))
    suite.addTests(loader.loadTestsFromTestCase(TestLZ4))
    suite.addTests(loader.loadTestsFromTestCase(TestHashing))
    suite.addTests(loader.loadTestsFromTestCase(TestImageWriters))
    suite.addTests(loader.loadTestsFromTestCase(TestTextureDecoders))
    suite.addTests(loader.loadTestsFromTestCase(TestSerializedFile))
    suite.addTests(loader.loadTestsFromTestCase(TestUnityFS))
    suite.addTests(loader.loadTestsFromTestCase(TestMonoPE))
    suite.addTests(loader.loadTestsFromTestCase(TestMonoIL))
    suite.addTests(loader.loadTestsFromTestCase(TestProjectReconstructor))
    suite.addTests(loader.loadTestsFromTestCase(TestCLIIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 60)
    if result.wasSuccessful():
        print("All tests passed!")
    else:
        print(f"Tests: {result.testsRun} run, {len(result.failures)} failures, {len(result.errors)} errors")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)