param(
    [ValidateSet('preflight', 'evaluation')]
    [string]$Stage = 'preflight'
)

# Tej runs this script. Both stages make paid calls after a local freeze check.
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    & python freeze.py --check
    if ($LASTEXITCODE -ne 0) { throw 'Freeze validation failed. No model calls started.' }
    $studyModels = @('oss-20b', 'luna', 'glm-flash', 'oss-120b', 'sol', 'glm-flash-t0')
    foreach ($studyModel in $studyModels) {
        $runnerArgs = @('run.py', '--model', $studyModel, '--items', 'items.jsonl',
                        '--workers', '4', '--run-tag', 'frozen_20261029')
        if ($Stage -eq 'preflight') { $runnerArgs += @('--preflight', '--repeats', '1') }
        & python @runnerArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Stopped at $studyModel ($Stage). Preserve all saved rows and inspect the error."
        }
    }
    if ($Stage -eq 'preflight') {
        Write-Output '18 frozen-configuration probes complete. Inspect them before -Stage evaluation.'
    } else {
        Write-Output 'Evaluation complete. Check saved run health before accuracy:'
        Write-Output 'python pilot_health.py --items items.jsonl --run-tag frozen_20261029 --evaluation'
        Write-Output 'Keep the 81 held-out items separate from the 21 development items in final reporting.'
    }
} finally {
    Pop-Location
}
