param(
    [int]$PreprocessPid = 24780
)

$ErrorActionPreference = "Stop"
$RepoDir = "C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT"
$Python = "C:\Users\rony.schwartz\.conda\envs\venv-napari\python.exe"
$LogsDir = Join-Path $RepoDir "05_evaluation\psd\full_volume_batch\logs"
$PreprocessLog = Join-Path $LogsDir "preprocess_samp_2_0.log"
$PreprocessErrLog = Join-Path $LogsDir "preprocess_samp_2_0.err.log"
$NlmTif = Join-Path $RepoDir "02_preprocessing\filters\nlm_output\nlm_volume.tif"
$PipelineLog = Join-Path $LogsDir "inference_samp_2_0.log"
$ConcatOut = "\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_samp_2_0\inference_concatenated\bnei_reem_samp_2_0.nii.gz"
$ManifestPath = Join-Path $RepoDir "05_evaluation\psd\full_volume_batch\manifest.json"

function Write-Stamp($msg) {
    $ts = (Get-Date).ToString("o")
    Write-Output "[$ts] $msg"
}

Write-Stamp "Waiting for preprocessing PID $PreprocessPid to finish..."
Wait-Process -Id $PreprocessPid -ErrorAction SilentlyContinue

Write-Stamp "Preprocessing process exited. Verifying success..."
$errContent = ""
if (Test-Path $PreprocessErrLog) { $errContent = Get-Content $PreprocessErrLog -Raw }
$outContent = Get-Content $PreprocessLog -Raw

if ($outContent -notmatch "Done\.") {
    Write-Stamp "FAILED: preprocessing log does not contain 'Done.' -- aborting auto-continue."
    Write-Stamp "--- stdout tail ---"
    Write-Output ($outContent.Substring([Math]::Max(0, $outContent.Length - 2000)))
    Write-Stamp "--- stderr tail ---"
    Write-Output ($errContent.Substring([Math]::Max(0, $errContent.Length - 2000)))
    exit 1
}
if (-not (Test-Path $NlmTif)) {
    Write-Stamp "FAILED: expected output not found: $NlmTif"
    exit 1
}
Write-Stamp "Preprocessing verified OK: $NlmTif"

Write-Stamp "Starting inference pipeline (tif_direct -> split -> predict -> concat)..."
& $Python -u (Join-Path $RepoDir "04_inference\scripts\run_bnei_reem_samp_2_0_pipeline.py") --gpu 0 2>&1 |
    Tee-Object -FilePath $PipelineLog
$pipelineExit = $LASTEXITCODE

if ($pipelineExit -ne 0) {
    Write-Stamp "FAILED: inference pipeline exited with code $pipelineExit. See $PipelineLog"
    exit 1
}
if (-not (Test-Path $ConcatOut)) {
    Write-Stamp "FAILED: expected concatenated output not found: $ConcatOut"
    exit 1
}
Write-Stamp "Inference pipeline complete: $ConcatOut"

Write-Stamp "Enabling bnei_reem_samp_2_0 entry in manifest.json..."
$manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
foreach ($v in $manifest.volumes) {
    if ($v.name -eq "bnei_reem_samp_2_0_fresh_bnei_reem_i4") {
        $v.enabled = $true
    }
}
$manifest | ConvertTo-Json -Depth 10 | Set-Content -Path $ManifestPath -Encoding utf8

Write-Stamp "Launching PSD batch for bnei_reem_samp_2_0_fresh_bnei_reem_i4..."
& $Python -u (Join-Path $RepoDir "05_evaluation\psd\run_psd_batch.py") --only bnei_reem_samp_2_0_fresh_bnei_reem_i4 2>&1 |
    Tee-Object -FilePath (Join-Path $LogsDir "psd_batch_driver_samp_2_0.log")
$psdExit = $LASTEXITCODE

Write-Stamp "PSD batch finished with exit code $psdExit."
if ($psdExit -ne 0) { exit 1 }
Write-Stamp "ALL DONE."
