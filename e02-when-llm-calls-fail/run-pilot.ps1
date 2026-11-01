$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    python build_items.py --check
    if ($LASTEXITCODE -ne 0) { throw 'Input checks failed' }
    python freeze.py --check
    if ($LASTEXITCODE -ne 0) { throw 'Review snapshot mismatch' }
    python -m unittest test_e02 -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    python run.py --dry-run
    if ($LASTEXITCODE -ne 0) { throw 'Pilot failed' }
    python analyse.py
    if ($LASTEXITCODE -ne 0) { throw 'Pilot analysis failed' }
    python pilot_fixtures.py
    if ($LASTEXITCODE -ne 0) { throw 'Scripted diagnostic fixtures failed' }
    python freeze.py --check
    if ($LASTEXITCODE -ne 0) { throw 'Review sources changed during pilot' }
} finally {
    Pop-Location
}
