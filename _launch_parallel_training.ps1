# Launch both training jobs in parallel on separate GPUs.
# train_iter4_continue_bnei_reem -> GPU 0  -> multi_sample_iter04_continue
# train_fresh_bnei_reem           -> GPU 1  -> multi_sample_fresh_bnei_reem

$Python  = "C:\Users\rony.schwartz\.conda\envs\venv-napari\python.exe"
$RepoDir = "C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT"

$ContinueScript = Join-Path $RepoDir "train_iter4_continue_bnei_reem.py"
$FreshScript    = Join-Path $RepoDir "train_fresh_bnei_reem.py"

$ContinueLog    = Join-Path $RepoDir "_train_iter4_continue_bnei_reem.log"
$ContinueErrLog = Join-Path $RepoDir "_train_iter4_continue_bnei_reem_err.log"
$FreshLog       = Join-Path $RepoDir "_train_fresh_bnei_reem.log"
$FreshErrLog    = Join-Path $RepoDir "_train_fresh_bnei_reem_err.log"

Write-Host ""
Write-Host "=== Launching parallel training jobs ==="
Write-Host ""

Write-Host "Starting: train_iter4_continue_bnei_reem  (GPU 0, fine-tune from iter04)"
$Job1 = Start-Process `
    -FilePath $Python `
    -ArgumentList $ContinueScript `
    -RedirectStandardOutput $ContinueLog `
    -RedirectStandardError  $ContinueErrLog `
    -PassThru `
    -WindowStyle Hidden

Write-Host "Starting: train_fresh_bnei_reem            (GPU 1, from scratch)"
$Job2 = Start-Process `
    -FilePath $Python `
    -ArgumentList $FreshScript `
    -RedirectStandardOutput $FreshLog `
    -RedirectStandardError  $FreshErrLog `
    -PassThru `
    -WindowStyle Hidden

Write-Host ""
Write-Host "Both jobs launched:"
Write-Host "  train_iter4_continue_bnei_reem  PID=$($Job1.Id)"
Write-Host "    stdout: $ContinueLog"
Write-Host "    stderr: $ContinueErrLog"
Write-Host ""
Write-Host "  train_fresh_bnei_reem            PID=$($Job2.Id)"
Write-Host "    stdout: $FreshLog"
Write-Host "    stderr: $FreshErrLog"
Write-Host ""
Write-Host "Monitor (run in separate terminals):"
Write-Host "  Get-Content '$ContinueLog' -Wait"
Write-Host "  Get-Content '$FreshLog' -Wait"
Write-Host ""
Write-Host "Check GPU utilization:"
Write-Host "  nvidia-smi dmon -s u"
Write-Host ""
