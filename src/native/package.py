"""Assemble a deployable package containing only release files, never fixtures."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT/'dist/SnowRunnerFFBFix-0.2.0'


def main():
    internal = DEST/'Sources'
    internal.mkdir(parents=True, exist_ok=True)
    files = {
        'SnowRunnerFFBFix.asi': ROOT/'build/native/SnowRunnerFFBFix.asi',
        'dinput8.dll': ROOT/'vendor/ultimate-asi-loader/dinput8.dll',
        'manage.ps1': ROOT/'src/native/manage.ps1',
        'steam-paths.ps1': ROOT/'src/native/steam-paths.ps1',
        'menu.ps1': ROOT/'src/native/menu.ps1',
        'i18n.ps1': ROOT/'src/native/i18n.ps1',
        'messages.json': ROOT/'src/native/messages.json',
        'README.fr.md': ROOT/'docs/usage.fr.md',
        'README.en.md': ROOT/'docs/usage.en.md',
        'LICENSE-MinHook.txt': ROOT/'vendor/minhook/LICENSE.txt',
        'LICENSE-ASI-Loader.txt': ROOT/'vendor/ultimate-asi-loader/LICENSE.txt',
    }
    for name, source in files.items():
        if name.endswith('.ps1'):
            # Windows PowerShell 5.1 needs a BOM for accented French text.
            (internal/name).write_text(source.read_text(encoding='utf-8'),encoding='utf-8-sig')
        else: shutil.copyfile(source,internal/name)
    entrypoint = 'Install.cmd'
    (DEST/entrypoint).write_text('@echo off\nsetlocal\ntitle SnowRunner\n'
        'if not exist "%~dp0Sources\\menu.ps1" (\n'
        '  echo Dossier Sources manquant / Sources folder missing.\n'
        '  echo Extrayez le ZIP complet / Extract the complete ZIP.\n'
        '  echo Entree pour fermer / Press Enter to close.\n'
        '  set /p "_ffb_close="\n  exit /b 1\n)\n'
        'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Sources\\menu.ps1" %*\n'
        'if errorlevel 1 exit /b 1\n',encoding='ascii')
    cfg = json.loads((ROOT/'src/native/game-profile.json').read_text())
    manifest = {'product':'SnowRunnerFFBFix','version':'0.2.0','packageRevision':1,'gameVersion':cfg['game_version'],
                'gameSha256':cfg['game_sha256'].lower(),
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
