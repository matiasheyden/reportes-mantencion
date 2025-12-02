$url = 'http://localhost:8501'
for ($i = 0; $i -lt 30; $i++) {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 5 -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
            Write-Output 'OK'
            exit 0
        }
    } catch {
        Write-Output "WAIT $i"
    }
    Start-Sleep -Seconds 2
}
Write-Output 'TIMEOUT'
exit 1
