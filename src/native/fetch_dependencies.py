"""Download pinned build dependencies into this repository only (no installation)."""
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def fetch(url, expected=None):
    data = urllib.request.urlopen(url, timeout=120).read()
    digest = hashlib.sha256(data).hexdigest()
    if expected and digest != expected:
        raise RuntimeError('SHA256 mismatch: ' + url)
    return data, digest


def extract(data, dest):
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if not (dest / name).resolve().is_relative_to(dest.resolve()):
                raise RuntimeError('Archive path escapes destination')
        z.extractall(dest)


def main():
    vendor = ROOT / 'vendor'
    lock = json.loads((vendor / 'manifest.json').read_text()) if (vendor / 'manifest.json').exists() else None
    manifest = {}
    url = 'https://github.com/mstorsjo/llvm-mingw/releases/download/20261104/llvm-mingw-20261104-ucrt-x86_64.zip'
    expected = '552191b5754c49a5a20723276a6fc56541ea1922c4c50b7b669022333fc1b40f'
    compiler = ROOT / '.toolchain/llvm-mingw-20261104-ucrt-x86_64/bin/clang.exe'
    if not compiler.exists():
        print('Downloading portable compiler...', flush=True)
        data, _ = fetch(url, expected)
        extract(data, ROOT / '.toolchain')
    manifest['compiler'] = {'url': url, 'sha256': expected}
    base = 'https://raw.githubusercontent.com/TsudaKageyu/minhook/v1.3.4/'
    names = ['LICENSE.txt', 'include/MinHook.h', 'src/buffer.c', 'src/buffer.h',
             'src/hook.c', 'src/trampoline.c', 'src/trampoline.h',
             'src/hde/hde64.c', 'src/hde/hde64.h', 'src/hde/pstdint.h', 'src/hde/table64.h']
    manifest['minhook'] = {'version': '1.3.4', 'files': {}}
    for name in names:
        expected_file = lock['minhook']['files'][name] if lock else None
        data, digest = fetch(base + name, expected_file)
        p = vendor / 'minhook' / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        manifest['minhook']['files'][name] = digest
    url = 'https://github.com/ThirteenAG/Ultimate-ASI-Loader/releases/download/v10.0.2/Ultimate-ASI-Loader-NoPDB_x64.zip'
    data, digest = fetch(url, 'fe964adf4de7f467ff39c440a4059de02e37d0574a62944eef2f55a35edafa2f')
    dest = vendor / 'ultimate-asi-loader'
    extract(data, dest)
    # Preserve upstream license independently of the binary distribution.
    license_data, _ = fetch('https://raw.githubusercontent.com/ThirteenAG/Ultimate-ASI-Loader/v10.0.2/license')
    (dest / 'LICENSE.txt').write_bytes(license_data)
    manifest['loader'] = {'version': '10.0.2', 'url': url, 'sha256': digest,
                          'files': {str(p.relative_to(dest)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in dest.rglob('*') if p.is_file()}}
    (vendor / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Dependencies ready; hashes in vendor/manifest.json', flush=True)


if __name__ == '__main__':
    main()
