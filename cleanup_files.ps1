Write-Host "Running cleanup (PowerShell) in: $PSScriptRoot"
Push-Location $PSScriptRoot
$files = @(
    "app.py.bak",
    "reporte.py.bak",
    "streamlit_run.log",
    "streamlit_run.log.bak",
    "reportlab-userguide.pdf",
    "test_pdf.py",
    "bitacora_15-10.pdf",
    "bitacora_15-10_styled.pdf",
    "bitacora_22-10.pdf",
    "bitacora_22-10_styled.pdf"
)
foreach ($f in $files) {
    if (Test-Path $f) {
        try { Remove-Item $f -Force -ErrorAction Stop; Write-Host "Removed: $f" } catch { Write-Warning "Failed to remove $f: $_" }
    } else { Write-Host "Not found: $f" }
}
Write-Host "Cleanup complete."
Pop-Location
Pause
