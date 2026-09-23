param(
    [string]$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
)

$ErrorActionPreference = 'Stop'
$aiRoot = Join-Path $ProjectRoot 'AI'
$appRoot = Join-Path $aiRoot 'app'
$resourceDir = Join-Path $ProjectRoot 'Java/OpportunityImpl/src/main/resources'
$archivePath = Join-Path $resourceDir 'mosaic-python.zip'

if (-not (Test-Path -LiteralPath (Join-Path $appRoot 'main.py') -PathType Leaf)) {
    throw "Python application not found at $appRoot"
}

New-Item -ItemType Directory -Path $resourceDir -Force | Out-Null
$temporaryPath = Join-Path $resourceDir ("mosaic-python-{0}.tmp" -f [guid]::NewGuid())

try {
    Add-Type -AssemblyName System.IO.Compression
    $stream = [System.IO.File]::Open($temporaryPath, [System.IO.FileMode]::CreateNew)
    try {
        $archive = [System.IO.Compression.ZipArchive]::new($stream, [System.IO.Compression.ZipArchiveMode]::Create)
        try {
            Get-ChildItem -LiteralPath $appRoot -Recurse -File -Filter '*.py' |
                Sort-Object FullName |
                ForEach-Object {
                    $entryName = $_.FullName.Substring($aiRoot.Length + 1).Replace('\', '/')
                    $entry = $archive.CreateEntry($entryName, [System.IO.Compression.CompressionLevel]::Optimal)
                    $source = [System.IO.File]::OpenRead($_.FullName)
                    try {
                        $destination = $entry.Open()
                        try { $source.CopyTo($destination) }
                        finally { $destination.Dispose() }
                    }
                    finally { $source.Dispose() }
                }
        }
        finally { $archive.Dispose() }
    }
    finally { $stream.Dispose() }

    [System.IO.File]::Copy($temporaryPath, $archivePath, $true)
}
finally {
    if (Test-Path -LiteralPath $temporaryPath) { Remove-Item -LiteralPath $temporaryPath }
}
