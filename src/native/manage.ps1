#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('Check','Install','Disable','Enable','Status','Uninstall')]
    [string]$Action = 'Check',
    [string]$GameDirectory,
    [ValidateSet('fr','en')][string]$Language = 'en',
    # Kept for older command-line callers. Cleanup is now automatic either way.
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
$loaderConfigPaths = @('global.ini','dinput8.ini','dinput8Hooked.dll','scripts\global.ini',
    'plugins\global.ini','update\global.ini','scripts\dinput8.ini',
    'plugins\dinput8.ini','update\dinput8.ini')

function Test-KnownLoaderHash([string]$Hash) {
    # Versions and filenames alone cannot establish the identity of a loader.
    if ($Hash -eq $package.files.'Payload/dinput8.dll') { return $true }
    if ($package.PSObject.Properties['compatibleLoaders']) {
        foreach ($loader in $package.compatibleLoaders) {
            if ($loader.architecture -eq 'x64' -and $loader.sha256 -eq $Hash) { return $true }
        }
    }
    return $false
}

function Get-StreamHash([IO.Stream]$Stream) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($algorithm.ComputeHash($Stream)).Replace('-','').ToLowerInvariant() }
    finally { $algorithm.Dispose() }
}

function Get-Hash([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    try { return Get-StreamHash $stream }
    finally { $stream.Dispose() }
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

function Test-LoaderUnused {
    # Do not follow junctions, ignore hidden plugins, or guess on unreadable trees.
    # This is a conservative dependency scan, not proof of every possible use.
    try {
        foreach ($relative in $loaderConfigPaths) {
            if (Test-Path -LiteralPath (Join-Path $bin $relative)) { return $false }
        }
        $pending = [Collections.Generic.Queue[string]]::new()
        $pending.Enqueue($bin)
        $count = 0
        while ($pending.Count) {
            $directory = $pending.Dequeue()
            if ((Get-Item -LiteralPath $directory -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                return $false
            }
            foreach ($item in Get-ChildItem -LiteralPath $directory -Force -ErrorAction Stop) {
                $count++
                if ($count -gt 10000 -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { return $false }
                if ($item.PSIsContainer) { $pending.Enqueue($item.FullName); continue }
                if (($item.Extension -ieq '.asi' -and $item.FullName -ine (Join-Path $bin 'SnowRunnerFFBFix.asi')) -or
                    $item.Extension -ieq '.cxx' -or $item.Name -ieq 'Xidi.64.dll') { return $false }
            }
        }
        return $true
    } catch { return $false }
}
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
            if ($name -ne 'dinput8.dll') { Fail 'existingFile' @($dest) }
            if (!(Test-KnownLoaderHash (Get-Hash $dest))) { Fail 'unknownLoader' }
        }
    }
    # Unknown configuration may disable ASI loading or enable unrelated loader features.
    foreach ($relative in $loaderConfigPaths) {
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
    $reusedLoader = $null
    try {
        foreach ($name in $names) {
            $dest = Target $name
            $owned = !(Test-Path -LiteralPath $dest)
            if ($owned) {
                # Copy without overwrite, including a file that appears after preflight.
                [IO.File]::Copy((Join-Path $payloadRoot $name), $dest, $false)
                $created.Add($name)
                $hash = $package.files."Payload/$name"
            } else {
                # Recheck files that appeared after preflight. Keep the reused
                # loader read-locked until the installation receipt is complete.
                if ($name -ne 'dinput8.dll') { Fail 'existingFile' @($dest) }
                $reusedLoader = [IO.File]::OpenRead($dest)
                $hash = Get-StreamHash $reusedLoader
                if (!(Test-KnownLoaderHash $hash)) { Fail 'unknownLoader' }
            }
            $entries += [pscustomobject]@{ name=$name; sha256=$hash; owned=$owned }
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
    } finally { if ($reusedLoader) { $reusedLoader.Dispose() } }
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
        if ($entry.name -eq 'dinput8.dll') { continue }
        $dest = Target $entry.name
        if ($entry.owned -and (Test-Path -LiteralPath $dest) -and (Get-Hash $dest) -ne $entry.sha256) {
            Fail 'modifiedFile' @($dest)
        }
    }
    $loaderEntry = $receipt.files | Where-Object name -EQ 'dinput8.dll'
    $removeOwnedLoader = $false
    if ($loaderEntry.owned) {
        try {
            $loaderPath = Target 'dinput8.dll'
            $removeOwnedLoader = (Test-Path -LiteralPath $loaderPath) -and
                (Test-KnownLoaderHash $loaderEntry.sha256) -and
                (Get-Hash $loaderPath) -eq $loaderEntry.sha256 -and (Test-LoaderUnused)
        } catch { $removeOwnedLoader = $false }
    }
    foreach ($entry in $receipt.files) {
        if ($entry.name -eq 'dinput8.dll') { continue }
        $dest = Target $entry.name
        if ($entry.owned -and (Test-Path -LiteralPath $dest)) { Remove-Item -LiteralPath $dest }
    }
    if ($removeOwnedLoader) {
        try {
            # Recheck just before removal; uncertainty must preserve the loader.
            $loaderPath = Target 'dinput8.dll'
            if ((Get-Hash $loaderPath) -eq $loaderEntry.sha256 -and (Test-LoaderUnused)) {
                Remove-Item -LiteralPath $loaderPath -ErrorAction Stop
            }
        } catch { Write-Verbose 'Loader preserved: it changed or could not be removed.' }
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
