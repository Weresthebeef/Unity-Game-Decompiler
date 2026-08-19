# Unity Game Decompiler (ugd)
# From-scratch implementation - NO stolen code
# MIT License - Copyright (c) 2026 Gc.idk

"""
Interactive and command-line interface for the Unity Game Decompiler.

Implements the full CLI described by the user:
- User pastes a folder/file path
- Auto-detection of game type (Mono vs IL2CPP)
- Full decompilation to a reconstructable Unity project
"""
import os
import sys
import shutil
import zipfile
import tempfile
import argparse
from typing import Dict, List, Optional, Any

from . import __version__, BANNER
from .utils import human_size
from .unityfs import BundleFile
from .serialized import SerializedFile
from .extract import save_extracted_assets
from .il2cpp import Il2CppMetadataParser
from .mono.pe import MonoAssembly
from .mono.decompile import MonoDecompiler
from .project import ProjectReconstructor


def print_banner() -> None:
    print(BANNER)


def detect_game_type(data_dir: str) -> Dict[str, Any]:
    """
    Detect the game type (Mono or IL2CPP) and Unity version.
    Checks standard Unity data-directory layouts.
    """
    result = {
        'is_mono': False,
        'is_il2cpp': False,
        'unity_version': 'Unknown',
        'platform': 'Unknown',
    }

    # Mono layout: <name>_Data/Managed/*.dll
    managed_dir = os.path.join(data_dir, 'Managed')
    if os.path.isdir(managed_dir):
        result['is_mono'] = True
        result['platform'] = 'Standalone'
        engine_dll = os.path.join(managed_dir, 'UnityEngine.dll')
        if os.path.isfile(engine_dll):
            try:
                with open(engine_dll, 'rb') as f:
                    data = f.read()
                assembly = MonoAssembly()
                if assembly.parse(data) and assembly.cli_header:
                    result['unity_version'] = (
                        f"{assembly.cli_header.MajorRuntimeVersion}."
                        f"{assembly.cli_header.MinorRuntimeVersion}"
                    )
            except Exception:
                pass
        return result

    # IL2CPP layout: <name>_Data/il2cpp_data/Metadata/global-metadata.dat
    metadata_candidates = [
        os.path.join(data_dir, 'il2cpp_data', 'Metadata', 'global-metadata.dat'),
        os.path.join(data_dir, 'global-metadata.dat'),
    ]
    for md in metadata_candidates:
        if os.path.isfile(md):
            result['is_il2cpp'] = True
            result['platform'] = 'Standalone'
            try:
                with open(md, 'rb') as f:
                    data = f.read()
                parser = Il2CppMetadataParser()
                if parser.parse(data):
                    version_map = {
                        24: '2020.1-2020.2',
                        27: '2020.3-2021.1',
                        29: '2021.2+',
                    }
                    result['unity_version'] = version_map.get(
                        parser.version, f"Metadata v{parser.version}")
            except Exception:
                pass
            return result

    # Android IL2CPP: lib/arm64-v8a/libil2cpp.so + metadata
    if os.path.isfile(os.path.join(data_dir, 'libil2cpp.so')):
        result['is_il2cpp'] = True
        result['platform'] = 'Android'
        return result

    # Nested <name>_Data folder
    data_folder = os.path.join(data_dir, 'Data')
    if os.path.isdir(data_folder):
        if os.path.isdir(os.path.join(data_folder, 'Managed')):
            result['is_mono'] = True
            result['platform'] = 'Standalone'
        elif os.path.isfile(os.path.join(data_folder, 'il2cpp_data', 'Metadata', 'global-metadata.dat')):
            result['is_il2cpp'] = True
            result['platform'] = 'Standalone'

    return result


def process_directory(data_dir: str, output_dir: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Process a game data directory: extract assets and decompile scripts."""
    report = {
        'game_type': 'Unknown',
        'unity_version': 'Unknown',
        'platform': 'Unknown',
        'assets_extracted': 0,
        'scripts_decompiled': 0,
        'textures_extracted': 0,
        'audio_extracted': 0,
        'errors': [],
    }

    game_info = detect_game_type(data_dir)
    report.update(game_info)

    game_type = ('Mono' if report['is_mono'] else
                 'IL2CPP' if report['is_il2cpp'] else 'Unknown')
    print(f"\nDetected: {report['platform']} game ({game_type})")
    print(f"Unity Version: {report['unity_version']}")

    game_name = os.path.basename(os.path.abspath(data_dir).rstrip('\\/'))
    reconstructor = ProjectReconstructor(output_dir, game_name)
    reconstructor.create_structure()

    script_dirs = []

    for root, dirs, files in os.walk(data_dir):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if file.endswith('.assets'):
                    process_assets_file(file_path, output_dir, options)
                    report['assets_extracted'] += 1

                elif file.endswith(('.unity3d', '.bundle')):
                    process_bundle_file(file_path, output_dir, options)
                    report['assets_extracted'] += 1

                elif file == 'global-metadata.dat' and report['is_il2cpp']:
                    process_il2cpp_metadata(file_path, output_dir, reconstructor)
                    report['scripts_decompiled'] += 1

                elif file.endswith('.dll') and report['is_mono']:
                    if file in ('UnityEngine.dll', 'UnityEngine.CoreModule.dll',
                                'mscorlib.dll', 'System.dll', 'System.Core.dll'):
                        continue
                    count = process_mono_assembly(file_path, output_dir, reconstructor)
                    report['scripts_decompiled'] += count

            except Exception as e:
                report['errors'].append(f"{file_path}: {e}")
                if options.get('verbose'):
                    import traceback
                    traceback.print_exc()

    reconstructor.finalize()
    report['output_dir'] = output_dir
    report['game_name'] = game_name
    return report


def process_assets_file(assets_path: str, output_dir: str, options: Dict[str, Any]) -> int:
    """Parse a .assets serialized file and extract everything from it."""
    with open(assets_path, 'rb') as f:
        data = f.read()

    sf = SerializedFile()
    if not sf.parse(data):
        print(f"Failed to parse: {assets_path}")
        return 0

    rel = os.path.relpath(assets_path, output_dir)
    sub = os.path.join(output_dir, "Assets", "Extracted",
                       os.path.splitext(rel)[0].replace('..', '_'))
    os.makedirs(sub, exist_ok=True)

    count = save_extracted_assets(sf, sub)

    reconstruct_scene(sf, output_dir, assets_path)
    return count


def process_bundle_file(bundle_path: str, output_dir: str, options: Dict[str, Any]) -> int:
    """Parse a UnityFS bundle and extract all entries."""
    with open(bundle_path, 'rb') as f:
        data = f.read()

    bundle = BundleFile()
    if not bundle.parse(data):
        print(f"Failed to parse bundle: {bundle_path}")
        return 0

    bundle_name = os.path.splitext(os.path.basename(bundle_path))[0]
    bundle_dir = os.path.join(output_dir, "Assets", "Bundles", bundle_name)
    os.makedirs(bundle_dir, exist_ok=True)

    count = 0
    for entry in bundle.entries:
        try:
            content = bundle.extract_entry(entry)
            out = os.path.join(bundle_dir, entry.name)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, 'wb') as f:
                f.write(content)
            if entry.name.endswith('.assets'):
                count += process_assets_file(out, output_dir, options)
            count += 1
        except Exception as e:
            print(f"Error extracting {entry.name}: {e}")
    return count


def process_il2cpp_metadata(metadata_path: str, output_dir: str,
                            reconstructor: ProjectReconstructor) -> int:
    """Parse global-metadata.dat and write C# skeletons + metadata dump."""
    with open(metadata_path, 'rb') as f:
        data = f.read()

    parser = Il2CppMetadataParser()
    if not parser.parse(data):
        print(f"Failed to parse IL2CPP metadata: {metadata_path}")
        return 0

    skeletons = parser.generate_csharp_skeletons()
    scripts_dir = os.path.join(output_dir, "Assets", "Scripts", "Il2CppSkeletons")
    os.makedirs(scripts_dir, exist_ok=True)

    for type_name, source in skeletons.items():
        safe = ''.join(c if c.isalnum() or c in '_' else '_' for c in type_name)
        if not safe:
            safe = 'Unknown'
        parts = safe.rsplit('.', 1)
        if len(parts) == 2:
            ns_dir = os.path.join(scripts_dir, *parts[0].split('.'))
            os.makedirs(ns_dir, exist_ok=True)
            file_path = os.path.join(ns_dir, parts[1] + '.cs')
        else:
            file_path = os.path.join(scripts_dir, safe + '.cs')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(source)

    md_dir = os.path.join(output_dir, "Il2CppMetadata")
    os.makedirs(md_dir, exist_ok=True)
    parser.dump(md_dir)

    print(f"IL2CPP: wrote {len(skeletons)} class skeletons")
    return len(skeletons)


def process_mono_assembly(dll_path: str, output_dir: str,
                          reconstructor: ProjectReconstructor) -> int:
    """Decompile a Mono assembly to C# and copy the DLL to Plugins."""
    decompiler = MonoDecompiler()
    assembly = decompiler.load_assembly(dll_path)
    if not assembly:
        print(f"Failed to load assembly: {dll_path}")
        return 0

    results = decompiler.decompile_all_methods(assembly)
    dll_name = os.path.splitext(os.path.basename(dll_path))[0]
    out_asm = os.path.join(output_dir, "Assets", "Scripts", dll_name)
    os.makedirs(out_asm, exist_ok=True)

    for method_name, source in results.items():
        safe = ''.join(c if c.isalnum() or c in '_' else '_' for c in method_name) or 'Method'
        with open(os.path.join(out_asm, f"{safe}.cs"), 'w', encoding='utf-8') as f:
            f.write(source)

    plugins_dir = os.path.join(output_dir, "Assets", "Plugins")
    os.makedirs(plugins_dir, exist_ok=True)
    shutil.copy2(dll_path, os.path.join(plugins_dir, os.path.basename(dll_path)))

    print(f"Mono: decompiled {len(results)} methods from {dll_name}")
    return len(results)


def reconstruct_scene(sf: SerializedFile, output_dir: str, assets_path: str) -> None:
    """Write a YAML scene file for GameObjects found in the serialized file."""
    from .unityyaml import UnityYAMLWriter

    scene_name = os.path.splitext(os.path.basename(assets_path))[0]
    scene_objects = []
    for obj in sf.objects:
        class_id = obj.class_id
        class_name = sf.get_class_name(class_id)
        if class_id in (4, 1):  # Transform, GameObject
            scene_objects.append({
                'class_id': class_id,
                'class_name': class_name,
                'path_id': obj.path_id,
                'name': f"{class_name}_{obj.path_id}",
            })

    if scene_objects:
        scene_dir = os.path.join(output_dir, "Assets", "Scenes")
        os.makedirs(scene_dir, exist_ok=True)
        scene_path = os.path.join(scene_dir, f"{scene_name}.unity")
        UnityYAMLWriter.write_scene(scene_path, scene_objects)
        print(f"Reconstructed scene: {scene_name}")


def interactive_mode() -> None:
    """Run the interactive paste-a-path CLI."""
    print_banner()
    handlers = {
        '1': cmd_decompile_directory,
        '2': cmd_decompile_file,
        '3': cmd_extract_assets,
        '4': cmd_extract_bundle,
        '5': cmd_decompile_assembly,
        '6': cmd_parse_metadata,
        '7': cmd_info,
        '8': cmd_help,
    }
    while True:
        try:
            print("\n" + "=" * 60)
            print("Unity Game Decompiler - Interactive Mode")
            print("=" * 60)
            print("""
Options:
  1. Decompile a game directory
  2. Decompile a single file (exe/apk/dll/dat)
  3. Extract assets from .assets file
  4. Extract assets from .unity3d bundle
  5. Decompile Mono assembly
  6. Parse IL2CPP metadata
  7. Info - show game info
  8. Help
  9. Exit
""")
            choice = input("Enter your choice (1-9): ").strip()
            if choice in ('9', 'exit', 'quit'):
                print("\nExiting...")
                break
            handler = handlers.get(choice)
            if handler:
                handler()
            else:
                print("Invalid choice.")
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()


def _ask_path(prompt: str) -> Optional[str]:
    path = input(prompt).strip().strip('"').strip("'")
    if not path or not os.path.exists(path):
        print("Invalid path.")
        return None
    return path


def _ask_output(default: str) -> str:
    out = input("Output directory (Enter for default): ").strip().strip('"')
    if not out:
        out = default
    out = os.path.abspath(out)
    os.makedirs(out, exist_ok=True)
    return out


def cmd_decompile_directory() -> None:
    data_dir = _ask_path("Enter the game data directory path:\nPath: ")
    if not data_dir:
        return
    output_dir = _ask_output(os.path.join(os.getcwd(), "output"))
    print("\nDecompiling... this may take a while.")
    report = process_directory(data_dir, output_dir, {'verbose': True})
    print_report(report)


def cmd_decompile_file() -> None:
    file_path = _ask_path("Enter the path to a file (exe/apk/dll/dat/unity3d):\nPath: ")
    if not file_path:
        return
    base = os.path.splitext(os.path.basename(file_path))[0]
    output_dir = _ask_output(os.path.join(os.getcwd(), "output", base))
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.apk':
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(file_path) as zf:
                zf.extractall(temp_dir)
            report = process_directory(temp_dir, output_dir, {'verbose': True})
            print_report(report)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    elif ext == '.dll':
        rec = ProjectReconstructor(output_dir)
        rec.create_structure()
        count = process_mono_assembly(file_path, output_dir, rec)
        rec.finalize()
        print(f"\nDecompiled {count} methods to: {output_dir}")
    elif 'metadata' in os.path.basename(file_path).lower():
        rec = ProjectReconstructor(output_dir)
        rec.create_structure()
        process_il2cpp_metadata(file_path, output_dir, rec)
        rec.finalize()
        print(f"\nProcessed IL2CPP metadata to: {output_dir}")
    elif ext in ('.unity3d', '.bundle'):
        process_bundle_file(file_path, output_dir, {'verbose': True})
        print(f"\nExtracted bundle to: {output_dir}")
    elif ext == '.assets':
        process_assets_file(file_path, output_dir, {'verbose': True})
        print(f"\nExtracted assets to: {output_dir}")
    elif ext == '.exe':
        data_dir = file_path[:-4] + '_Data'
        if not os.path.isdir(data_dir):
            data_dir = file_path
        report = process_directory(data_dir, output_dir, {'verbose': True})
        print_report(report)
    else:
        print(f"Unsupported file type: {ext}")


def cmd_extract_assets() -> None:
    path = _ask_path("Enter the path to the .assets file:\nPath: ")
    if not path:
        return
    output_dir = _ask_output(os.path.join(os.getcwd(), "output"))
    count = process_assets_file(path, output_dir, {'verbose': True})
    print(f"\nExtracted {count} assets to: {output_dir}")


def cmd_extract_bundle() -> None:
    path = _ask_path("Enter the path to the .unity3d bundle:\nPath: ")
    if not path:
        return
    output_dir = _ask_output(os.path.join(os.getcwd(), "output"))
    count = process_bundle_file(path, output_dir, {'verbose': True})
    print(f"\nExtracted {count} files to: {output_dir}")


def cmd_decompile_assembly() -> None:
    path = _ask_path("Enter the path to the .dll assembly:\nPath: ")
    if not path:
        return
    base = os.path.splitext(os.path.basename(path))[0]
    output_dir = _ask_output(os.path.join(os.getcwd(), "output", base))
    rec = ProjectReconstructor(output_dir)
    rec.create_structure()
    count = process_mono_assembly(path, output_dir, rec)
    rec.finalize()
    print(f"\nDecompiled {count} methods to: {output_dir}")


def cmd_parse_metadata() -> None:
    path = _ask_path("Enter the path to global-metadata.dat:\nPath: ")
    if not path:
        return
    output_dir = _ask_output(os.path.join(os.getcwd(), "output"))
    rec = ProjectReconstructor(output_dir)
    rec.create_structure()
    process_il2cpp_metadata(path, output_dir, rec)
    rec.finalize()
    print(f"\nProcessed IL2CPP metadata to: {output_dir}")


def cmd_info() -> None:
    path = _ask_path("Enter the path to a game directory or file:\nPath: ")
    if not path:
        return
    show_info(path)


def show_info(path: str) -> None:
    if os.path.isfile(path):
        show_file_info(path)
    else:
        info = detect_game_type(path)
        game_type = ('Mono' if info['is_mono'] else
                     'IL2CPP' if info['is_il2cpp'] else 'Unknown')
        print("\nGame Info:")
        print(f"  Type: {game_type}")
        print(f"  Unity Version: {info['unity_version']}")
        print(f"  Platform: {info['platform']}")
        counts: Dict[str, int] = {}
        for root, dirs, files in os.walk(path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                counts[ext or '(none)'] = counts.get(ext or '(none)', 0) + 1
        print("\n  File Types:")
        for ext, count in sorted(counts.items(), key=lambda x: -x[1])[:10]:
            print(f"    {ext}: {count}")


def show_file_info(path: str) -> None:
    ext = os.path.splitext(path)[1].lower()
    name = os.path.basename(path)

    if ext == '.dll':
        with open(path, 'rb') as f:
            data = f.read()
        assembly = MonoAssembly()
        if assembly.parse(data):
            print("\nMono Assembly Info:")
            print(f"  File: {path}")
            print(f"  CLI Version: {assembly.cli_header.MajorRuntimeVersion}."
                  f"{assembly.cli_header.MinorRuntimeVersion}")
            print(f"  Entry Point Token: 0x{assembly.cli_header.EntryPointToken:08X}")
            if assembly.metadata and assembly.metadata.tables:
                print("\n  Metadata Tables:")
                for table_idx, rows in sorted(assembly.metadata.tables.items()):
                    if rows:
                        print(f"    Table 0x{table_idx:02X}: {len(rows)} rows")
        else:
            print("Not a valid Mono assembly.")

    elif 'metadata' in name.lower():
        with open(path, 'rb') as f:
            data = f.read()
        parser = Il2CppMetadataParser()
        if parser.parse(data):
            print("\nIL2CPP Metadata Info:")
            print(f"  File: {path}")
            print(f"  Version: {parser.version}")
            print(f"  Type Definitions: {len(parser.type_definitions)}")
            print(f"  Method Definitions: {len(parser.method_definitions)}")
            print(f"  Field Definitions: {len(parser.field_definitions)}")
            print(f"  Parameter Definitions: {len(parser.parameter_definitions)}")
            print(f"  Image Definitions: {len(parser.image_definitions)}")
            print(f"  String Literals: {len(parser.string_literals)}")
        else:
            print("Not a valid IL2CPP metadata file.")

    elif ext == '.assets':
        with open(path, 'rb') as f:
            data = f.read()
        sf = SerializedFile()
        if sf.parse(data):
            print("\nSerialized File Info:")
            print(f"  File: {path}")
            print(f"  Version: {sf.version}")
            print(f"  Objects: {len(sf.objects)}")
            print(f"  Types: {len(sf.types)}")
            print(f"  Externals: {len(sf.externals)}")
            counts: Dict[str, int] = {}
            for obj in sf.objects:
                cn = sf.get_class_name(obj.class_id)
                counts[cn] = counts.get(cn, 0) + 1
            print("\n  Top Classes:")
            for cn, count in sorted(counts.items(), key=lambda x: -x[1])[:10]:
                print(f"    {cn}: {count}")
        else:
            print("Not a valid serialized file.")

    elif ext in ('.unity3d', '.bundle'):
        with open(path, 'rb') as f:
            data = f.read()
        bundle = BundleFile()
        if bundle.parse(data):
            print("\nBundle Info:")
            print(f"  File: {path}")
            print(f"  Signature: {bundle.signature}")
            print(f"  Version: {bundle.version}")
            print(f"  Unity Version: {bundle.unity_version}")
            print(f"  Entries: {len(bundle.entries)}")
            total = sum(e.size for e in bundle.entries)
            print(f"  Total Size: {human_size(total)}")
            for entry in bundle.entries[:20]:
                print(f"    - {entry.name} ({human_size(entry.size)})")
            if len(bundle.entries) > 20:
                print(f"    ... and {len(bundle.entries) - 20} more")
        else:
            print("Not a valid UnityFS bundle.")

    else:
        print(f"Unknown file type: {ext}")


def cmd_help() -> None:
    print("""
Unity Game Decompiler - Help
============================
A complete, from-scratch Unity game decompiler (Mono + IL2CPP).

Features:
  - Extracts assets from .assets files and .unity3d bundles
  - Decodes textures (DXT, ETC, RGBA, RGB565...) to PNG
  - Decompiles Mono assemblies (PE/CLI/IL) to C#
  - Generates C# skeletons from IL2CPP global-metadata.dat
  - Reconstructs scenes/prefabs as Unity YAML
  - Builds a reconstructable Unity project tree

CLI examples:
  python ugd.py --interactive
  python ugd.py "C:\\Games\\MyGame\\MyGame_Data" -o ./output
  python ugd.py game.apk -o ./output
  python ugd.py Assembly-CSharp.dll -o ./output
  python ugd.py global-metadata.dat -o ./output
  python ugd.py "path\\to\\game" --info
""")


def print_report(report: Dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("Decompilation Report")
    print("=" * 60)
    print(f"Game Type: {report.get('game_type', 'Unknown')}")
    print(f"Unity Version: {report.get('unity_version', 'Unknown')}")
    print(f"Platform: {report.get('platform', 'Unknown')}")
    print(f"Assets Extracted: {report.get('assets_extracted', 0)}")
    print(f"Scripts Decompiled: {report.get('scripts_decompiled', 0)}")
    print(f"Output Directory: {report.get('output_dir', '')}")
    errors = report.get('errors', [])
    if errors:
        print(f"\nErrors: {len(errors)}")
        for err in errors[:10]:
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
    print("=" * 60)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Returns process exit code."""
    parser = argparse.ArgumentParser(
        prog='ugd',
        description='Unity Game Decompiler - from-scratch Mono + IL2CPP decompiler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  ugd \"C:\\Games\\MyGame\\MyGame_Data\" -o ./output\n"
            "  ugd game.apk -o ./output\n"
            "  ugd Assembly-CSharp.dll -o ./output\n"
            "  ugd global-metadata.dat -o ./output\n"
            "  ugd --interactive\n"
        ),
    )
    parser.add_argument('path', nargs='?', help='Path to game dir, file, or APK')
    parser.add_argument('-o', '--output', help='Output directory')
    parser.add_argument('--info', action='store_true', help='Show info only')
    parser.add_argument('--interactive', action='store_true', help='Run interactive mode')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--force', action='store_true', help='Overwrite existing output dir')
    args = parser.parse_args(argv)

    if args.interactive or not args.path:
        print_banner()
        interactive_mode()
        return 0

    path = args.path.strip().strip('"').strip("'")
    if not os.path.exists(path):
        print(f"Error: path does not exist: {path}")
        return 1

    if args.info:
        show_info(path)
        return 0

    if args.output:
        output_dir = os.path.abspath(args.output)
    else:
        base = os.path.splitext(os.path.basename(path))[0]
        output_dir = os.path.join(os.getcwd(), base + "_decompiled")

    if os.path.exists(output_dir):
        if args.force:
            shutil.rmtree(output_dir)
        else:
            print(f"Error: output directory already exists: {output_dir}")
            print("Use --force to overwrite.")
            return 1
    os.makedirs(output_dir, exist_ok=True)

    if os.path.isfile(path):
        ext = os.path.splitext(path)[1].lower()
        if ext == '.apk':
            temp_dir = tempfile.mkdtemp()
            try:
                with zipfile.ZipFile(path) as zf:
                    zf.extractall(temp_dir)
                report = process_directory(temp_dir, output_dir, {'verbose': args.verbose})
                print_report(report)
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
        elif ext == '.dll':
            rec = ProjectReconstructor(output_dir)
            rec.create_structure()
            count = process_mono_assembly(path, output_dir, rec)
            rec.finalize()
            print(f"Decompiled {count} methods to: {output_dir}")
        elif 'metadata' in os.path.basename(path).lower():
            rec = ProjectReconstructor(output_dir)
            rec.create_structure()
            process_il2cpp_metadata(path, output_dir, rec)
            rec.finalize()
            print(f"Processed IL2CPP metadata to: {output_dir}")
        elif ext in ('.assets', '.unity3d', '.bundle'):
            fn = process_bundle_file if ext in ('.unity3d', '.bundle') else process_assets_file
            count = fn(path, output_dir, {'verbose': args.verbose})
            print(f"Extracted {count} items to: {output_dir}")
        elif ext == '.exe':
            data_dir = path[:-4] + '_Data'
            if not os.path.isdir(data_dir):
                data_dir = os.path.dirname(path)
            report = process_directory(data_dir, output_dir, {'verbose': args.verbose})
            print_report(report)
        else:
            print(f"Unsupported file type: {ext}")
            return 1
    else:
        report = process_directory(path, output_dir, {'verbose': args.verbose})
        print_report(report)

    return 0


if __name__ == '__main__':
    sys.exit(main())