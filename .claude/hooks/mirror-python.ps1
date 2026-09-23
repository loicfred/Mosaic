param(
    [string]$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
)

# Keeps the site's Python folder an exact mirror of AI/: code, datasets and models. Its own .venv is left alone.
# robocopy /MIR copies only changed files and removes files AI/ no longer has.
$ErrorActionPreference = 'Stop'
$source = Join-Path $ProjectRoot 'AI'
$target = Join-Path $ProjectRoot 'Java/OpportunityApp/config/py/mosaic'

foreach ($folder in 'app', 'datasets', 'models') {
    robocopy (Join-Path $source $folder) (Join-Path $target $folder) /MIR /XD __pycache__ /NFL /NDL /NJH /NJS /NP | Out-Null
    # robocopy exit codes below 8 mean success (0 = nothing to copy, 1 = files copied, 2+ = extras removed).
    if ($LASTEXITCODE -ge 8) { throw "Mirroring AI/$folder failed with robocopy code $LASTEXITCODE" }
}
exit 0
