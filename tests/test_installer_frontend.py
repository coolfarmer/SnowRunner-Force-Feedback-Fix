"""Check the published C# process boundary on synthetic game files only."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = Path(tempfile.mkdtemp(prefix='frontend-', dir=ROOT/'build/native'))
    package = base/"Package avec accents é & [crochets] ' apostrophe"
    shutil.copytree(ROOT/'dist/SnowRunnerFFBFix-0.2.1', package)
    sources = package/'Sources'
    exe = sources/'Installer/SnowRunnerFFBFix.Setup.exe'
    game = base/"Jeu é & [x]; $variable ' apostrophe/Sources/Bin"
    game.mkdir(parents=True)
    fake = b'frontend fixture; never executed'
    (game/'SnowRunner.exe').write_bytes(fake)
    manifest = json.loads((sources/'package.json').read_text())
    manifest['gameSha256'] = hashlib.sha256(fake).hexdigest()
    (sources/'package.json').write_text(json.dumps(manifest))
    results = []

    def run(name, args=(), inputs='', code=0):
        env = dict(os.environ, DOTNET_ROOT=str(base/'absent-runtime'),
                   DOTNET_ROOT_X64=str(base/'absent-runtime'), DOTNET_MULTILEVEL_LOOKUP='0')
        p = subprocess.run([str(exe), *args], input=inputs, cwd=base, env=env,
                           capture_output=True, text=True, encoding='utf-8', timeout=30)
        assert p.returncode == code, (name, p.stdout, p.stderr)
        assert not p.stderr, (name, p.stderr)
        results.append(name)
        print('PASS', name, flush=True)
        return p.stdout

    args = ['-Language', 'fr', '-GameDirectory', str(game)]
    out = run('preview-does-not-install', [*args, '--preview'])
    assert str(game) in out and 'Installer le correctif' in out
    assert list(game.iterdir()) == [game/'SnowRunner.exe']
    run('invalid-argument', ['-Action', 'Install'], code=2)
    run('missing-path-argument', ['-GameDirectory'], code=2)
    run('invalid-language', ['-Language', 'de'], code=2)
    out = run('literal-path-with-metacharacters', [*args, '--plain'], '1\n\n0\n')
    assert 'Installation terminée.\n\nDossier d\'installation :\n'+str(game)+'\n\nLancez le jeu normalement depuis Steam.' in out
    assert (game/'SnowRunnerFFBFix.asi').is_file()
    out = run('literal-path-uninstall-without-dll-question', args, '3\n')
    assert 'Désinstallation terminée.' in out and 'dinput8.dll' not in out
    assert list(game.iterdir()) == [game/'SnowRunner.exe']

    # Drain both output streams without deadlock; do not interpret backend markup.
    (sources/'Scripts/manage.ps1').write_text(
        'param([string]$Action,[string]$Language,[string]$GameDirectory)\n'
        '[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)\n'
        '[Console]::Out.WriteLine("[red]literal backend text[/]")\n'
        '[Console]::Error.WriteLine(("e" * 100000))\nexit 7\n', encoding='utf-8-sig')
    out = run('backend-failure-and-concurrent-output', args, '2\n\n0\n')
    assert '[red]literal backend text[/]' in out and 'e'*100000 in out
    assert "L'opération n'a pas abouti" in out
    (sources/'Scripts/manage.ps1').unlink()
    out = run('missing-backend', args, '1\n\n0\n')
    assert 'Le paquet est incomplet' in out
    assert list(game.iterdir()) == [game/'SnowRunner.exe']
    (sources/'Locales/messages.json').write_text('{}')
    out = run('malformed-catalog', args, '\n', code=1)
    assert 'Le paquet est incomplet' in out
    (sources/'Locales/messages.json').unlink()
    out = run('missing-catalog', args, '\n', code=1)
    assert 'Le paquet est incomplet' in out
    report = {'cases': results, 'realGameChanged': False,
              'publishedExeSha256': hashlib.sha256(exe.read_bytes()).hexdigest()}
    (ROOT/'logs/installer-frontend-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f'PASS {len(results)} frontend boundary cases')


if __name__ == '__main__':
    main()
