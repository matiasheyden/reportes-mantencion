$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'streamlit' -or $_.CommandLine -match 'app.py') }
if ($procs) {
    foreach ($p in $procs) {
        Write-Output "Stopping PID $($p.ProcessId): $($p.CommandLine)"
        try {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
            Write-Output "Stopped $($p.ProcessId)"
        } catch {
            Write-Output "Could not stop PID $($p.ProcessId): $_"
        }
    }
} else {
    Write-Output "No streamlit/app.py processes found."
}
