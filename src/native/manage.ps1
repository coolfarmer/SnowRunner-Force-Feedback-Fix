#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('Check','Install','Disable','Enable','Status','Uninstall')]
    [string]$Action = 'Check',
    [string]$GameDirectory,
    [ValidateSet('fr','en')][string]$Language = 'en',
    [switch]$RemoveLoader
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
. (Join-Path $PSScriptRoot 'i18n.ps1')
Initialize-Language $Language
try {
Set-StrictMode -Version Latest
$product = 'SnowRunnerFFBFix'
$names = @('dinput8.dll','SnowRunnerFFBFix.asi')
$packageRoot = Split-Path -Parent $PSScriptRoot
$payloadRoot = Join-Path $packageRoot 'Payload'
try { $package = Get-Content -LiteralPath (Join-Path $packageRoot 'package.json') -Raw | ConvertFrom-Json }
catch { Fail 'missingPackage' }
. (Join-Path $PSScriptRoot 'steam-paths.ps1')

function Get-Hash([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-','').ToLowerInvariant()
    } finally { $algorithm.Dispose(); $stream.Dispose() }
}
function Assert-PlainFile([string]$Path) {
    if (Test-Path -LiteralPath $Path) {
        $item = Get-Item -LiteralPath $Path -Force
        if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            Fail 'notRegular' @($Path)
        }
    }
}
function Find-Game {
    $roots = @()
    $steam = Get-ItemProperty -LiteralPath 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue
    if ($steam -and $steam.PSObject.Properties['SteamPath']) { $roots += $steam.SteamPath }
    foreach ($key in @('HKLM:\SOFTWARE\WOW6432Node\Valve\Steam','HKLM:\SOFTWARE\Valve\Steam')) {
        $machineSteam = Get-ItemProperty -LiteralPath $key -ErrorAction SilentlyContinue
        if ($machineSteam -and $machineSteam.PSObject.Properties['InstallPath']) { $roots += $machineSteam.InstallPath }
    }
    $found = @(Find-SnowRunnerDirectories -SteamRoots $roots)
    if ($found.Count -eq 0) { Fail 'notFound' }
    if ($found.Count -gt 1) {
        Fail 'multipleGames' @(($found -join "`n"))
    }
    Write-Host (T 'detectedDirectory' @($found[0]))
    return $found[0]
}
if (!$GameDirectory) { $GameDirectory = Find-Game }
$bin = [IO.Path]::GetFullPath($GameDirectory).TrimEnd('\','/')
if (!(Test-Path -LiteralPath (Join-Path $bin 'SnowRunner.exe'))) {
    $bin = Join-Path $bin 'Sources\Bin'
}
if (!(Test-Path -LiteralPath $bin -PathType Container)) { Fail 'missingExe' @($bin) }
$bin = (Resolve-Path -LiteralPath $bin).ProviderPath.TrimEnd('\','/')
if (!(Test-Path -LiteralPath (Join-Path $bin 'SnowRunner.exe') -PathType Leaf)) { Fail 'missingExe' @($bin) }
# Reject junctions/symlinks anywhere in the installation path before changing files.
$ancestor = Get-Item -LiteralPath $bin -Force
while ($ancestor) {
    if ($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint) { Fail 'reparsePath' @($ancestor.FullName) }
    $ancestor = $ancestor.Parent
}
function Target([string]$Name) {
    if ($Name -notin @('dinput8.dll','SnowRunnerFFBFix.asi','SnowRunnerFFBFix.disabled',
                      'SnowRunnerFFBFix.log','SnowRunnerFFBFix.install.json','SnowRunner.exe')) {
        Fail 'unexpectedFilename'
    }
    $p = [IO.Path]::GetFullPath((Join-Path $bin $Name))
    if ([IO.Path]::GetDirectoryName($p) -ne $bin) { Fail 'escapedPath' }
    Assert-PlainFile $p
    return $p
}
$receiptPath = Target 'SnowRunnerFFBFix.install.json'
$marker = Target 'SnowRunnerFFBFix.disabled'
$markerText = 'SnowRunnerFFBFix disabled by manage.ps1'
if ($Action -eq 'Status') {
    Write-Output (T 'gameDirectory' @(''))
    Write-Output $bin
    Write-Output ''
    $installed = Test-Path -LiteralPath $receiptPath
    $disabled = Test-Path -LiteralPath $marker
    $yesNo = if ($installed) { T 'yes' } else { T 'no' }
    Write-Output (T 'installed' @($yesNo))
    $yesNo = if ($disabled) { T 'yes' } else { T 'no' }
    Write-Output (T 'disabledNext' @($yesNo))
    Write-Output ''
    if ($installed) { Show-PluginStatus (Target 'SnowRunnerFFBFix.log') }
    else { Write-Output (T 'notInstalledStatus') }
    exit 0
}
if ($Action -ne 'Check' -and (Get-Process -Name SnowRunner -ErrorAction SilentlyContinue)) {
    Fail 'closeGame'
}

if ($Action -in @('Check','Install')) {
    if ((Get-Hash (Target 'SnowRunner.exe')) -ne $package.gameSha256) {
        Fail 'unknownGame'
    }
    foreach ($name in $names) {
        $source = Join-Path $payloadRoot $name
        if (!(Test-Path -LiteralPath $source -PathType Leaf)) { Fail 'packageHash' @($name) }
        Assert-PlainFile $source
        if ((Get-Hash $source) -ne $package.files."Payload/$name") { Fail 'packageHash' @($name) }
        $dest = Target $name
        if (Test-Path -LiteralPath $dest) {
            if ($name -ne 'dinput8.dll' -or (Get-Hash $dest) -ne $package.files."Payload/$name") {
                Fail 'existingFile' @($dest)
            }
        }
    }
    # Unknown configuration may disable ASI loading or enable unrelated loader features.
    foreach ($relative in @('global.ini','dinput8.ini','dinput8Hooked.dll','scripts\global.ini',
                            'plugins\global.ini','update\global.ini','scripts\dinput8.ini',
                            'plugins\dinput8.ini','update\dinput8.ini')) {
        if (Test-Path -LiteralPath (Join-Path $bin $relative)) {
            Fail 'loaderConfig' @($relative)
        }
    }
    if (Test-Path -LiteralPath $receiptPath) { Fail 'receiptExists' }
    if (Test-Path -LiteralPath $marker) { Fail 'markerExists' }
    if ($Action -eq 'Check') {
        Write-Output (T 'checkOk')
        Write-Output ''
        Write-Output (T 'checkDetails')
        exit 0
    }
    $created = [Collections.Generic.List[string]]::new()
    $entries = @()
    try {
        foreach ($name in $names) {
            $dest = Target $name
            $owned = !(Test-Path -LiteralPath $dest)
            if ($owned) {
                # Copy without overwrite, including a file that appears after preflight.
                [IO.File]::Copy((Join-Path $payloadRoot $name), $dest, $false)
                $created.Add($name)
            }
            $entries += [pscustomobject]@{ name=$name; sha256=$package.files."Payload/$name"; owned=$owned }
        }
        $receipt = [pscustomobject]@{product=$product; version=$package.version; files=$entries}
        $bytes = [Text.Encoding]::UTF8.GetBytes(($receipt | ConvertTo-Json -Depth 5))
        $stream = [IO.File]::Open($receiptPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        $created.Add('SnowRunnerFFBFix.install.json')
        try { $stream.Write($bytes,0,$bytes.Length) } finally { $stream.Dispose() }
    } catch {
        foreach ($name in $created) {
            $dest = Target $name
            if (Test-Path -LiteralPath $dest) {
                # Never delete a binary that another actor changed during installation.
                if ($name -eq 'SnowRunnerFFBFix.install.json' -or (Get-Hash $dest) -eq $package.files."Payload/$name") {
                    Remove-Item -LiteralPath $dest
                }
            }
        }
        throw
    }
    Write-Output (T 'installOk')
    Write-Output ''
    Write-Output (T 'installDirectoryLabel')
    Write-Output $bin
    Write-Output ''
    Write-Output (T 'installNextStep')
    exit 0
}

if (!(Test-Path -LiteralPath $receiptPath)) { Fail 'noReceipt' }
try { $receipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json }
catch { Fail 'invalidReceipt' }
if ($receipt.product -ne $product -or @($receipt.files).Count -ne 2 -or
    (($receipt.files.name | Sort-Object) -join ',') -ne (($names | Sort-Object) -join ',')) {
    Fail 'invalidReceipt'
}
foreach ($entry in $receipt.files) {
    if ($entry.sha256 -notmatch '^[a-f0-9]{64}$' -or $entry.owned -isnot [bool]) { Fail 'invalidReceipt' }
}
if ($Action -eq 'Disable') {
    if (!(Test-Path -LiteralPath $marker)) { [IO.File]::WriteAllText($marker,$markerText) }
    Write-Output (T 'disableOk')
    Write-Output ''
    Write-Output (T 'disableDetails')
    exit 0
}
if ($Action -eq 'Enable') {
    if (Test-Path -LiteralPath $marker) {
        if ([IO.File]::ReadAllText($marker) -ne $markerText) { Fail 'unknownMarker' }
        Remove-Item -LiteralPath $marker
    }
    Write-Output (T 'enableOk')
    Write-Output ''
    Write-Output (T 'enableDetails')
    exit 0
}
if ($Action -eq 'Uninstall') {
    # Complete preflight before deleting anything. No recursive deletion.
    foreach ($entry in $receipt.files) {
        if ($entry.name -eq 'dinput8.dll' -and !$RemoveLoader) { continue }
        $dest = Target $entry.name
        if ($entry.owned -and (Test-Path -LiteralPath $dest) -and (Get-Hash $dest) -ne $entry.sha256) {
            Fail 'modifiedFile' @($dest)
        }
    }
    $otherPlugins = @()
    if ($RemoveLoader) {
        foreach ($dir in @($bin,(Join-Path $bin 'scripts'),(Join-Path $bin 'plugins'),(Join-Path $bin 'update'))) {
            if (Test-Path -LiteralPath $dir) {
                $otherPlugins += @(Get-ChildItem -LiteralPath $dir -Filter '*.asi' -File -Recurse |
                    Where-Object FullName -NE (Target 'SnowRunnerFFBFix.asi'))
            }
        }
    }
    foreach ($entry in $receipt.files) {
        if ($entry.name -eq 'dinput8.dll' -and !$RemoveLoader) {
            Write-Output (T 'loaderKept'); continue
        }
        $dest = Target $entry.name
        if (!$entry.owned) {
            if ($entry.name -eq 'dinput8.dll') { Write-Output (T 'preexistingLoader') }
            continue
        }
        if ($entry.name -eq 'dinput8.dll' -and $otherPlugins.Count) {
            Write-Output (T 'sharedLoader'); continue
        }
        if (Test-Path -LiteralPath $dest) {
            Remove-Item -LiteralPath $dest
            if ($entry.name -eq 'dinput8.dll') { Write-Output (T 'loaderRemoved') }
        }
    }
    if ((Test-Path -LiteralPath $marker) -and [IO.File]::ReadAllText($marker) -eq $markerText) {
        Remove-Item -LiteralPath $marker
    }
    Remove-Item -LiteralPath $receiptPath
    Write-Output ''
    Write-Output (T 'uninstallOk')
    Write-Output ''
    Write-Output (T 'uninstallDetails')
}

} catch {
    Show-LocalizedError $_
    exit 1
}
