# Documentación Técnica y Funcional: Dashboard de Gestión de Mantenimiento

## 1. Comportamiento Esperado y Protocolo de Actualización
**Instrucción para Agentes de IA Futuros:**
Este documento sirve como la "Fuente de la Verdad" para la lógica de negocio de la aplicación `app.py`. Al realizar modificaciones futuras en el código, el agente debe:
1.  Leer este documento primero para entender la lógica preexistente.
2.  Si se modifica una fórmula, una fuente de datos o una visualización, este documento **DEBE** ser actualizado para reflejar el cambio.
3.  El objetivo es mantener una sincronización perfecta entre el código (`app.py`) y esta documentación.

---

## 2. Descripción General
Esta aplicación es un Dashboard interactivo desarrollado en **Python** utilizando el framework **Streamlit**. Su propósito es centralizar, procesar y visualizar los datos operativos y financieros del departamento de mantenimiento. Permite la toma de decisiones basada en datos reales de disponibilidad de equipos y control presupuestario.

### Estructura de la Aplicación
La app se divide en tres secciones principales accesibles mediante un selector de radio (`st.radio`):
1.  **KPI Dashboard & Disponibilidad:** Análisis de fallas, tiempos de parada y disponibilidad operativa.
2.  **Control Presupuestario:** Seguimiento de gastos (OM, Servicios, Otros) vs. Presupuesto anual.
3.  **Bitácora:** Explorador de registros crudos de mantenimiento.

---

## 3. Fuentes de Datos y Variables
La aplicación carga datos desde **Google Sheets** (o Excel local como respaldo). Las hojas clave son:

### A. Hoja `tbl_bitacora` (Fuente de Fallas)
*   **Ubicación en código:** `sheets["tbl_bitacora"]`
*   **Variables Clave:**
    *   `Fecha` / `Date`: Fecha del evento.
    *   `Equipo` / `Ubic`: Identificador único del activo (ej. "REX", "TROZADORA 1").
    *   `Downtime` / `Minutos Detención`: Tiempo real que el equipo estuvo detenido por falla.
    *   `Inicio` / `Fin`: (Opcional) Hora de inicio y fin de la falla para cálculo automático.

### B. Hoja `tbl_programacion` (Fuente de Tiempo Operativo)
*   **Ubicación en código:** `sheets["tbl_programacion"]`
*   **Propósito:** Define las horas reales que un equipo *debería* haber trabajado. Fundamental para el cálculo correcto de disponibilidad.
*   **Variables Clave:**
    *   `Fecha`: Día de la programación.
    *   `Equipo`: Debe coincidir exactamente con los nombres en `tbl_bitacora`.
    *   `Horas Programadas`: Cantidad de horas planificadas para ese día (ej. 9.5, 12, 24).

### C. Hojas Financieras (`OM`, `Presupuesto`, `Otros_Gastos`)
*   **OM:** Órdenes de Mantenimiento (Repuestos y Servicios).
*   **Presupuesto:** Metas de gasto mensual por categoría.
*   **Otros_Gastos:** Gastos misceláneos (Caja chica, compras directas).

---

## 4. Lógica de Negocio y Ecuaciones

### 4.1. Cálculo de Disponibilidad (KPI Dashboard)
La disponibilidad es la métrica más crítica y compleja de la app. Utiliza un enfoque **Híbrido**.

**Ecuación General:**
$$ \text{Disponibilidad (\%)} = \frac{\text{Tiempo Programado} - \text{Tiempo de Downtime}}{\text{Tiempo Programado}} \times 100 $$

**Lógica del "Tiempo Programado" (Denominador):**
El sistema determina el tiempo programado siguiendo esta jerarquía lógica:

1.  **Fecha de Corte:** Se define una constante `PROGRAMMING_START_DATE` (01/11/2025).
2.  **Antes de la Fecha de Corte:** Se asume un **Turno Estándar** para llenar el vacío de datos históricos.
    *   *Lunes a Jueves:* 08:00 a 18:00 (10h) - 30m colación = **9.5 horas (570 min)**.
    *   *Viernes:* 08:00 a 14:30 (6.5h) - 30m colación = **6.0 horas (360 min)**.
    *   *Sábado/Domingo:* 0 horas.
3.  **Después de la Fecha de Corte:**
    *   El sistema busca en `tbl_programacion`.
    *   **Si existe registro:** Usa el valor exacto ingresado por el usuario.
    *   **Si NO existe registro (NaN):** Aplica el **Turno Estándar** como respaldo (Fallback).
    *   *Nota:* Si un día no se trabaja (ej. feriado) y no está en la tabla, el sistema podría asumir turno estándar si no se ingresa explícitamente como "0 horas".

**Lógica del "Downtime" (Numerador):**
*   Se suman los minutos de la columna `Downtime` de `tbl_bitacora` para el rango de fechas y equipo seleccionado.
*   Función: `compute_downtime_minutes()`. Intenta leer la columna directa; si falla, calcula `Fin - Inicio`.

### 4.2. Métricas de Confiabilidad (MTTR / MTBF)
*   **MTTR (Mean Time To Repair):** Tiempo promedio que toma reparar una falla.
    $$ \text{MTTR} = \frac{\text{Total Downtime (min)}}{\text{Cantidad de Eventos de Falla}} $$
*   **MTBF (Mean Time Between Failures):** Tiempo promedio operativo entre dos fallas consecutivas.
    $$ \text{MTBF} = \frac{\text{Tiempo Total Programado} - \text{Total Downtime}}{\text{Cantidad de Eventos de Falla}} $$

### 4.3. Control Presupuestario (Waterfall Chart)
Visualiza cómo el presupuesto anual se consume mes a mes.
*   **Presupuesto Anual:** Suma total de la columna `Monto` en la hoja `Presupuesto` para el año seleccionado.
*   **Gastos Reales:** Suma de `OM` (Repuestos + Servicios) + `Otros_Gastos`.
*   **Disponible:** `Presupuesto Anual - Gastos Acumulados`.
*   **Gráfico:** Se usa `plotly.graph_objects.Waterfall`.
    *   La primera barra es el Presupuesto (Positivo).
    *   Las barras siguientes son los gastos mensuales (Negativos/Rojos).
    *   La última barra es el "Disponible" (Total final).

---

## 5. Funciones Auxiliares Importantes

### `load_sheets(xls_path)`
*   **Propósito:** Gestiona la conexión a datos.
*   **Comportamiento:** Prioriza la conexión a Google Sheets vía API (`st.secrets`). Si falla, busca un archivo Excel local (`BBDD_MANTENCION.xlsm`). Si falla, busca un CSV en caché.

### `clean_currency(val)`
*   **Propósito:** Limpieza de datos financieros sucios.
*   **Problema:** Excel a veces envía montos como texto: "$ 1.500,00" o "1,500.00".
*   **Solución:** Elimina símbolos `$` y `.`, reemplaza `,` por `.` y convierte a `float`. Es vital para evitar errores de cálculo en el presupuesto.

### `find_column(df, keywords)`
*   **Propósito:** Flexibilidad en los nombres de columnas.
*   **Lógica:** Busca en el DataFrame una columna que contenga alguna de las palabras clave.
*   **Ejemplo:** Para encontrar la fecha, busca "fecha", "date", "time". Esto permite que el usuario cambie ligeramente los encabezados en Excel sin romper la app.

---

## 6. Visualización y Estética
*   **Librería:** `Plotly Express` y `Plotly Graph Objects`.
*   **Tema:** Oscuro (Dark Mode) forzado mediante CSS personalizado (`_GLOBAL_CSS`) para una apariencia profesional tipo "Centro de Control".
*   **Tooltips:** Los gráficos circulares de disponibilidad incluyen `customdata` para mostrar:
    *   % Disponibilidad.
    *   Minutos Totales Programados (Dato real o estimado).
    *   Minutos de Downtime (Dato real).
    *   Manejo de "Sin programación" para evitar mostrar `NaN`.

---

## 7. Guía de Uso para el Usuario Final
1.  **Actualización de Datos:** Ingrese las fallas en `tbl_bitacora` y la planificación semanal en `tbl_programacion` en su Google Sheet.
2.  **Refresco:** En la app, presione "R" o limpie la caché si acaba de editar el Excel.
3.  **Análisis:**
    *   Use el **KPI Dashboard** para ver qué equipos fallan más y su disponibilidad real vs. programada.
    *   Use el **Control Presupuestario** para ver si se está excediendo del gasto mensual permitido.
