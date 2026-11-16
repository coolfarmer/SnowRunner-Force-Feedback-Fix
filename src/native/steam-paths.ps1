# Discovery only: no registry or filesystem writes. Compatible with Windows PowerShell 5.1.
function Find-SnowRunnerDirectories {
    param([string[]]$SteamRoots)
    # Windows paths are case-insensitive. Normalize separators before deduplication.
    $roots = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($root in $SteamRoots) {
        if ([string]::IsNullOrWhiteSpace($root)) { continue }
        try { $normalized = [IO.Path]::GetFullPath($root).TrimEnd('\','/') }
        catch { continue }
        [void]$roots.Add($normalized)
    }
    foreach ($root in @($roots)) {
        $vdf = Join-Path $root 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf -PathType Leaf) {
            foreach ($match in [regex]::Matches((Get-Content -LiteralPath $vdf -Raw), '"path"\s+"([^"]+)"')) {
                $library = $match.Groups[1].Value.Replace('\\','\')
                try { $normalized = [IO.Path]::GetFullPath($library).TrimEnd('\','/') }
                catch { continue }
                [void]$roots.Add($normalized)
            }
        }
    }
    $found = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($root in $roots) {
        $p = Join-Path $root 'steamapps\common\SnowRunner\Sources\Bin'
        if (Test-Path -LiteralPath (Join-Path $p 'SnowRunner.exe') -PathType Leaf) {
            [void]$found.Add([IO.Path]::GetFullPath($p))
        }
    }
    foreach ($path in $found) { Write-Output $path }
}
