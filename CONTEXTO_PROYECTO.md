# CONTEXTO DEL PROYECTO: Reportes de Mantención
> **Archivo Maestro de Transición**
> *Entregar este archivo al nuevo Agente de IA para continuar el trabajo sin perder contexto.*

## 1. Resumen del Proyecto
Sistema de gestión de mantenimiento y dashboard de KPIs desarrollado en **Python + Streamlit**.
El objetivo es reemplazar el uso manual de Excel por una aplicación web interactiva que centralice bitácoras, control presupuestario y análisis de confiabilidad.

## 2. Arquitectura Actual
*   **Lenguaje:** Python 3.x
*   **Framework:** Streamlit
*   **Datos:**
    *   **Fuente Principal (Producción):** Google Sheets (`BBDD_mantencion`). La app lee de aquí usando `st.secrets`.
    *   **Respaldo/Desarrollo:** `BBDD_MANTENCION.xlsm` (Excel local).
    *   **Capa de Datos:** `app.py` intenta leer de Google Sheets primero. Si falla, busca CSV o Excel local.
    *   **Hoja Maestra:** Se implementó lógica para leer una hoja `maestra_activos` que clasifica los items en `Equipo`, `Sistema` y `Edificio`.

## 3. Funcionalidades Implementadas (Estado: Funcional)
1.  **KPI Dashboard:**
    *   Cálculo de Disponibilidad, MTTR, MTBF.
    *   **Filtros:** Fecha, Equipo y (Recientemente agregado) **Tipo, Sistema y Edificio**.
    *   Lógica Híbrida: Antes de Nov-2025 usa turno estándar, después usa `tbl_programacion`.
2.  **Análisis de Confiabilidad:**
    *   Pestañas: Resumen General, Pareto, Weibull.
    *   Cálculo automático de Beta/Eta (Weibull) para diagnóstico de fallas.
    *   Filtro Global de Fechas.
3.  **Control Presupuestario:**
    *   Comparativa de Gastos (OM, Servicios) vs Presupuesto.
4.  **Bitácora:**
    *   Visualización de datos crudos.

## 4. Problemas Recientes y Soluciones Aplicadas
*   **Conflicto de Tildes:** El dashboard no filtraba "Ubicación" porque el código buscaba "Ubicacion". **Solución:** Se implementó normalización de strings (función `normalize_str`) para ignorar tildes y mayúsculas.
*   **Instalación Docker/WSL:** VS Code intentó instalar un Dev Container automáticamente. **Solución:** Se instruyó al usuario borrar la carpeta `.devcontainer` para aligerar el entorno.
*   **Saturación del Chat:** El contexto se volvió muy pesado. **Solución:** Creación de este archivo para migración.

## 5. Roadmap / Pendientes Inmediatos
1.  **Migración de Datos:** El usuario quiere dejar de depender de Excel y mover todo a un sistema de gestión "gratuito" y personal.
    *   *Propuesta:* Migrar a **SQLite** local + Streamlit.
2.  **Optimización:** Limpiar código muerto en `app.py` relacionado con cargas de Excel antiguas si se confirma la migración.
3.  **Interfaz:** Mejorar la UX de los filtros nuevos (asegurar que se oculten si no hay datos).

## 6. Instrucciones para el Nuevo Agente
1.  Lee `app.py` para entender la lógica de `load_sheets` y los filtros de `maestra_activos`.
2.  Asume que el entorno es Windows local (sin Docker).
3.  El usuario es **no-técnico experto** (entiende la lógica de negocio perfectamente, pero necesita guía paso a paso en código).
4.  **Prioridad:** Estabilidad del sistema actual y planificación de la migración a SQLite.
