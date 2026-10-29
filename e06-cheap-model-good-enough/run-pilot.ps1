param(
    [ValidateSet('preflight', 'pilot')]
    [string]$Stage = 'preflight'
)

# Tej runs this script. Each stage makes paid calls. Never read or print credentials here.
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $studyModels = @('oss-20b', 'luna', 'glm-flash', 'oss-120b', 'sol', 'glm-flash-t0')
    foreach ($studyModel in $studyModels) {
        $runnerArgs = @(
            'run.py', '--model', $studyModel, '--items', 'items_samples.jsonl',
            '--repeats', '1', '--workers', '4', '--run-tag', 'sixmodel_20261029'
        )
        if ($Stage -eq 'preflight') { $runnerArgs += '--preflight' }
        & python @runnerArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Stopped at $studyModel ($Stage). Review the error before continuing."
        }
    }
    if ($Stage -eq 'preflight') {
        Write-Output 'Preflight complete: inspect all 18 compatibility answers before running -Stage pilot.'
    } else {
        Write-Output 'Pilot complete. Check health before accuracy:'
        Write-Output 'python pilot_health.py --run-tag sixmodel_20261029'
        Write-Output 'Then manually review 3 answers per model per task and recalculate the six-model budget.'
    }
} finally {
    Pop-Location
}
