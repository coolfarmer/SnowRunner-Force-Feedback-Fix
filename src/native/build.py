"""Build the x64 plugin and native fixture, without launching SnowRunner."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / 'build/native'
TOOLCHAIN = Path(os.environ.get('LLVM_MINGW_ROOT', str(ROOT / '.toolchain/llvm-mingw-20261104-ucrt-x86_64')))
BIN = TOOLCHAIN / 'bin'
CC = BIN / 'x86_64-w64-mingw32-clang.exe'


def write_profile(dest, game_hash=None, guards=None, target=None):
    cfg = json.loads((ROOT / 'src/native/game-profile.json').read_text())
    guards = guards if guards is not None else cfg['guards']
    target = cfg['constructorRva'] if target is None else target
    lines = ['/* Generated from verified profiles. No runtime override. */', '#pragma once',
             '#define PROFILE_NAME "' + ('SYNTHETIC-TEST-ONLY' if game_hash else cfg['game_version']) + '"',
             '#define GAME_SHA256 "' + (game_hash or cfg['game_sha256']).lower() + '"',
             '#define CONSTRUCTOR_RVA ' + hex(target)]
    for i, g in enumerate(guards):
        b = bytes.fromhex(g['hex'])
        lines.append(f'static const unsigned char guard_{i}[] = {{' + ','.join(f'0x{x:02x}' for x in b) + '};')
    lines.append('static const CodeGuard PROFILE_GUARDS[] = {')
    lines += [f'    {{{g["rva"]}, sizeof(guard_{i}), guard_{i}}},' for i, g in enumerate(guards)]
    lines.append('};')
    dest.mkdir(parents=True, exist_ok=True)
    (dest / 'profile.h').write_text('\n'.join(lines) + '\n')


def compile_target(out, sources, includes=(), extra=()):
    out.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env['PATH'] = str(BIN) + os.pathsep + env.get('PATH', '')
    common = ['-O2', '-g', '-Wall', '-Wextra', '-Werror', '-std=c11', '-DUNICODE', '-D_UNICODE',
              '-I' + str(ROOT/'src/native'), '-I' + str(ROOT/'vendor/minhook/include')]
    common += ['-I' + str(p) for p in includes]
    cmd = [str(CC), *common, *(str(ROOT/p) for p in sources), *extra,
           '-Wl,--dynamicbase,--nxcompat,--no-insert-timestamp', '-lbcrypt', '-o', str(out)]
    subprocess.run(cmd, env=env, check=True, cwd=ROOT)


CORE = ['src/native/fix.c', 'src/native/hash.c', 'src/native/thunk.S',
        'vendor/minhook/src/buffer.c', 'vendor/minhook/src/hook.c',
        'vendor/minhook/src/trampoline.c', 'vendor/minhook/src/hde/hde64.c']


def verify_vendor():
    m = json.loads((ROOT/'vendor/manifest.json').read_text())
    for group, sub in [('minhook', 'minhook'), ('loader', 'ultimate-asi-loader')]:
        for file, digest in m[group]['files'].items():
            actual = hashlib.sha256((ROOT/'vendor'/sub/file).read_bytes()).hexdigest()
            if actual != digest:
                raise RuntimeError('Dependency fingerprint changed: ' + file)


def main():
    verify_vendor()
    write_profile(BUILD / 'release-profile')
    compile_target(BUILD/'SnowRunnerFFBFix.asi', CORE + ['src/native/plugin.c'],
                   [BUILD/'release-profile'], ['-shared', '-Wl,--exclude-all-symbols,--strip-debug'])
    compile_target(BUILD/'native-tests.exe', CORE + ['tests/native/core_tests.c', 'tests/native/fixture.S'])
    compile_target(BUILD/'loader-host.exe', ['tests/native/loader_host.c', 'tests/native/fixture.S'],
                   extra=['-ldinput8', '-ldxguid', '-Wl,--export-all-symbols'])
    versions = subprocess.check_output([str(CC), '--version'], text=True).strip()
    artifacts = {name: hashlib.sha256((BUILD/name).read_bytes()).hexdigest()
                 for name in ('SnowRunnerFFBFix.asi','native-tests.exe','loader-host.exe')}
    (BUILD/'build.json').write_text(json.dumps({'compiler': versions, 'artifacts': artifacts}, indent=2)+'\n')
    print(json.dumps({'built': artifacts}, indent=2))


if __name__ == '__main__':
    main()
