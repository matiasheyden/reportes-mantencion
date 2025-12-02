Write-Host "=== INICIANDO ACTUALIZACIÓN DE DATOS ===" -ForegroundColor Cyan

# 1. Convertir Excel a CSV
Write-Host "1. Generando CSV desde Excel..." -ForegroundColor Yellow
python export_data.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al exportar datos. Proceso detenido." -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit
}

# 2. Git commands
Write-Host "2. Sincronizando con la nube (GitHub)..." -ForegroundColor Yellow

# Verificar si es un repo git
if (-not (Test-Path ".git")) {
    Write-Host "Error: Esta carpeta no está configurada como repositorio Git." -ForegroundColor Red
    Write-Host "Por favor configura el repositorio primero."
    Read-Host "Presiona Enter para salir"
    exit
}

git add tbl_bitacora.csv
git commit -m "Actualización de datos: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
git push

if ($LASTEXITCODE -eq 0) {
    Write-Host "=== ¡ACTUALIZACIÓN COMPLETADA CON ÉXITO! ===" -ForegroundColor Green
    Write-Host "Tu aplicación se actualizará en unos momentos."
} else {
    Write-Host "Hubo un error al subir los cambios a GitHub." -ForegroundColor Red
}

Read-Host "Presiona Enter para cerrar"
