"""Assemble a deployable package containing only release files, never fixtures."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT/'dist/SnowRunnerFFBFix-0.2.1'


def main():
    internal = DEST/'Sources'
    internal.mkdir(parents=True, exist_ok=True)
    files = {
        'Payload/SnowRunnerFFBFix.asi': ROOT/'build/native/SnowRunnerFFBFix.asi',
        'Payload/dinput8.dll': ROOT/'vendor/ultimate-asi-loader/dinput8.dll',
        'Scripts/manage.ps1': ROOT/'src/native/manage.ps1',
        'Scripts/steam-paths.ps1': ROOT/'src/native/steam-paths.ps1',
        'Scripts/menu.ps1': ROOT/'src/native/menu.ps1',
        'Installer/SnowRunnerFFBFix.Setup.exe': ROOT/'build/installer/SnowRunnerFFBFix.Setup.exe',
        'Scripts/i18n.ps1': ROOT/'src/native/i18n.ps1',
        'Locales/messages.json': ROOT/'src/native/messages.json',
        'Docs/README.fr.md': ROOT/'docs/usage.fr.md',
        'Docs/README.en.md': ROOT/'docs/usage.en.md',
        'Licenses/LICENSE-MinHook.txt': ROOT/'vendor/minhook/LICENSE.txt',
        'Licenses/LICENSE-ASI-Loader.txt': ROOT/'vendor/ultimate-asi-loader/LICENSE.txt',
        'Licenses/LICENSE-Spectre.Console.txt': ROOT/'vendor/spectre-console/LICENSE.txt',
        'Licenses/LICENSE-dotnet.txt': ROOT/'build/nuget/microsoft.netcore.app.runtime.win-x64/10.0.12/LICENSE.TXT',
        'Licenses/THIRD-PARTY-NOTICES-dotnet.txt': ROOT/'build/nuget/microsoft.netcore.app.runtime.win-x64/10.0.12/THIRD-PARTY-NOTICES.TXT',
    }
    for name, source in files.items():
        (internal/name).parent.mkdir(parents=True, exist_ok=True)
        if name.endswith('.ps1'):
            # Windows PowerShell 5.1 needs a BOM for accented French text.
            (internal/name).write_text(source.read_text(encoding='utf-8'),encoding='utf-8-sig')
        else: shutil.copyfile(source,internal/name)
    entrypoint = 'Install.cmd'
    (DEST/entrypoint).write_text('@echo off\nsetlocal\ntitle SnowRunner FFB Fix\n'
        'if not exist "%~dp0Sources\\Installer\\SnowRunnerFFBFix.Setup.exe" (\n'
        '  echo Dossier Sources manquant / Sources folder missing.\n'
        '  echo Extrayez le ZIP complet / Extract the complete ZIP.\n'
        '  echo Entree pour fermer / Press Enter to close.\n'
        '  set /p "_ffb_close="\n  exit /b 1\n)\n'
        '"%~dp0Sources\\Installer\\SnowRunnerFFBFix.Setup.exe" %*\n'
        'if errorlevel 1 exit /b 1\n',encoding='ascii')
    cfg = json.loads((ROOT/'src/native/game-profile.json').read_text())
    loaders = json.loads((ROOT/'src/native/compatible-loaders.json').read_text())
    assert all(entry['architecture'] == 'x64' and len(entry['sha256']) == 64 for entry in loaders)
    assert hashlib.sha256((internal/'Payload/dinput8.dll').read_bytes()).hexdigest() in {
        entry['sha256'] for entry in loaders}
    manifest = {'product':'SnowRunnerFFBFix','version':'0.2.1','packageRevision':1,'gameVersion':cfg['game_version'],
                'gameSha256':cfg['game_sha256'].lower(),
                'compatibleLoaders':loaders,
                'entrypoint':{'name':entrypoint,'sha256':hashlib.sha256((DEST/entrypoint).read_bytes()).hexdigest()},
                'files':{name:hashlib.sha256((internal/name).read_bytes()).hexdigest() for name in files}}
    (internal/'package.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive = DEST.parent / (DEST.name + '.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        # Explicit whitelist: old files left in staging cannot enter the archive.
        z.write(DEST/entrypoint,DEST.name+'/'+entrypoint)
        for name in [*files,'package.json']: z.write(internal/name,DEST.name+'/Sources/'+name)
    print(json.dumps({'archive':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
                      'bytes':archive.stat().st_size},indent=2))


if __name__ == '__main__': main()
