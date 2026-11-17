function Initialize-Language([string]$Code) {
    if ($Code -notin @('fr','en')) { throw 'Unsupported language code' }
    $catalog = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../Locales/messages.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $script:translations = $catalog.$Code
    $script:activeLanguage = $Code
}
function T([string]$Key, [object[]]$Values = @()) {
    $property = $script:translations.PSObject.Properties[$Key]
    if (!$property) { throw "Missing translation key: $Key" }
    return [string]::Format([string]$property.Value, [object[]]$Values)
}
function Fail([string]$Key, [object[]]$Values = @()) {
    $exception = [InvalidOperationException]::new((T $Key $Values))
    $exception.Data['PlayerMessage'] = $true
    throw $exception
}
function Show-LocalizedError($Record) {
    $exception = $Record.Exception
    $known = $false
    $key = 'unexpectedError'
    while ($exception) {
        if ($exception.Data['PlayerMessage']) {
            $message = $exception.Message; $known = $true; break
        }
        if ($exception -is [UnauthorizedAccessException]) { $key = 'accessDenied' }
        elseif ($exception -is [IO.FileNotFoundException] -or $exception -is [IO.DirectoryNotFoundException]) { $key = 'fileMissing' }
        elseif ($exception -is [IO.IOException] -and $key -eq 'unexpectedError') { $key = 'ioError' }
        $exception = $exception.InnerException
    }
    if (!$known) { $message = T $key }
    Write-Host (T 'errorPrefix' @($message)) -ForegroundColor Yellow
    if (!$known) {
        # Keep OS-language exceptions out of the localized interface.
        $diagnostic = Join-Path (Split-Path -Parent $PSScriptRoot) 'setup-diagnostic.log'
        try {
            ($Record | Out-String) | Set-Content -LiteralPath $diagnostic -Encoding UTF8
            Write-Host (T 'diagnosticSaved' @($diagnostic))
        } catch { Write-Host (T 'diagnosticUnavailable') }
    }
}
function Show-PluginStatus([string]$LogPath) {
    if (!(Test-Path -LiteralPath $LogPath)) { Write-Output (T 'noLog'); return }
    $lines = @(Get-Content -LiteralPath $LogPath)
    $fields = @{}
    foreach ($line in $lines) {
        if ($line -match '^([a-z]+)=(.*)$') { $fields[$Matches[1]] = $Matches[2] }
    }
    foreach ($key in @('pid','armed','applied','failed','skipped')) {
        if (!$fields.ContainsKey($key) -or $fields[$key] -notmatch '^\d+$') {
            Write-Output (T 'unknownLog'); return
        }
    }
    $state = 'inactiveState'
    if ($fields['failed'] -ne '0') { $state = 'disarmedState' }
    elseif ($lines -match '^DISABLED:') { $state = 'disabledState' }
    elseif ($fields['armed'] -eq '1') { $state = 'activeState' }
    Write-Output (T 'sessionLog' @($fields['pid'],(T $state)))
    $process = Get-Process -Id ([int]$fields['pid']) -ErrorAction SilentlyContinue
    $current = $process -and $process.ProcessName -ieq 'SnowRunner'
    if ($current) {
        $current = $process.StartTime.ToUniversalTime() -le (Get-Item -LiteralPath $LogPath).LastWriteTimeUtc
    }
    if ($current) { Write-Output (T 'liveLog') } else { Write-Output (T 'historicalLog') }
    if ($lines -match 'INACTIVE: unknown game') { Write-Output (T 'inactiveGame') }
    # Keep interpreting historical 0.1.0 logs after a package upgrade.
    elseif ($lines -match 'INACTIVE: unverified Logitech') { Write-Output (T 'inactiveSdk') }
    elseif ($lines -match 'INACTIVE: loaded code mismatch') { Write-Output (T 'inactiveCode') }
    elseif ($lines -match '^INACTIVE:') { Write-Output (T 'inactiveHook') }
    Write-Output ''
    Write-Output (T 'counts' @($fields['applied'],$fields['failed'],$fields['skipped']))
    Write-Output ''
    Write-Output (T 'physicalNote')
}
