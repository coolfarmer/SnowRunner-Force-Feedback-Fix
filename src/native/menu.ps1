#requires -Version 5.1
param([string]$GameDirectory, [string]$Language)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$selectedDirectory = $GameDirectory

function Select-Language {
    while ($true) {
        Write-Host "`nChoisissez votre langue / Choose your language`n"
        Write-Host '  1  Français'
        Write-Host '  2  English'
        Write-Host '  0  Quitter / Exit'
        Write-Host '> ' -NoNewline
        $answer = [Console]::ReadLine()
        if ($null -eq $answer -or $answer.Trim() -eq '0') { exit 0 }
        switch ($answer.Trim()) {
            '1' { return 'fr' }
            '2' { return 'en' }
            default { Write-Host 'Choisissez 1 ou 2 / Choose 1 or 2.' }
        }
    }
}
if ($Language -notin @('fr','en')) { $Language = Select-Language }
try {
    . (Join-Path $PSScriptRoot 'i18n.ps1')
    Initialize-Language $Language
    try { [Console]::Title = T 'title' } catch { }
} catch {
    if ($Language -eq 'fr') { Write-Host "Le paquet est incomplet ou illisible. Extrayez à nouveau le ZIP complet.`n`nAppuyez sur Entrée pour fermer." }
    else { Write-Host "The package is incomplete or unreadable. Extract the complete ZIP again.`n`nPress Enter to close." }
    $null = [Console]::ReadLine()
    exit 1
}
function Invoke-Operation([string]$Action) {
    Write-Host ''
    try {
        foreach ($file in @('manage.ps1','../package.json','steam-paths.ps1','../Locales/messages.json','i18n.ps1')) {
            if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot $file) -PathType Leaf)) { Fail 'missingPackage' }
        }
        $arguments = @('-NoProfile','-ExecutionPolicy','Bypass','-File',
                       (Join-Path $PSScriptRoot 'manage.ps1'),'-Action',$Action,'-Language',$script:Language)
        if ($script:selectedDirectory) { $arguments += @('-GameDirectory',$script:selectedDirectory) }
        if ($Action -eq 'Uninstall') {
            Write-Host (T 'keepLoaderQuestion')
            Write-Host ''
            Write-Host (T 'keepLoaderExplanation')
            Write-Host ''
            Write-Host (T 'keepLoaderChoices')
            while ($true) {
                Write-Host (T 'keepLoaderPrompt') -NoNewline
                $answer = [Console]::ReadLine()
                if ($null -eq $answer) { return }
                $answer = $answer.Trim()
                if ($answer -eq '' -or $answer -eq '1') { break }
                if ($answer -eq '2') { $arguments += '-RemoveLoader'; break }
                if ($answer -eq '0') { return }
                Write-Host (T 'invalidChoice')
            }
        }
        & "$PSHOME\powershell.exe" @arguments
        if ($LASTEXITCODE -ne 0) { Write-Host (T 'operationFailed') -ForegroundColor Yellow }
    } catch { Show-LocalizedError $_ }
    Write-Host "`n$(T 'returnPrompt')"
    $null = [Console]::ReadLine()
}
try {
    $screen = 'main'
    while ($true) {
        Write-Host "`n=================================================="
        Write-Host "  $(T 'title')"
        Write-Host '=================================================='
        if ($selectedDirectory) { Write-Host (T 'selectedDirectory' @($selectedDirectory)) }
        else { Write-Host (T 'autoDirectory') }
        if ($screen -eq 'main') { $entries = @('install','status','uninstall','options','help','language') }
        else { $entries = @('check','disable','enable','chooseDirectory') }
        Write-Host ''
        for ($i=0; $i -lt $entries.Count; $i++) { Write-Host ('  {0}  {1}' -f ($i+1),(T $entries[$i])) }
        $zero = if ($screen -eq 'main') { T 'quit' } else { T 'back' }
        Write-Host "  0  $zero"
        Write-Host "`n$(T 'closeGameHint')"
        Write-Host "`n$(T 'choice')" -NoNewline
        $choice = [Console]::ReadLine()
        if ($null -eq $choice) { break }
        $choice = $choice.Trim()
        if ($screen -eq 'main') {
            switch ($choice) {
                '0' { exit 0 }
                '1' { Invoke-Operation 'Install' }
                '2' { Invoke-Operation 'Status' }
                '3' { Invoke-Operation 'Uninstall' }
                '4' { $screen = 'options' }
                '5' {
                    Write-Host "`n$(T 'helpText')"
                    Write-Host "`n$(T 'returnPrompt')"
                    $null = [Console]::ReadLine()
                }
                '6' {
                    $Language = Select-Language
                    Initialize-Language $Language
                    try { [Console]::Title = T 'title' } catch { }
                }
                default { Write-Host (T 'invalidChoice') }
            }
        } else {
            switch ($choice) {
                '0' { $screen = 'main' }
                '1' { Invoke-Operation 'Check' }
                '2' { Invoke-Operation 'Disable' }
                '3' { Invoke-Operation 'Enable' }
                '4' {
                    Write-Host "`n$(T 'directoryPrompt')"
                    Write-Host ''
                    Write-Host (T 'directoryReset')
                    Write-Host ''
                    $path = [Console]::ReadLine()
                    if ($null -eq $path) { exit 0 }
                    $selectedDirectory = $path.Trim().Trim('"')
                }
                default { Write-Host (T 'invalidChoice') }
            }
        }
    }
} catch {
    Show-LocalizedError $_
    Write-Host (T 'returnPrompt')
    $null = [Console]::ReadLine()
    exit 1
}
