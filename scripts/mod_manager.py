"""Portable build, install, verify, and rollback for Block Raiden."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

from archive_ops import crilayla, dat_members, replace_members, collapse_wmb
from patch_ops import apply_patch, sha256
from textures import make_textures

PACKAGE = Path(__file__).resolve().parents[1]
EXE = 'METAL GEAR RISING REVENGEANCE.exe'
ALLOWED = re.compile(r'GameData/pl/pl[0-9a-f]{4}\.(dat|dtt)\Z')


def safe_path(root, relative):
    if not ALLOWED.fullmatch(relative):
        raise ValueError('Unexpected mod file path: ' + relative)
    root = Path(root).resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError('File escaped its intended folder')
    return target


def game_candidates():
    steam = set()
    if os.name == 'nt':
        import winreg
        for hive, key, value in [(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam', 'SteamPath'),
                                 (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam', 'InstallPath')]:
            try:
                with winreg.OpenKey(hive, key) as handle:
                    steam.add(Path(winreg.QueryValueEx(handle, value)[0]))
            except OSError:
                pass
    steam.add(Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Steam')
    libraries = set(steam)
    for directory in steam:
        vdf = directory / 'steamapps/libraryfolders.vdf'
        if vdf.is_file():
            for path in re.findall(r'"path"\s+"((?:\\.|[^"\\])*)"', vdf.read_text(encoding='utf-8', errors='replace')):
                libraries.add(Path(path.replace('\\\\', '\\')))
    return sorted({(p / 'steamapps/common/METAL GEAR RISING REVENGEANCE').resolve()
                   for p in libraries if (p / 'steamapps/common/METAL GEAR RISING REVENGEANCE' / EXE).is_file()}, key=str)


def select_game(value):
    if value:
        directory = Path(value).resolve()
    else:
        candidates = game_candidates()
        if len(candidates) == 1:
            directory = candidates[0]
        else:
            if candidates:
                print('Multiple installations found:')
                for item in candidates:
                    print('  ' + str(item))
            directory = Path(input('Paste the Rising folder containing the game EXE: ').strip().strip('"')).resolve()
    if not (directory / EXE).is_file() or not (directory / 'GameData/data000.cpk').is_file():
        raise ValueError('Rising was not found in that folder')
    return directory


def select_minecraft(value, required):
    if value:
        path = Path(value).resolve()
        make_textures(path, required)
        return path
    versions = Path(os.environ.get('APPDATA', '')) / '.minecraft/versions'
    candidates = sorted(versions.glob('*/*.jar'), key=lambda p: p.stat().st_mtime, reverse=True)
    preferred = versions / '1.21.11/1.21.11.jar'
    if preferred.is_file():
        candidates = [preferred] + [p for p in candidates if p != preferred]
    for jar in candidates:
        try:
            make_textures(jar, required)
            return jar
        except (KeyError, ValueError, OSError, zipfile.BadZipFile):
            continue
    path = Path(input('Paste your installed Minecraft Java 1.21.11 client JAR path: ').strip().strip('"')).resolve()
    make_textures(path, required)
    return path


def require_game_closed():
    if os.name == 'nt':
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                                 "if (Get-Process -Name 'METAL GEAR RISING REVENGEANCE' -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }"],
                                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0:
            raise ValueError('Close Rising before installing or uninstalling')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_atomic(path, blob):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.block-raiden-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(blob)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, value):
    write_atomic(path, json.dumps(value, indent=2).encode('utf-8'))


def load_release():
    release = read_json(PACKAGE / 'release.json')
    if release['format'] != 1 or len(release['assets']) != 26:
        raise ValueError('Unsupported release manifest')
    paths = [asset['output'] for asset in release['assets']]
    if len(set(paths)) != 26 or any(not ALLOWED.fullmatch(p) for p in paths):
        raise ValueError('Invalid release paths')
    return release


def read_original(game, asset):
    if asset['archive'] != 'data000.cpk' or asset['offset'] < 0 or not 0 < asset['packed_size'] < 64 * 1024 * 1024:
        raise ValueError('Unsupported asset location')
    with (game / 'GameData' / asset['archive']).open('rb') as handle:
        handle.seek(asset['offset'])
        blob = handle.read(asset['packed_size'])
    if sha256(blob) != asset['packed_sha256']:
        raise ValueError('Your Rising game archives differ from the supported PC version: ' + asset['output'])
    original = crilayla(blob) if blob.startswith(b'CRILAYLA') else blob
    if sha256(original) != asset['original_sha256']:
        raise ValueError('Original game asset verification failed')
    return original


def build_files(game, jar, release):
    wta, wtp = make_textures(jar, release['minecraft_textures'])
    output = {}
    for i, asset in enumerate(release['assets'], 1):
        original = read_original(game, asset)
        replacements = {}
        for name, offset, size in dat_members(original):
            member = original[offset:offset + size]
            if asset['kind'] == 'hide' and name.endswith('.wmb'):
                replacements[name] = collapse_wmb(member)
            elif asset['kind'] == 'model' and name.endswith('.wmb'):
                patch_path = PACKAGE / 'patches' / (Path(asset['output']).stem + '.patch')
                replacements[name] = apply_patch(member, patch_path.read_bytes())
            elif asset['kind'] == 'model' and name.endswith('.wta'):
                replacements[name] = wta
            elif asset['kind'] == 'texture' and name.endswith('.wtp'):
                replacements[name] = wtp
        blob = replace_members(original, replacements)
        if sha256(blob) != asset['installed_sha256']:
            raise ValueError('Generated mod differs from the verified release: ' + asset['output'])
        output[asset['output']] = blob
        print(f'Built and verified {i}/26: {Path(asset["output"]).name}', flush=True)
    return output


def state_root(game, supplied):
    if supplied:
        return Path(supplied).resolve()
    identifier = sha256(str(game).casefold().encode())[:16]
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData/Local'))) / 'BlockRaidenMod' / identifier


def check_state(state, game, release):
    if state['format'] != 1 or Path(state['game_dir']).resolve() != game:
        raise ValueError('Backup manifest belongs to another game folder')
    allowed = {asset['output'] for asset in release['assets']}
    paths = [entry['path'] for entry in state['files']]
    if len(paths) != 26 or set(paths) != allowed:
        raise ValueError('Invalid installation manifest')


def preflight_uninstall(game, state_dir, state, release):
    check_state(state, game, release)
    operations = []
    for entry in state['files']:
        target = safe_path(game, entry['path'])
        backup = safe_path(state_dir / 'backups', entry['path'])
        allowed = {entry['installed_sha256']}
        if state.get('phase') == 'installing' and entry['had_original']:
            allowed.add(entry['original_sha256'])
        if target.exists() and (not target.is_file() or sha256(target.read_bytes()) not in allowed):
            raise ValueError('Another mod changed ' + entry['path'] + '. No files were removed.')
        if entry['had_original'] and (not backup.is_file() or sha256(backup.read_bytes()) != entry['original_sha256']):
            raise ValueError('A required backup is missing or changed. No files were removed.')
        operations.append((entry, target, backup))
    return operations


def uninstall(game, state_dir, release):
    manifest = state_dir / 'installation.json'
    if not manifest.is_file():
        print('No installation record found for this game folder.')
        return
    state = read_json(manifest)
    operations = preflight_uninstall(game, state_dir, state, release)
    # Mark recovery phase first, allowing already-restored originals after an interruption.
    state['phase'] = 'installing'
    write_json(manifest, state)
    for entry, target, backup in operations:
        if entry['had_original']:
            write_atomic(target, backup.read_bytes())
        elif target.is_file():
            target.unlink()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    write_json(state_dir / ('uninstalled-' + stamp + '.json'), state)
    manifest.unlink()
    print('Uninstalled. Previous loose files restored; saves and game archives retained.')


def install(game, state_dir, release, files):
    manifest = state_dir / 'installation.json'
    if manifest.exists():
        state = read_json(manifest)
        check_state(state, game, release)
        preflight_uninstall(game, state_dir, state, release)
        if state.get('phase') != 'installed':
            raise ValueError('An interrupted operation was found. Run Uninstall first, then install again.')
        if state.get('release') != release['version']:
            raise ValueError('Uninstall the earlier release before installing this version.')
        for entry in state['files']:
            write_atomic(safe_path(game, entry['path']), files[entry['path']])
        print('Reinstalled and verified 26 files.')
        return
    state = {'format': 1, 'release': release['version'], 'game_dir': str(game),
             'phase': 'installing', 'files': []}
    # Validate every target before making backups or touching game files.
    for relative, blob in files.items():
        target = safe_path(game, relative)
        if target.exists() and not target.is_file():
            raise ValueError('A mod target is not a regular file')
        exists = target.is_file()
        state['files'].append({'path': relative, 'had_original': exists,
                               'original_sha256': sha256(target.read_bytes()) if exists else None,
                               'installed_sha256': sha256(blob)})
    for entry in state['files']:
        if entry['had_original']:
            write_atomic(safe_path(state_dir / 'backups', entry['path']), safe_path(game, entry['path']).read_bytes())
    write_json(manifest, state)
    try:
        for entry in state['files']:
            target = safe_path(game, entry['path'])
            write_atomic(target, files[entry['path']])
            if sha256(target.read_bytes()) != entry['installed_sha256']:
                raise ValueError('Installed file verification failed')
        state['phase'] = 'installed'
        write_json(manifest, state)
    except Exception:
        uninstall(game, state_dir, release)
        raise
    print('Installed and verified 26 files. Backups: ' + str(state_dir))


def main():
    parser = argparse.ArgumentParser(description='Block Raiden: a Steve character mod for Rising')
    parser.add_argument('action', choices=['install', 'uninstall', 'verify', 'build'])
    parser.add_argument('--game-dir', help='Rising folder containing the game EXE')
    parser.add_argument('--minecraft-jar', help='Installed Minecraft Java client JAR')
    parser.add_argument('--state-dir', help='Advanced: custom backup/state directory')
    parser.add_argument('--output', help='Build only: folder for generated mod files')
    args = parser.parse_args()
    release = load_release()
    game = select_game(args.game_dir)
    state_dir = state_root(game, args.state_dir)
    print('Game folder: ' + str(game))
    if args.action in {'install', 'uninstall'}:
        require_game_closed()
    if args.action == 'uninstall':
        uninstall(game, state_dir, release)
    elif args.action == 'verify':
        for asset in release['assets']:
            path = safe_path(game, asset['output'])
            if not path.is_file() or sha256(path.read_bytes()) != asset['installed_sha256']:
                raise ValueError('Installed mod verification failed: ' + asset['output'])
        print('All 26 installed files match this release.')
    else:
        if args.action == 'build' and not args.output:
            raise ValueError('Build requires --output')
        jar = select_minecraft(args.minecraft_jar, release['minecraft_textures'])
        print('Minecraft client: ' + str(jar))
        files = build_files(game, jar, release)
        if args.action == 'build':
            output = Path(args.output).resolve()
            if output == game or output.is_relative_to(game):
                raise ValueError('Use install to write into the game folder')
            for relative, blob in files.items():
                write_atomic(safe_path(output, relative), blob)
            print('Build complete. No game files changed.')
        else:
            install(game, state_dir, release, files)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, EOFError) as error:
        print('\nUnable to complete operation: ' + str(error), file=sys.stderr)
        sys.exit(1)
