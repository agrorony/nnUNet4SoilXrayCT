# Launch N training jobs in parallel across GPUs.
#
# Generalized replacement for the old repo-root `_launch_parallel_training.ps1`,
# which hardcoded exactly two jobs (train_iter4_continue_bnei_reem -> GPU 0,
# train_fresh_bnei_reem -> GPU 1). This version accepts an arbitrary array of
# {ScriptArgs, Label} pairs, either inline (edit $Jobs below) or from a JSON
# file passed via -JobsFile, and launches each as `run_training.py <ScriptArgs>`
# with its own log/err redirect into logs_archive/training/<Label>/.
#
# Usage:
#   .\launch_parallel_runs.ps1
#   .\launch_parallel_runs.ps1 -JobsFile jobs.json
#
# jobs.json format:
# [
#   { "Label": "iter04_continue", "ScriptArgs": "--config ..\\run_configs\\iter04_continue.yaml --gpu 0" },
#   { "Label": "fresh_bnei_reem",  "ScriptArgs": "--config ..\\run_configs\\train_fresh_bnei_reem.yaml --gpu 1" }
# ]

param(
    [string]$JobsFile = ""
)

$Python   = "C:\Users\rony.schwartz\.conda\envs\venv-napari\python.exe"
$RepoDir  = "C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT"
$RunTrain = Join-Path $RepoDir "03_training\scripts\run_training.py"
$LogRoot  = Join-Path $RepoDir "logs_archive\training"

if ($JobsFile -ne "") {
    $Jobs = Get-Content $JobsFile -Raw | ConvertFrom-Json
} else {
    # Default jobs, equivalent to the two the old script hardcoded:
    #   train_iter4_continue_bnei_reem -> GPU 0 -> multi_sample_iter04_continue
    #   train_fresh_bnei_reem           -> GPU 1 -> multi_sample_fresh_bnei_reem
    $Jobs = @(
        @{ Label = "iter04_continue";  ScriptArgs = "--config `"$RepoDir\03_training\run_configs\iter04_continue.yaml`" --gpu 0" },
        @{ Label = "train_fresh_bnei_reem"; ScriptArgs = "--config `"$RepoDir\03_training\run_configs\train_fresh_bnei_reem.yaml`" --gpu 1" }
    )
}

Write-Host ""
Write-Host "=== Launching $($Jobs.Count) parallel training job(s) ==="
Write-Host ""

$Procs = @()
foreach ($Job in $Jobs) {
    $JobLogDir = Join-Path $LogRoot $Job.Label
    New-Item -ItemType Directory -Force -Path $JobLogDir | Out-Null
    $Log    = Join-Path $JobLogDir "$($Job.Label).log"
    $ErrLog = Join-Path $JobLogDir "$($Job.Label)_err.log"

    Write-Host "Starting: $($Job.Label)"
    $ArgList = @($RunTrain) + ($Job.ScriptArgs -split ' ')
    $Proc = Start-Process `
        -FilePath $Python `
        -ArgumentList $ArgList `
        -RedirectStandardOutput $Log `
        -RedirectStandardError  $ErrLog `
        -PassThru `
        -WindowStyle Hidden

    Write-Host "  PID=$($Proc.Id)"
    Write-Host "  stdout: $Log"
    Write-Host "  stderr: $ErrLog"
    Write-Host ""
    $Procs += $Proc
}

Write-Host "All jobs launched. Monitor with:"
foreach ($Job in $Jobs) {
    $JobLogDir = Join-Path $LogRoot $Job.Label
    Write-Host "  Get-Content '$(Join-Path $JobLogDir "$($Job.Label).log")' -Wait"
}
Write-Host ""
Write-Host "Check GPU utilization:"
Write-Host "  nvidia-smi dmon -s u"
Write-Host ""
