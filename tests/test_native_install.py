"""Exercise the real package manager inside temporary fake game directories only."""
from datetime import datetime, timezone
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smt-loader', type=Path, help='Optional exact dinput8.dll from SMT v1.5; never executed')
    args = parser.parse_args()
    reports = []
    # A unique directory avoids deleting or overwriting prior test evidence.
    base = Path(tempfile.mkdtemp(prefix='installer-',dir=ROOT/'build/native'))
    shutil.copytree(ROOT/'dist/SnowRunnerFFBFix-0.2.0',base/'package')
    pkg = base/'package/Sources'
    manifest = json.loads((pkg/'package.json').read_text())
    assert 'sdkPath' not in manifest and 'sdkSha256' not in manifest
    smt_hash = '66fd34b4f7944c1ef3e67a1b4c5d4973109405f824971cbe19372bb9c9ac6535'
    assert {x['version']: x['sha256'] for x in manifest['compatibleLoaders']} == {
        '8.5.0': smt_hash, '10.0.2': manifest['files']['Payload/dinput8.dll']}
    # All child operations start with no SDK at the former lookup location.
    env = dict(os.environ, ProgramW6432=str(base/'program-files'))
    sdk = base/'program-files/Logi/Trueforce/1_3_12/trueforce_sdk_x64.dll'
    assert not sdk.exists()
    fake_exe = b'Synthetic installation test, never executed.\n'
    manifest['gameSha256'] = hashlib.sha256(fake_exe).hexdigest()
    (pkg/'package.json').write_text(json.dumps(manifest,indent=2))

    def game(name):
        path = base/name/'Sources/Bin'
        path.mkdir(parents=True)
        (path/'SnowRunner.exe').write_bytes(fake_exe)
        return path

    def run(action, path, success=True, match=None, remove_loader=False):
        proc = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
            '-File',str(pkg/'Scripts/manage.ps1'),'-Action',action,'-GameDirectory',str(path)] +
            (['-RemoveLoader'] if remove_loader else []),
            env=env,capture_output=True,text=True,encoding='utf-8',timeout=45)
        reports.append({'action':action,'directory':str(path),'expectedSuccess':success,
                        'removeLoader':remove_loader,'exitCode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr})
        assert (proc.returncode==0)==success, proc.stdout+proc.stderr
        if match: assert match in proc.stdout+proc.stderr, proc.stdout+proc.stderr
        print('PASS',action,path.parent.parent.name,flush=True)

    def untouched(path):
        assert (path/'SnowRunner.exe').read_bytes()==fake_exe

    a = game('normal')
    run('Check',a.parent.parent)
    assert sorted(p.name for p in a.iterdir())==['SnowRunner.exe']
    run('Install',a)
    receipt=json.loads((a/'SnowRunnerFFBFix.install.json').read_text(encoding='utf-8-sig'))
    assert all(x['owned'] for x in receipt['files'])
    run('Disable',a); assert (a/'SnowRunnerFFBFix.disabled').exists()
    run('Status',a)
    run('Enable',a); assert not (a/'SnowRunnerFFBFix.disabled').exists()
    run('Install',a,False,'Existing file will not be overwritten')
    run('Uninstall',a)
    assert sorted(p.name for p in a.iterdir())==['SnowRunner.exe']
    untouched(a)

    # Installing also succeeds with an unrelated SDK file; it is preserved.
    sdk.parent.mkdir(parents=True)
    sdk.write_bytes(b'unrecognized SDK fixture; never loaded')
    extra = game('different-sdk')
    run('Check',extra)
    run('Install',extra)
    # Legacy scripts may still pass this flag; it cannot bypass automatic safeguards.
    run('Uninstall',extra,remove_loader=True)
    assert sorted(p.name for p in extra.iterdir())==['SnowRunner.exe']
    assert sdk.read_bytes()==b'unrecognized SDK fixture; never loaded'
    untouched(extra)

    # Upgrade uses the old receipt's hashes, never overwrites the old binary.
    upgrade = game('upgrade-from-0.1.0')
    entries = []
    for name in ('dinput8.dll','SnowRunnerFFBFix.asi'):
        if name == 'dinput8.dll': shutil.copyfile(pkg/'Payload'/name,upgrade/name)
        else: (upgrade/name).write_bytes(b'prior plugin fixture; never loaded')
        entries.append({'name':name,'sha256':hashlib.sha256((upgrade/name).read_bytes()).hexdigest(),'owned':True})
    (upgrade/'SnowRunnerFFBFix.install.json').write_text(json.dumps({
        'product':'SnowRunnerFFBFix','version':'0.1.0','files':entries}))
    run('Install',upgrade,False,'Existing file will not be overwritten')
    run('Uninstall',upgrade)
    run('Install',upgrade)
    assert hashlib.sha256((upgrade/'SnowRunnerFFBFix.asi').read_bytes()).hexdigest()==manifest['files']['Payload/SnowRunnerFFBFix.asi']
    run('Uninstall',upgrade)
    untouched(upgrade)

    b=game('unknown-version'); (b/'SnowRunner.exe').write_bytes(b'updated game')
    run('Install',b,False,'Unknown game version')
    assert len(list(b.iterdir()))==1

    c=game('loader-conflict'); (c/'dinput8.dll').write_bytes(b'preexisting loader')
    run('Install',c,False,'An unrecognized mod loader')
    assert (c/'dinput8.dll').read_bytes()==b'preexisting loader' and len(list(c.iterdir()))==2

    d=game('shared-loader'); shutil.copyfile(pkg/'Payload/dinput8.dll',d/'dinput8.dll')
    run('Install',d)
    run('Uninstall',d,remove_loader=True)
    assert (d/'dinput8.dll').exists() and not (d/'SnowRunnerFFBFix.asi').exists()

    e=game('loader-other-plugin'); run('Install',e)
    (e/'other.asi').write_bytes(b'other plugin')
    run('Uninstall',e)
    assert (e/'dinput8.dll').exists() and (e/'other.asi').read_bytes()==b'other plugin'

    nested=game('nested-other-plugin'); run('Install',nested)
    (nested/'plugins/subfolder').mkdir(parents=True)
    (nested/'plugins/subfolder/other.asi').write_bytes(b'nested plugin')
    run('Uninstall',nested)
    assert (nested/'dinput8.dll').exists()
    assert (nested/'plugins/subfolder/other.asi').read_bytes()==b'nested plugin'
    assert not (nested/'SnowRunnerFFBFix.asi').exists()

    changed=game('modified-loader'); run('Install',changed)
    (changed/'dinput8.dll').write_bytes(b'loader replaced by another mod')
    run('Uninstall',changed,remove_loader=True)
    assert (changed/'dinput8.dll').read_bytes()==b'loader replaced by another mod'
    assert not (changed/'SnowRunnerFFBFix.asi').exists()
    assert not (changed/'SnowRunnerFFBFix.install.json').exists()

    # A known alternative is reused without touching its bytes or taking ownership.
    # The synthetic allowlist entry isolates hash matching from DLL execution.
    alternative = game('recognized-alternative')
    alternative_bytes = b'alternative loader fixture; never executed'
    alternative_hash = hashlib.sha256(alternative_bytes).hexdigest()
    manifest['compatibleLoaders'].append({'version':'test', 'architecture':'x64', 'sha256':alternative_hash})
    (pkg/'package.json').write_text(json.dumps(manifest))
    (alternative/'dinput8.dll').write_bytes(alternative_bytes)
    run('Check',alternative)
    assert len(list(alternative.iterdir())) == 2
    run('Install',alternative)
    reused = json.loads((alternative/'SnowRunnerFFBFix.install.json').read_text())
    loader_entry = next(x for x in reused['files'] if x['name'] == 'dinput8.dll')
    assert loader_entry == {'name':'dinput8.dll','sha256':alternative_hash,'owned':False}
    run('Uninstall',alternative)
    assert (alternative/'dinput8.dll').read_bytes() == alternative_bytes
    assert not (alternative/'SnowRunnerFFBFix.asi').exists()
    manifest['compatibleLoaders'].pop()
    (pkg/'package.json').write_text(json.dumps(manifest))

    if args.smt_loader:
        assert hashlib.sha256(args.smt_loader.read_bytes()).hexdigest() == smt_hash
        smt = game('actual-smt-8.5.0')
        shutil.copyfile(args.smt_loader,smt/'dinput8.dll')
        (smt/'SMT.asi').write_bytes(b'other mod placeholder; never executed')
        before = {p.name:p.read_bytes() for p in smt.iterdir()}
        run('Check',smt)
        run('Install',smt)
        reused = json.loads((smt/'SnowRunnerFFBFix.install.json').read_text())
        assert next(x for x in reused['files'] if x['name']=='dinput8.dll') == {
            'name':'dinput8.dll','sha256':smt_hash,'owned':False}
        run('Uninstall',smt)
        assert {p.name:p.read_bytes() for p in smt.iterdir()} == before

    # Ownership alone never authorizes removal when dependency discovery is uncertain.
    for name, relative, content in (
        ('new-loader-config','dinput8.ini',b'[GlobalSets]\nLoadPlugins=1'),
        ('new-global-config','scripts/global.ini',b'[GlobalSets]'),
        ('chained-loader','dinput8Hooked.dll',b'chained proxy'),
        ('source-plugin','plugins/probe.cxx',b'snippet'),
        ('hidden-plugin','hidden.asi',b'hidden plugin'),
    ):
        uncertain = game(name)
        run('Install',uncertain)
        other = uncertain/relative
        other.parent.mkdir(parents=True,exist_ok=True)
        other.write_bytes(content)
        if name == 'hidden-plugin':
            set_attributes = ctypes.windll.kernel32.SetFileAttributesW
            set_attributes.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
            assert set_attributes(str(other),2)
        run('Uninstall',uncertain)
        assert (uncertain/'dinput8.dll').exists() and other.read_bytes() == content
        assert not (uncertain/'SnowRunnerFFBFix.asi').exists()

    # A file that cannot be inspected is kept, without blocking plugin removal.
    locked = game('locked-loader'); run('Install',locked)
    create_file = ctypes.windll.kernel32.CreateFileW
    create_file.argtypes = [ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,
                           ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
    create_file.restype = ctypes.c_void_p
    handle = create_file(str(locked/'dinput8.dll'),0x80000000,0,None,3,0,None)
    assert handle not in (None,ctypes.c_void_p(-1).value)
    try:
        run('Uninstall',locked)
        assert not (locked/'SnowRunnerFFBFix.asi').exists()
    finally:
        close_handle = ctypes.windll.kernel32.CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        assert close_handle(handle)
    assert (locked/'dinput8.dll').exists()

    junction_game = game('junction-dependency'); run('Install',junction_game)
    external = base/'junction-target'; external.mkdir()
    (external/'untouched.txt').write_bytes(b'outside game directory')
    create_junction = base/'create-junction.ps1'
    create_junction.write_text('param($Link,$Target)\n$ErrorActionPreference="Stop"\n'
        'New-Item -ItemType Junction -Path $Link -Value $Target | Out-Null\n')
    junction = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(create_junction),
                    '-Link',str(junction_game/'redirect'),'-Target',str(external)],capture_output=True,text=True)
    assert junction.returncode == 0, junction.stdout + junction.stderr
    run('Uninstall',junction_game)
    assert (junction_game/'dinput8.dll').exists()
    assert (external/'untouched.txt').read_bytes() == b'outside game directory'
    assert not (junction_game/'SnowRunnerFFBFix.asi').exists()

    f=game('modified-plugin'); run('Install',f)
    (f/'SnowRunnerFFBFix.asi').write_bytes(b'modified by user')
    run('Uninstall',f,False,'Modified installed file preserved')
    assert (f/'dinput8.dll').exists() and (f/'SnowRunnerFFBFix.install.json').exists()
    assert (f/'SnowRunnerFFBFix.asi').read_bytes()==b'modified by user'

    g=game('configured-loader'); (g/'dinput8.ini').write_text('[GlobalSets]\nLoadPlugins=0\n')
    run('Install',g,False,'Existing loader configuration')
    assert len(list(g.iterdir()))==2

    h=game('receipt-escape'); run('Install',h)
    r=json.loads((h/'SnowRunnerFFBFix.install.json').read_text())
    r['files'][0]['name']='../outside.dll'
    (h/'SnowRunnerFFBFix.install.json').write_text(json.dumps(r))
    run('Uninstall',h,False,'Invalid installation receipt')
    assert (h/'dinput8.dll').exists() and (h/'SnowRunnerFFBFix.asi').exists()

    # Moving the payload must preserve missing/corrupt binary checks before any write.
    payload = pkg/'Payload/SnowRunnerFFBFix.asi'
    original = payload.read_bytes()
    damaged = game('damaged-package')
    try:
        payload.unlink()
        run('Install',damaged,False,'SnowRunnerFFBFix.asi')
        assert list(damaged.iterdir()) == [damaged/'SnowRunner.exe']
        payload.write_bytes(b'corrupted payload')
        run('Install',damaged,False,'SnowRunnerFFBFix.asi')
        assert list(damaged.iterdir()) == [damaged/'SnowRunner.exe']
    finally:
        payload.write_bytes(original)

    for p in (c,d,e,f,g,h,nested,changed): untouched(p)
    report={'timestampUtc':datetime.now(timezone.utc).isoformat(),'gameLaunched':False,
            'realGameChanged':False,'actualSmtLoaderChecked':bool(args.smt_loader),'tests':reports}
    (ROOT/'logs/native-installer-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'PASS {len(reports)} installer operations. Evidence: {base}')


if __name__ == '__main__': main()
