"""Exercise the real package manager inside temporary fake game directories only."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    reports = []
    # A unique directory avoids deleting or overwriting prior test evidence.
    base = Path(tempfile.mkdtemp(prefix='installer-',dir=ROOT/'build/native'))
    shutil.copytree(ROOT/'dist/SnowRunnerFFBFix-0.2.0',base/'package')
    pkg = base/'package/Sources'
    manifest = json.loads((pkg/'package.json').read_text())
    assert 'sdkPath' not in manifest and 'sdkSha256' not in manifest
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

    def run(action, path, success=True, match=None):
        proc = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
            '-File',str(pkg/'manage.ps1'),'-Action',action,'-GameDirectory',str(path)],
            env=env,capture_output=True,text=True,timeout=45)
        reports.append({'action':action,'directory':str(path),'expectedSuccess':success,
                        'exitCode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr})
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
    run('Uninstall',extra)
    assert sorted(p.name for p in extra.iterdir())==['SnowRunner.exe']
    assert sdk.read_bytes()==b'unrecognized SDK fixture; never loaded'
    untouched(extra)

    # Upgrade uses the old receipt's hashes, never overwrites the old binary.
    upgrade = game('upgrade-from-0.1.0')
    entries = []
    for name in ('dinput8.dll','SnowRunnerFFBFix.asi'):
        if name == 'dinput8.dll': shutil.copyfile(pkg/name,upgrade/name)
        else: (upgrade/name).write_bytes(b'prior plugin fixture; never loaded')
        entries.append({'name':name,'sha256':hashlib.sha256((upgrade/name).read_bytes()).hexdigest(),'owned':True})
    (upgrade/'SnowRunnerFFBFix.install.json').write_text(json.dumps({
        'product':'SnowRunnerFFBFix','version':'0.1.0','files':entries}))
    run('Install',upgrade,False,'Existing file will not be overwritten')
    run('Uninstall',upgrade)
    run('Install',upgrade)
    assert hashlib.sha256((upgrade/'SnowRunnerFFBFix.asi').read_bytes()).hexdigest()==manifest['files']['SnowRunnerFFBFix.asi']
    run('Uninstall',upgrade)
    untouched(upgrade)

    b=game('unknown-version'); (b/'SnowRunner.exe').write_bytes(b'updated game')
    run('Install',b,False,'Unknown game version')
    assert len(list(b.iterdir()))==1

    c=game('loader-conflict'); (c/'dinput8.dll').write_bytes(b'preexisting loader')
    run('Install',c,False,'Existing file will not be overwritten')
    assert (c/'dinput8.dll').read_bytes()==b'preexisting loader' and len(list(c.iterdir()))==2

    d=game('shared-loader'); shutil.copyfile(pkg/'dinput8.dll',d/'dinput8.dll')
    run('Install',d)
    run('Uninstall',d)
    assert (d/'dinput8.dll').exists() and not (d/'SnowRunnerFFBFix.asi').exists()

    e=game('loader-other-plugin'); run('Install',e)
    (e/'other.asi').write_bytes(b'other plugin')
    run('Uninstall',e,match='Loader preserved')
    assert (e/'dinput8.dll').exists() and (e/'other.asi').read_bytes()==b'other plugin'

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

    for p in (c,d,e,f,g,h): untouched(p)
    report={'timestampUtc':datetime.now(timezone.utc).isoformat(),'gameLaunched':False,
            'realGameChanged':False,'tests':reports}
    (ROOT/'logs/native-installer-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'PASS {len(reports)} installer operations. Evidence: {base}')


if __name__ == '__main__': main()
