# Reportes de Mantención — Proyecto

Resumen rápido:
- `app.py`: Streamlit app que muestra KPI, Bitácora y Disponibilidad alimentada por `BBDD_MANTENCION.xlsm`.
- `BBDD_MANTENCION.xlsm`: archivo de datos (confidencial).
- `reporte.py`: script para exportar todas las hojas a `csv_exports/`.
- `start_streamlit_local.ps1` / `.bat`: scripts para preparar venv, instalar deps y arrancar la app localmente (abren UNA pestaña en el navegador).
- `README_DEPLOY.md`: opciones para alojar los reportes 24/7 (Oracle Cloud, Streamlit Cloud, GitHub Actions, etc.).
- `README_FOR_MANAGEMENT.md` y atajos (`management_shortcut.url`, `open_report.bat`) para distribuir a gerencia.

Cómo ejecutar localmente (Windows):

1. Abrir `PowerShell` en la carpeta del proyecto.
2. Ejecutar:

```powershell
.
\start_streamlit_local.ps1
```

o simplemente hacer doble clic en `start_streamlit_local.bat`.

Notas de seguridad:
- No subas `BBDD_MANTENCION.xlsm` a un repositorio público.
- Usa HTTPS y autenticación si vas a exponer la app a gerencia.

Si quieres, puedo:
- Ejecutar un `cleanup` (eliminar backups/logs/PDFs) — lo hago si confirmas.
- Preparar un `deploy` automatizado a Oracle Cloud Free Tier y los scripts de `nginx`/`systemd`.
