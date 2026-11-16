"""Native regression and actual ASI loader integration in disposable fixture hosts."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src/native'))
from build import BUILD, CORE, compile_target, write_profile
import pefile


def main():
    results = []

    def run(name, cmd, cwd=ROOT, env=None):
        result = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=45)
        results.append({'name':name, 'exitCode':result.returncode, 'stdout':result.stdout, 'stderr':result.stderr})
        print(name, result.returncode, result.stdout.strip(), flush=True)
        if result.returncode:
            raise RuntimeError(result.stderr or result.stdout or f'{name} exited {result.returncode}')

    for case in ('guards','abi','semantics','readonly','boundary','executable','overflow','null'):
        run(case, [str(BUILD/'native-tests.exe'),case])

    host = BUILD/'loader-host.exe'
    pe = pefile.PE(str(host))
    symbol = next(x for x in pe.DIRECTORY_ENTRY_EXPORT.symbols if x.name == b'FixtureCtor')
    target = symbol.address
    guards = [{'rva':target,'hex':pe.get_data(target,32).hex()}]
    game_hash = hashlib.sha256(host.read_bytes()).hexdigest()
    profile = BUILD/'fixture-profile'
    write_profile(profile,game_hash,guards,target)
    fixture = BUILD/'fixture-plugin.asi'
    compile_target(fixture, CORE+['src/native/plugin.c'],[profile],['-shared','-Wl,--exclude-all-symbols'])

    for case in ('release-refusal','active-sdk-absent','active-sdk-different','disabled','code-mismatch','game-update'):
        dest = BUILD/'loader-tests'/case
        dest.mkdir(parents=True,exist_ok=True)
        shutil.copy2(host,dest/'loader-host.exe')
        shutil.copy2(ROOT/'vendor/ultimate-asi-loader/dinput8.dll',dest/'dinput8.dll')
        marker = dest/'SnowRunnerFFBFix.disabled'
        marker.unlink(missing_ok=True)
        if case == 'disabled': marker.write_text('disabled\n')
        if case == 'code-mismatch':
            bad = [{'rva':target,'hex':guards[0]['hex'][:-2]+'cc'}]
            bad_profile = BUILD/'bad-fixture-profile'
            write_profile(bad_profile,game_hash,bad,target)
            compile_target(dest/'SnowRunnerFFBFix.asi', CORE+['src/native/plugin.c'],
                           [bad_profile],['-shared','-Wl,--exclude-all-symbols'])
        else:
            shutil.copy2(BUILD/'SnowRunnerFFBFix.asi' if case == 'release-refusal' else fixture,
                         dest/'SnowRunnerFFBFix.asi')
        if case == 'game-update':
            with (dest/'loader-host.exe').open('ab') as f: f.write(b'unknown build')
        # Redirect only the child's former SDK lookup location; never touch G HUB.
        env = dict(os.environ, ProgramW6432=str(dest/'program-files'))
        sdk = dest/'program-files/Logi/Trueforce/1_3_12/trueforce_sdk_x64.dll'
        if case == 'active-sdk-different':
            sdk.parent.mkdir(parents=True, exist_ok=True)
            sdk.write_bytes(b'not a Logitech DLL; must never be loaded or inspected')
        else:
            assert not sdk.exists()
        active = case.startswith('active-')
        run('loader-'+case,[str(dest/'loader-host.exe'),'active' if active else 'inactive'],dest,env)
        log = (dest/'SnowRunnerFFBFix.log').read_text()
        if active: assert 'applied=1' in log and 'armed=1' in log
        else: assert 'armed=0' in log
        if case in ('release-refusal','game-update'): assert 'unknown game executable SHA256' in log
        if case == 'code-mismatch': assert 'loaded code mismatch' in log
        results[-1]['statusLog'] = log

    # Inspect the deployable file, never the fixture build.
    release = pefile.PE(str(BUILD/'SnowRunnerFFBFix.asi'))
    exports = [s.name.decode() for s in release.DIRECTORY_ENTRY_EXPORT.symbols]
    assert sorted(exports) == ['GetFixStatus','InitializeASI']
    assert release.FILE_HEADER.Machine == 0x8664
    assert b'SYNTHETIC-TEST-ONLY' not in (BUILD/'SnowRunnerFFBFix.asi').read_bytes()
    assert b'coolfarmer' not in (BUILD/'SnowRunnerFFBFix.asi').read_bytes().lower()
    assert all(not s.Name.startswith(b'.debug') for s in release.sections)
    binary = (BUILD/'SnowRunnerFFBFix.asi').read_bytes()
    for text in ('trueforce_sdk_x64.dll', 'unverified Logitech SDK'):
        assert text.encode() not in binary and text.encode('utf-16le') not in binary
    report = {'timestampUtc':datetime.now(timezone.utc).isoformat(), 'results':results,
              'gameLaunched':False,'wheelUsed':False,
              'pluginSha256':hashlib.sha256((BUILD/'SnowRunnerFFBFix.asi').read_bytes()).hexdigest()}
    out = ROOT/'logs/native-validation.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(f'PASS {len(results)} cases; report: {out}')


if __name__ == '__main__': main()
