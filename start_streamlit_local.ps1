<#
start_streamlit_local.ps1

Descripción:
- Crea/activa un entorno virtual en `.venv` si no existe.
- Instala dependencias desde `requirements.txt` si existe.
- Mata procesos que estén escuchando en el puerto 8501 (limpia arranques previos).
- Inicia Streamlit en modo headless (para que Streamlit no abra el navegador dos veces).
- Espera a que el servidor responda y abre UNA sola pestaña en el navegador por defecto.

Uso:
- Desde PowerShell: `.
start_streamlit_local.ps1` (ejecutar desde la carpeta del proyecto)
- O doble-clic en `start_streamlit_local.bat` que llama este script.

#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "[start_streamlit_local] Iniciando procedimiento en: $PSScriptRoot"

Push-Location $PSScriptRoot

try {
    # Seleccionar python en venv si existe, sino fallback al del sistema
    $venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        $Python = $venvPython
        Write-Host "Usando Python de venv: $Python"
    } else {
        Write-Host "No se encontró .venv. Buscando Python en PATH..."
        $py = Get-Command python -ErrorAction SilentlyContinue
        if ($py) {
            $Python = $py.Path
            Write-Host "Usando Python del sistema: $Python"
        } else {
            throw "No se encontró Python en el sistema. Instala Python 3 y vuelve a intentar."
        }
    }

    # Si no existe .venv, crearlo
    if (-not (Test-Path (Join-Path $PSScriptRoot ".venv"))) {
        Write-Host "Creando entorno virtual .venv..."
        & $Python -m venv .venv
        # actualizar la ruta al python dentro del venv
        $Python = (Resolve-Path ".venv\Scripts\python.exe").Path
        Write-Host "Entorno virtual creado: $Python"
    }

    # Instalar requirements si existe
    $req = Join-Path $PSScriptRoot "requirements.txt"
    if (Test-Path $req) {
        Write-Host "Instalando dependencias desde requirements.txt..."
        & $Python -m pip install --upgrade pip setuptools wheel | Out-Null
        & $Python -m pip install -r $req
    } else {
        Write-Host "No se encontró requirements.txt — omitiendo instalación." 
    }

    # Matar procesos que usan el puerto 8501
    Write-Host "Buscando procesos que usen el puerto 8501..."
    try {
        $conns = Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue
        if ($conns) {
            $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($pid in $pids) {
                Write-Host "Deteniendo PID $pid en puerto 8501..."
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
        } else {
            Write-Host "No hay procesos en el puerto 8501"
        }
    } catch {
        Write-Warning "Fallo al comprobar procesos en puerto 8501: $_"
    }

    # Iniciar Streamlit en modo headless para que NO abra el navegador automáticamente
    Write-Host "Iniciando Streamlit (headless) en segundo plano..."
    $args = @('-m','streamlit','run','app.py','--server.headless','true','--server.port','8501','--server.address','localhost')
    # Usar python del venv para garantizar dependencias correctas
    $pythonExec = (Resolve-Path ".venv\Scripts\python.exe").Path
    $si = Start-Process -FilePath $pythonExec -ArgumentList $args -WindowStyle Minimized -PassThru
    Write-Host "Streamlit arrancado (PID $($si.Id)). Esperando a que el servidor responda..."

    # Esperar a que el servidor responda (timeout 60s)
    $timeout = 60
    $elapsed = 0
    $listening = $false
    while ($elapsed -lt $timeout) {
        Start-Sleep -Seconds 1
        $elapsed += 1
        try {
            $t = Test-NetConnection -ComputerName localhost -Port 8501 -WarningAction SilentlyContinue
            if ($t.TcpTestSucceeded) { $listening = $true; break }
        } catch {
            # ignorar
        }
    }

    if (-not $listening) {
        Write-Warning "El servidor no respondió en http://localhost:8501 después de $timeout segundos. Revisa logs o ejecuta manualmente."
        Write-Host "Puedes ver la salida de streamlit con: tail -f .\nstreamlit_run.log (si lo configuraste) o ejecuta manualmente: \".\.venv\Scripts\python.exe -m streamlit run app.py\""
    } else {
        Write-Host "Servidor activo en http://localhost:8501 — abriendo navegador UNA sola vez..."
        Start-Process "http://localhost:8501"
    }

    Write-Host "Hecho. Si necesitas que el servidor se ejecute como servicio (arranque automático), puedo generar un servicio de Windows o instrucciones para systemd en Linux." 

} catch {
    Write-Error "Error durante el proceso: $_"
} finally {
    Pop-Location
}

exit 0
