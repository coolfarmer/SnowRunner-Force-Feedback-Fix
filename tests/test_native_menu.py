"""Drive the actual root CMD entrypoint through its menu on fake game folders."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = Path(tempfile.mkdtemp(prefix='menu-', dir=ROOT/'build/native'))
    package = base/'Dossier partage & espaces'
    shutil.copytree(ROOT/'dist/SnowRunnerFFBFix-0.2.0',package)
    assert {p.name for p in package.iterdir()} == {'Install.cmd','Sources'}
    internal = package/'Sources'
    assert {p.name for p in internal.iterdir()} == {
        'package.json', 'Installer', 'Payload', 'Scripts', 'Locales', 'Docs', 'Licenses'}
    manifest = json.loads((internal/'package.json').read_text())
    fake_exe = b'fake game; never executed'
    manifest['gameSha256'] = hashlib.sha256(fake_exe).hexdigest()
    (internal/'package.json').write_text(json.dumps(manifest))
    game = base/'Faux jeu avec espaces/Sources/Bin'
    game.mkdir(parents=True)
    (game/'SnowRunner.exe').write_bytes(fake_exe)
    results = []

    def run(name, inputs, target=game, powershell=False):
        if powershell:
            command = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                       '-File', str(internal/'Scripts/menu.ps1')]
            if target is not None: command += ['-GameDirectory', str(target)]
        else:
            command = 'cmd.exe /d /s /c ""'+str(package/'Install.cmd')+'"'
            if target is not None: command += ' -GameDirectory "'+str(target)+'"'
            command += '"'
        p = subprocess.run(command, input=('2\n'+inputs) if inputs else inputs, text=True, encoding='utf-8', errors='replace',
                           capture_output=True,timeout=35,cwd=base)
        assert p.returncode == 0, p.stdout+p.stderr
        results.append({'name':name,'exitCode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        print('PASS',name,flush=True)
        return p.stdout+p.stderr

    assert 'Install the fix' in run('quit-without-change','0\n')
    run('invalid-and-empty-choices','x\n\n0\n')
    assert len(list(game.iterdir())) == 1
    assert 'Check passed: compatible files' in run('check-through-options','4\n1\n\n0\n0\n')
    assert len(list(game.iterdir())) == 1
    assert 'Installation complete.' in run('install','1\n\n0\n')
    assert (game/'SnowRunnerFFBFix.asi').exists()
    assert 'Installed: yes' in run('status','2\n\n0\n')
    run('disable','4\n2\n\n0\n0\n')
    assert (game/'SnowRunnerFFBFix.disabled').exists()
    run('enable','4\n3\n\n0\n0\n')
    assert not (game/'SnowRunnerFFBFix.disabled').exists()
    assert 'Existing file will not be overwritten' in run('refusal-keeps-menu-open','1\n\n0\n')
    before={p.name:p.read_bytes() for p in game.iterdir()}
    run('cancel-uninstall','3\n0\n0\n')
    assert {p.name:p.read_bytes() for p in game.iterdir()}==before
    run('uninstall-eof','3\n')
    assert {p.name:p.read_bytes() for p in game.iterdir()}==before
    out=run('uninstall-default-keeps-loader','3\n\n\n0\n')
    assert 'Yes, keep (default)' in out
    assert sorted(p.name for p in game.iterdir())==['SnowRunner.exe','dinput8.dll']

    # A separate fresh installation owns its loader and can explicitly remove it.
    remove_game=base/'Removal/Sources/Bin'
    remove_game.mkdir(parents=True)
    (remove_game/'SnowRunner.exe').write_bytes(fake_exe)
    run('install-for-explicit-removal','1\n\n0\n',remove_game)
    out=run('uninstall-explicit-removal','3\n2\n\n0\n',remove_game)
    assert 'removed at your request' in out
    assert sorted(p.name for p in remove_game.iterdir())==['SnowRunner.exe']
    run('install-for-explicit-keep','1\n\n0\n',remove_game)
    run('uninstall-invalid-then-explicit-keep','3\nx\n1\n\n0\n',remove_game)
    assert sorted(p.name for p in remove_game.iterdir())==['SnowRunner.exe','dinput8.dll']
    run('reinstall-with-preexisting-loader','1\n\n0\n',remove_game)
    out=run('uninstall-protects-preexisting-loader','3\n2\n\n0\n',remove_game)
    assert 'present before the fix' in out
    assert sorted(p.name for p in remove_game.iterdir())==['SnowRunner.exe','dinput8.dll']
    # Manual path is input data, never a command or script fragment.
    assert 'Check passed: compatible files' in run('manual-folder','4\n4\n"'+str(game)+'"\n1\n\n0\n0\n',None)
    run('help','5\n\n0\n')
    changed = run('change-language-to-french','6\n1\n4\n1\n\n0\n0\n')
    french = changed.rsplit('> ',1)[-1]
    assert 'Vérification réussie' in french and 'Installer le correctif' in french
    assert 'Check passed:' not in french and 'Install the fix' not in french
    run('stdin-eof','')
    # The documented PowerShell fallback must resolve the same reorganized resources.
    fallback_game = base/'Fallback game/Sources/Bin'
    fallback_game.mkdir(parents=True)
    (fallback_game/'SnowRunner.exe').write_bytes(fake_exe)
    for name, inputs, expected in [
        ('check', '4\n1\n\n0\n0\n', 'Check passed: compatible files'),
        ('install', '1\n\n0\n', 'Installation complete.'),
        ('status', '2\n\n0\n', 'Installed: yes'),
        ('disable', '4\n2\n\n0\n0\n', 'Disabled for next launch.'),
        ('enable', '4\n3\n\n0\n0\n', 'Enabled for next launch.'),
        ('help', '5\n\n0\n', 'Sources\\Docs\\README.en.md'),
        ('uninstall', '3\n2\n\n0\n', 'removed at your request'),
    ]:
        assert expected in run('powershell-'+name, inputs, fallback_game, powershell=True)
    assert list(fallback_game.iterdir()) == [fallback_game/'SnowRunner.exe']
    assert (game/'SnowRunner.exe').read_bytes()==fake_exe
    with zipfile.ZipFile(ROOT/'dist/SnowRunnerFFBFix-0.2.0.zip') as z:
        assert z.testzip() is None
        prefix='SnowRunnerFFBFix-0.2.0/'
        files=z.namelist()
        assert [n for n in files if '/' not in n[len(prefix):]]==[prefix+'Install.cmd']
        m=json.loads(z.read(prefix+'Sources/package.json'))
        assert m['version']=='0.2.0' and m['packageRevision']==4
        assert 'sdkPath' not in m and 'sdkSha256' not in m
        assert set(files)=={prefix+'Install.cmd',prefix+'Sources/package.json'} | {
            prefix+'Sources/'+name for name in m['files']}
        assert {p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()} == {
            name[len(prefix):] for name in files}
        for name,digest in m['files'].items():
            assert hashlib.sha256(z.read(prefix+'Sources/'+name)).hexdigest()==digest
        assert hashlib.sha256(z.read(prefix+m['entrypoint']['name'])).hexdigest()==m['entrypoint']['sha256']
        native=json.loads((ROOT/'logs/native-validation.json').read_text())
        assert m['files']['Payload/SnowRunnerFFBFix.asi']==native['pluginSha256']
    report={'observedUtc':datetime.now(timezone.utc).isoformat(),'cases':results,'realGameChanged':False,
            'pluginMatchesNativeValidation':True,'version':'0.2.0','packageRevision':4}
    (ROOT/'logs/native-menu-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'PASS {len(results)} menu cases and archive integrity')


if __name__ == '__main__': main()
