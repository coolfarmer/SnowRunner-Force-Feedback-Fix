#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$env:DOTNET_CLI_HOME = Join-Path $repo 'build/dotnet-home'
$env:NUGET_PACKAGES = Join-Path $repo 'build/nuget'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
& dotnet restore (Join-Path $PSScriptRoot 'Installer.csproj') --locked-mode
if ($LASTEXITCODE -ne 0) { throw 'Installer restore failed' }
& dotnet publish (Join-Path $PSScriptRoot 'Installer.csproj') -c Release --no-restore -o (Join-Path $repo 'build/installer')
if ($LASTEXITCODE -ne 0) { throw 'Installer publish failed' }
