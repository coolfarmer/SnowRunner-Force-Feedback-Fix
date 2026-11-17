"""Exercise both player languages, operation failures and translated runtime logs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    base=Path(tempfile.mkdtemp(prefix='languages-',dir=ROOT/'build/native'))
    catalog=json.loads((ROOT/'src/native/messages.json').read_text(encoding='utf-8'))
    assert catalog['fr'].keys()==catalog['en'].keys()
    for key in catalog['fr']:
        assert re.findall(r'\{\d+\}',catalog['fr'][key])==re.findall(r'\{\d+\}',catalog['en'][key]),key
    results=[]
    for lang,choice in [('fr','1'),('en','2')]:
        pkg=base/lang/'Package with spaces & accents'
        shutil.copytree(ROOT/'dist/SnowRunnerFFBFix-0.2.0',pkg)
        sources=pkg/'Sources'
        manifest=json.loads((sources/'package.json').read_text())
        game=base/lang/'Game/Sources/Bin'
        game.mkdir(parents=True)
        fake=b'fixture game; never launched'
        (game/'SnowRunner.exe').write_bytes(fake)
        manifest['gameSha256']=hashlib.sha256(fake).hexdigest()
        (sources/'package.json').write_text(json.dumps(manifest))
        t=catalog[lang]

        def inspect(name,p,expected,code=0,menu=False):
            assert p.returncode==code,p.stdout+p.stderr
            assert not p.stderr,p.stderr
            text=p.stdout.split('> ',1)[-1] if menu else p.stdout
            assert expected in text,(name,text)
            assert 'CategoryInfo' not in text and 'FullyQualifiedErrorId' not in text
            assert 'Physical validation' not in text
            other=catalog['en' if lang=='fr' else 'fr']
            for key,value in other.items():
                if value==t[key] or len(value)<24 or '{' in value or '\n' in value: continue
                assert value not in text,(name,'wrong language',key,text)
            results.append({'language':lang,'case':name,'exitCode':p.returncode})
            return text

        def operation(action,expected,code=0,target=game):
            p=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                str(sources/'Scripts/manage.ps1'),'-Action',action,'-Language',lang,'-GameDirectory',str(target)],
                capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=25)
            return inspect(action,p,expected,code)

        def menu(inputs,expected,code=0):
            command='cmd.exe /d /s /c ""'+str(pkg/'Install.cmd')+'" -GameDirectory "'+str(game)+'""'
            p=subprocess.run(command,input=choice+'\n'+inputs,capture_output=True,text=True,
                             encoding='utf-8',errors='replace',timeout=30)
            return inspect('menu',p,expected,code,True)

        menu('5\n\n0\n',t['helpText'])
        menu('4\n1\n\n0\n0\n',t['checkOk'])
        menu('1\n\n0\n',t['installOk'].format(game))
        assert (game/'SnowRunnerFFBFix.asi').exists()
        menu('1\n\n0\n',t['existingFile'].format(game/'SnowRunnerFFBFix.asi'))
        operation('Status',t['installed'].format(t['yes']))
        operation('Disable',t['disableOk'])
        operation('Enable',t['enableOk'])
        log=game/'SnowRunnerFFBFix.log'
        for line,state,detail in [
            ('ACTIVE: guarded constructor initialization','activeState',None),
            ('DISABLED: marker file exists','disabledState',None),
            ('DISARMED: memory initialization failed','disarmedState',None),
            ('INACTIVE: unknown game executable SHA256','inactiveState','inactiveGame'),
            ('INACTIVE: unverified Logitech SDK','inactiveState','inactiveSdk'),
            ('INACTIVE: loaded code mismatch','inactiveState','inactiveCode'),
            ('INACTIVE: MH_Initialize error','inactiveState','inactiveHook')]:
            log.write_text('SnowRunnerFFBFix 0.1.0 experimental\npid=999999\n'+line+'\n'+
                f'armed={int(state=="activeState")}\napplied=3\nfailed={int(state=="disarmedState")}\nskipped=0\n'+
                'Physical validation of this native plugin: pending\n')
            out=operation('Status',t[state])
            assert t['historicalLog'] in out and t['physicalNote'] in out
            if detail: assert t[detail] in out
        log.write_text('broken log')
        operation('Status',t['unknownLog'])
        out=menu('3\n\n\n0\n',t['uninstallOk'])
        assert t['keepLoaderQuestion'] in out and t['keepLoaderChoices'] in out
        assert t['keepLoaderPrompt'] in out and t['loaderKept'] in out
        assert (game/'dinput8.dll').exists() and not (game/'SnowRunnerFFBFix.asi').exists()
        operation('Status',t['notInstalledStatus'])
        operation('Disable',t['noReceipt'],1)
        operation('Check',t['missingExe'].format(base/'missing/Sources/Bin'),1,base/'missing')
        (game/'SnowRunner.exe').write_bytes(b'updated')
        menu('1\n\n0\n',t['unknownGame'])
        (game/'SnowRunner.exe').write_bytes(fake)
        # A legacy metadata key cannot reintroduce the removed SDK requirement.
        manifest['sdkSha256']='0'*64
        manifest['sdkPath']=str(base/'missing-logitech-sdk.dll')
        (sources/'package.json').write_text(json.dumps(manifest))
        operation('Check',t['checkOk'])
        # Malformed package files get a translated message, not a PowerShell stack.
        (sources/'package.json').write_text('{invalid')
        menu('1\n\n0\n',t['missingPackage'])
        # OS exceptions are mapped independently of Windows display language.
        probe=base/lang/'error-probe.ps1'
        probe.write_text("param([string]$Sources,[string]$Language)\n"
            "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)\n"
            ". (Join-Path $Sources 'Scripts/i18n.ps1')\nInitialize-Language $Language\n"
            "try { throw [UnauthorizedAccessException]::new('RAW OS ERROR MUST NOT BE DISPLAYED') } catch { Show-LocalizedError $_ }\n",
            encoding='utf-8-sig')
        p=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(probe),'-Sources',str(sources),'-Language',lang],
                         capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=20)
        out=inspect('access-error',p,t['accessDenied'])
        assert 'RAW OS ERROR' not in out
        (sources/'Locales/messages.json').rename(sources/'Locales/messages.saved')
        # Resource loading fallback is also in the selected language.
        fallback='Le paquet est incomplet' if lang=='fr' else 'The package is incomplete'
        menu('\n',fallback,1)
        print('PASS',lang,'operations, errors, log states and resource fallback',flush=True)

    report={'observedUtc':datetime.now(timezone.utc).isoformat(),'cases':results,'realGameChanged':False,
            'catalogKeysPerLanguage':len(catalog['fr'])}
    (ROOT/'logs/native-language-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'PASS {len(results)} localized cases; {len(catalog["fr"])} matching translation keys')


if __name__=='__main__': main()
