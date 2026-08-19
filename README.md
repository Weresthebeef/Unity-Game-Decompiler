# Unity Game Decompiler (ugd)

A **complete, from-scratch** Unity game decompiler that decompiles Unity games (both Mono and IL2CPP) back into their code and reconstructable Unity projects.

> **IMPORTANT**: This is a **from-scratch implementation**. No code was stolen, copied, or borrowed from any existing decompiler (UnityPy, Il2CppDumper, dnSpy, ILSpy, etc.). Every parser, decompiler, and extractor was written from scratch based on official specifications and reverse-engineered formats.

## Features

### Core Features
- **Mono Support**: Full decompilation of Mono assemblies (DLL files)
  - PE/COFF header parsing
  - CLI metadata table parsing
  - Complete IL (Intermediate Language) disassembly
  - IL to C# decompilation
- **IL2CPP Support**: IL2CPP metadata parsing
  - global-metadata.dat parsing (versions 24, 27, 29)
  - Type, method, and field definitions extraction
  - C# class skeleton generation
- **Asset Extraction**: Extract all Unity assets
  - Serialized file parsing (.assets)
  - UnityFS bundle parsing (.unity3d)
  - Type tree support
  - External reference resolution
- **Texture Decoding**: Full texture format support
  - RGBA32, RGBA24, ARGB32, ARGB4444
  - RGB565, RGB24
  - DXT1, DXT5
  - ETC1, ETC2_RGB, ETC2_RGBA8
  - PNG output
- **Mesh Extraction**: Vertex and triangle data extraction
- **Audio Extraction**: AudioClip decoding
- **Scene/Prefab Reconstruction**: YAML-based scene reconstruction
- **Project Reconstruction**: Full Unity project structure generation

### Supported Unity Versions
- Unity 2017.x through 2022.x (Mono)
- Unity 2018.x through 2022.x (IL2CPP)

### Supported Platforms
- Windows (Standalone)
- Android (APK)
- WebGL
- macOS
- Linux

## Installation

```bash
# Clone the repository
git clone https://github.com/Gc.idk/unity-game-decompiler.git
cd unity-game-decompiler

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (none required for core functionality)
# This tool is self-contained and has no external dependencies
```

## Usage

### Interactive Mode

```bash
# Run in interactive mode
python -m ugd --interactive
python ugd.py --interactive
```

This launches an interactive CLI where you can:
1. Decompile a game directory
2. Decompile a single file
3. Extract assets from .assets files
4. Extract assets from .unity3d bundles
5. Decompile Mono assemblies
6. Parse IL2CPP metadata
7. Show game info
8. Get help

### Command-Line Mode

```bash
# Decompile a game directory
python -m ugd "C:\Games\MyGame\MyGame_Data" -o ./output

# Decompile an APK
python -m ugd game.apk -o ./output

# Decompile a single DLL
python -m ugd Assembly-CSharp.dll -o ./output

# Extract from an assets file
python -m ugd level0.assets -o ./output

# Extract from a bundle
python -m ugd streamingassets.unity3d -o ./output

# Show info about a game
python -m ugd "C:\Games\MyGame\MyGame_Data" --info

# Get help
python -m ugd --help
```

### Command-Line Options

```
Usage: ugd [OPTIONS] PATH

Arguments:
  PATH  Path to game directory, file, or APK

Options:
  -o, --output TEXT     Output directory
  --extract             Extract assets only
  --decompile           Decompile scripts only
  --metadata            Parse IL2CPP metadata only
  --info                Show info only
  --interactive         Run in interactive mode
  -v, --verbose         Verbose output
  --force               Force overwrite output
  --help                Show this help message
```

## Output Structure

When decompiling a game, the tool creates the following structure:

```
output/
├── Assets/
│   ├── Scripts/
│   │   ├── Assembly-CSharp/      # Decompiled Mono scripts
│   │   ├── Il2CppSkeletons/       # Generated IL2CPP class skeletons
│   │   └── Plugins/               # Original DLLs (for Mono)
│   ├── Textures/                  # Extracted textures as PNG
│   ├── Meshes/                    # Extracted mesh data
│   ├── Audio/                     # Extracted audio clips
│   ├── Scenes/                    # Reconstructed scenes
│   ├── Prefabs/                   # Reconstructed prefabs
│   ├── Materials/                 # Extracted materials
│   ├── Extracted/                 # Raw extracted assets
│   └── Bundles/                   # Extracted bundle contents
├── ProjectSettings/              # Reconstructed project settings
├── Il2CppMetadata/               # IL2CPP metadata dumps (if applicable)
└── report.txt                     # Decompilation report
```

## How It Works

### Mono Decompilation

1. **PE/COFF Parsing**: Parses the DOS header, COFF header, optional header, and section headers
2. **CLI Metadata**: Parses CLI header and metadata tables (TypeDef, MethodDef, FieldDef, etc.)
3. **Method Body Extraction**: Extracts IL code from method bodies
4. **IL Disassembly**: Disassembles IL instructions using a complete opcode table
5. **C# Decompilation**: Converts IL to readable C# code using stack-based analysis

### IL2CPP Metadata Parsing

1. **Header Parsing**: Parses the global-metadata.dat header
2. **Type System**: Extracts type definitions, method definitions, and field definitions
3. **String Literals**: Extracts all string literals from the metadata
4. **Skeleton Generation**: Generates C# class skeletons with proper signatures

### Asset Extraction

1. **Bundle Parsing**: Parses UnityFS, UnityWeb, and UnityRaw bundle formats
2. **Serialized File Parsing**: Parses the serialized file header, type tree, and objects
3. **Asset Reconstruction**: Reconstructs Unity objects (GameObjects, Components, Textures, etc.)
4. **Format Conversion**: Converts Unity-specific formats (textures, meshes, audio) to standard formats

## Limitations

### Mono
- Some complex IL patterns may not decompile perfectly
- Async/await methods may have limited support
- Generic type constraints are not fully reconstructed
- Debug information (local variable names) is not available

### IL2CPP
- **No code recovery**: IL2CPP compiles C# to native code, so the original code is lost
- Only class/method/field signatures are recovered
- Method bodies cannot be recovered (only skeletons)
- Some type information may be incomplete

### Assets
- Some custom/third-party asset types may not be recognized
- Complex shader properties may not be fully reconstructed
- Animation curves may have limited precision
- Some audio formats may not be supported

## Technical Details

### No External Dependencies

This tool has **zero external dependencies** for its core functionality. It implements everything from scratch:
- LZ4 decompression
- PNG encoding
- FNV-1a hashing
- PE/COFF parsing
- CLI metadata parsing
- IL disassembly
- C# decompilation
- UnityFS parsing
- Serialized file parsing
- Texture decoding
- And more...

### File Formats Supported

#### Bundle Formats
- UnityFS (most common)
- UnityWeb
- UnityRaw

#### Serialized File Versions
- 1 (Unity 2.x)
- 2-15 (Unity 3.x - 5.x)
- 16-22 (Unity 2017.x - 2021.x)

#### Texture Formats
- RGBA32, RGBA24
- ARGB32, ARGB4444
- RGB565, RGB24
- DXT1, DXT5
- ETC1, ETC2_RGB, ETC2_RGBA8

#### IL2CPP Metadata Versions
- 24 (Unity 2020.1 - 2020.2)
- 27 (Unity 2020.3 - 2021.1)
- 29 (Unity 2021.2+)

## Building

This is a pure Python project. No compilation is required.

```bash
# Run directly
python -m ugd [options] path

# Or install as a package
pip install -e .
ugd [options] path
```

## Testing

```bash
# Run self-tests
python -m tests.selftest

# Or
python tests/selftest.py
```

The self-test generates synthetic test data, processes it through the decompiler, and validates the output.

## Contributing

Contributions are welcome! Please ensure:
1. All code is **from scratch** - no copying from existing decompilers
2. Follow the existing code style
3. Add tests for new features
4. Update documentation as needed

## License

MIT License - Copyright (c) 2026 Gc.idk

See [LICENSE](LICENSE) for full license text.

## Credits

- **Gc.idk**: Primary author and maintainer
- **Unity Technologies**: For creating Unity and its file formats
- **ECMA**: For the CLI specification (ECMA-335)
- **Various researchers**: For documenting Unity file formats

## Disclaimer

This tool is for **educational and research purposes only**. Use it responsibly and respect copyright laws. Only decompile games that you own or have permission to decompile.

The authors are not responsible for any misuse of this tool.
