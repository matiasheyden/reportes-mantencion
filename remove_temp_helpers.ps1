$folder = 'C:\Users\heyde\OneDrive\Escritorio\python_work\base de datos'
Set-Location -Path $folder
$files = @('do_cleanup_remove.ps1','do_stop_streamlit.ps1')
foreach ($f in $files) {
    if (Test-Path $f) {
        try { Remove-Item -LiteralPath $f -Force -ErrorAction Stop; Write-Output ("Removed: " + $f) } catch { Write-Warning ("Failed to remove " + $f + ": " + $_) }
    } else { Write-Output "Not found: $f" }
}
