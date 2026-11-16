# Run with Windows PowerShell 5.1, as used by the distributed CMD launchers.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'src\native\steam-paths.ps1')
$base = Join-Path $root ('build\native\discovery-' + [Guid]::NewGuid().ToString('N'))
function Fixture-Game([string]$Library) {
    $bin = Join-Path $Library 'steamapps\common\SnowRunner\Sources\Bin'
    [void][IO.Directory]::CreateDirectory($bin)
    [IO.File]::WriteAllText((Join-Path $bin 'SnowRunner.exe'),'fixture; never executed')
    return $bin
}
function Check([bool]$Condition,[string]$Message) {
    if (!$Condition) { throw $Message }
    Write-Output "PASS $Message"
}
$steam = Join-Path $base 'Steam With Spaces'
$first = Fixture-Game $steam
$vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
[IO.File]::WriteAllText($vdf, ('"libraryfolders" { "0" { "path" "' + $steam.Replace('\','\\') + '" } }'))
$found = @(Find-SnowRunnerDirectories -SteamRoots @($steam.ToLowerInvariant().Replace('\','/'),$steam.ToUpperInvariant(),$steam+'\'))
Check ($found.Count -eq 1 -and $found[0] -ieq $first) 'same library with mixed case, separators and trailing slash counted once'
Check (@(Find-SnowRunnerDirectories -SteamRoots @()).Count -eq 0) 'no roots gives no result'
Check (@(Find-SnowRunnerDirectories -SteamRoots @((Join-Path $base 'missing'))).Count -eq 0) 'missing library gives no result'
$external = Join-Path $base 'Other Library'
$second = Fixture-Game $external
[IO.File]::WriteAllText($vdf, ('"libraryfolders" { "0" { "path" "' + $steam.Replace('\','\\') + '" } "1" { "path" "' + $external.Replace('\','\\') + '" } }'))
$found = @(Find-SnowRunnerDirectories -SteamRoots @($steam))
Check ($found.Count -eq 2 -and $found -contains $first -and $found -contains $second) 'genuinely different installations remain distinct'
$emptySteam = Join-Path $base 'Steam Without Game'
[void][IO.Directory]::CreateDirectory((Join-Path $emptySteam 'steamapps'))
[IO.File]::WriteAllText((Join-Path $emptySteam 'steamapps\libraryfolders.vdf'),('"libraryfolders" { "1" { "path" "' + $external.Replace('\','\\') + '" } }'))
$found = @(Find-SnowRunnerDirectories -SteamRoots @($emptySteam))
Check ($found.Count -eq 1 -and $found[0] -ieq $second) 'game on another Steam library discovered'
Write-Output "Evidence: $base"
