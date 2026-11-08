# Tej runs this from PowerShell after checking the printed estimate.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Invoke-ExperimentPython {
    param([string[]]$PythonArguments)
    & python @PythonArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Experiment command failed. Resolve the reported error before continuing."
    }
}

Invoke-ExperimentPython -PythonArguments @('freeze.py', '--check')
Invoke-ExperimentPython -PythonArguments @('run.py', '--estimate')
Invoke-ExperimentPython -PythonArguments @('run.py', '--full', '--model', 'api')
Invoke-ExperimentPython -PythonArguments @('freeze.py', '--check')
Invoke-ExperimentPython -PythonArguments @('analyse.py')
Invoke-ExperimentPython -PythonArguments @('analyse_uncertainty.py')
Invoke-ExperimentPython -PythonArguments @('freeze.py', '--check')
Write-Host 'Send results/local, results/api and analysis back for the post handover. Keep .env private.'
