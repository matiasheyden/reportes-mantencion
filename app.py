import streamlit as st
from pathlib import Path
import pandas as pd
from typing import Dict, Optional, List
import math
import io
import os

# Página ancha y título
st.set_page_config(layout="wide", page_title="Reportes de Mantención")

# Global CSS for a more professional look
_GLOBAL_CSS = """
<style>
/* Page background and container */
main .block-container{padding-top:2rem; max-width:1200px}
h1{font-family: 'Helvetica Neue', Arial, sans-serif; font-size:40px; color:#ffffff}
.stApp {background-color:#0b0f12}
/* Make most page text white for better contrast on dark background */
html, body, .stApp, main .block-container, .section-title, .small-muted, p, label, span, div, th, td, a, input, textarea, select, option {
    color: #ffffff !important;
}
/* Table styling in HTML render */
table {border-collapse: collapse; width: 100%; font-size:13px; font-family: 'Inter', 'Helvetica Neue', Arial;}
th {background: #0f1720; color: #ffffff; padding: 10px; text-align:left}
td {border: 1px solid #1f2933; padding: 10px; vertical-align: top; white-space: pre-wrap; word-break: break-word; color: #ffffff}
.section-title {font-size:20px; color:#ffffff; margin-bottom:8px}
.small-muted {font-size:12px; color:#bfc8cc}
/* Links / accents */
a { color: #93c5fd !important; }

/* Selection styling so selected text remains readable */
::selection { background: #2563eb; color: #ffffff; }
::-moz-selection { background: #2563eb; color: #ffffff; }

/* Make widgets and buttons use readable text color */
.stButton>button, .stMetric, .stMarkdown, .stText, .css-1x0x1gf, .css-1d391kg {
    color: #ffffff !important;
}
/* AG-Grid specific overrides (st-aggrid) so cells and headers are white */
.ag-root, .ag-root *, .ag-theme-alpine, .ag-theme-balham, .ag-theme-streamlit, .ag-theme-material {
    color: #ffffff !important;
}
.ag-header-cell, .ag-header-cell-label, .ag-header, .ag-cell, .ag-cell-value, .ag-row, .ag-cell-wrapper {
    color: #ffffff !important;
    background-color: transparent !important;
}
.ag-center-cols-viewport, .ag-body-viewport, .ag-body-viewport .ag-row {
    background-color: transparent !important;
}
/* make links inside grid white */
.ag-root a, .ag-root a:link, .ag-root a:visited { color: #93c5fd !important; }
/* ensure selected cells remain readable */
.ag-row-selected .ag-cell, .ag-row-focus .ag-cell, .ag-cell-focus { background: rgba(37,99,235,0.12) !important; color: #ffffff !important; }
/* scrollbar thumb contrast for embedded grids */
.ag-body-viewport::-webkit-scrollbar-thumb { background-color: rgba(255,255,255,0.12); }
</style>
"""
st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def find_column(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
    for col in df.columns:
        low = str(col).lower()
        for kw in keywords:
            if kw in low:
                return col
    return None


@st.cache_data
def load_sheets(xls_path: Path) -> Dict[str, pd.DataFrame]:
    # Performance: avoid loading the whole workbook (xlsm) which can be large and slow
    # Fast path: use a cached CSV if present and newer than the Excel file
    csv_cache = xls_path.parent / "tbl_bitacora.csv"
    try:
        if csv_cache.exists() and csv_cache.stat().st_mtime >= xls_path.stat().st_mtime:
            df = pd.read_csv(csv_cache, parse_dates=True, encoding="utf-8-sig")
            return {"tbl_bitacora": df}
    except Exception:
        # If cache check/reading fails, continue to try reading Excel
        pass

    try:
        # Try reading only the sheet we actually use (much faster than sheet_name=None)
        df = pd.read_excel(xls_path, sheet_name="tbl_bitacora", engine="openpyxl")
        # Save a CSV cache to speed up subsequent loads (best-effort)
        try:
            df.to_csv(csv_cache, index=False, encoding="utf-8-sig")
        except Exception:
            pass
        return {"tbl_bitacora": df}
    except Exception:
        # Last-resort: fall back to reading all sheets (original behaviour)
        return pd.read_excel(xls_path, sheet_name=None, engine="openpyxl")


def compute_downtime_minutes(row: pd.Series, det_min_col: Optional[str], inicio_col: Optional[str], fin_col: Optional[str]) -> float:
    # prefer explicit downtime column
    if det_min_col and det_min_col in row.index:
        try:
            v = row[det_min_col]
            if pd.isna(v):
                raise ValueError
            if isinstance(v, str):
                v = v.replace(",", ".")
            return float(v)
        except Exception:
            pass
    # try compute from start/end datetimes
    try:
        if inicio_col and fin_col and inicio_col in row.index and fin_col in row.index:
            a = pd.to_datetime(row[inicio_col], errors="coerce")
            b = pd.to_datetime(row[fin_col], errors="coerce")
            if pd.isna(a) or pd.isna(b):
                return 0.0
            delta = b - a
            return max(delta.total_seconds() / 60.0, 0.0)
    except Exception:
        return 0.0
    return 0.0


def generate_pdf_from_dataframe(df: pd.DataFrame, out_path: str):
    """Try to generate a simple PDF from a pandas DataFrame using reportlab.
    Returns True if successful, False if reportlab not installed or fails.
    """
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
    except Exception:
        return False

    # prepare PDF document (landscape provides wider tables; portrait may be selected if preferred)
    doc = SimpleDocTemplate(out_path, pagesize=landscape(A4), leftMargin=18, rightMargin=18, topMargin=18, bottomMargin=18)
    elements = []
    styles = getSampleStyleSheet()
    # define clearer styles: black text on white background, readable sizes
    styleN = ParagraphStyle('NormalPDF', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=11, alignment=TA_LEFT, textColor=colors.black)
    styleH = ParagraphStyle('HeadingPDF', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, leading=16, alignment=TA_LEFT, textColor=colors.black)

    elements.append(Paragraph("Reporte - Bitácora", styleH))
    elements.append(Spacer(1, 8))

    # convert dataframe to list of lists and ensure strings (wrap using Paragraph)
    ncols = len(df.columns) if df is not None else 0
    data = []
    # header as bold Paragraphs
    header = [Paragraph(str(c), ParagraphStyle('hdr', parent=styleN, fontName='Helvetica-Bold', fontSize=10, textColor=colors.black)) for c in df.columns]
    data.append(header)

    for _, row in df.iterrows():
        cells = []
        for x in row.tolist():
            txt = "" if pd.isna(x) else str(x)
            txt = txt.replace("\n", "<br />")
            cells.append(Paragraph(txt, styleN))
        if len(cells) > ncols:
            merged = " ".join([c.getPlainText() for c in cells[ncols-1:]])
            cells = cells[: ncols - 1] + [Paragraph(merged, styleN)]
        elif len(cells) < ncols:
            cells += [Paragraph("", styleN)] * (ncols - len(cells))
        data.append(cells)

    # compute column widths to create a balanced, printable table
    page_w, page_h = landscape(A4)
    available_w = page_w - (doc.leftMargin + doc.rightMargin)
    # prefer to give first columns a bit less and description columns more room
    if ncols > 0:
        base_w = available_w / ncols
        col_w = [base_w for _ in range(ncols)]
        # if there are many columns, cap minimal width
        min_w = 40
        col_w = [max(min_w, w) for w in col_w]
    else:
        col_w = None

    tbl = Table(data, colWidths=col_w, repeatRows=1)
    # Light, printable style: white background, black text, subtle alternating row colors
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
    ]))

    elements.append(tbl)
    try:
        doc.build(elements)
        return True
    except Exception:
        return False


def filter_by_date_and_turn(df: pd.DataFrame, date, turno):
    fecha_col = find_column(df, ["fecha", "date"])
    turno_col = find_column(df, ["turno", "shift"])
    if fecha_col is None:
        return pd.DataFrame()
    df2 = df.copy()
    df2["__fecha_parsed"] = pd.to_datetime(df2[fecha_col], errors="coerce")
    df2["__fecha_date"] = df2["__fecha_parsed"].dt.date
    if turno_col is not None:
        df2["__turno_str"] = df2[turno_col].astype(str)
    else:
        df2["__turno_str"] = ""
    res = df2[df2["__fecha_date"] == date]
    if turno is not None and turno != "Todos":
        res = res[res["__turno_str"] == str(turno)]
    return res


def main():
    st.title("Reportes de Mantención")
    workspace = Path(__file__).parent
    xls = workspace / "BBDD_MANTENCION.xlsm"
    if not xls.exists():
        st.error(f"No se encontró el archivo de datos: {xls}")
        return

    sheets = load_sheets(xls)
    # Trabajar exclusivamente con tbl_bitacora
    if "tbl_bitacora" not in sheets:
        st.error("No se encontró la hoja `tbl_bitacora` en el archivo. Asegúrese de que exista y vuelva a cargar.")
        return
    df = sheets["tbl_bitacora"].copy()

    # Use explicit radio selector for sections to keep selection stable across reruns
    selection = st.radio("Sección", ["KPI Dashboard", "Bitácora", "Disponibilidad"], index=0, key="app_tab")

    # KPI Dashboard (simple)
    if selection == "KPI Dashboard":
        st.subheader("KPI Dashboard")
        target = "tbl_bitacora" if "tbl_bitacora" in sheets else sheet_choice
        df_k = sheets[target].copy()
        fecha_col_k = find_column(df_k, ["fecha", "date"]) or ""
        equipo_col_k = find_column(df_k, ["ubic", "equipo"]) or ""
        det_min_col_k = find_column(df_k, ["detenci", "detencion", "downtime", "min"]) or None
        inicio_col_k = find_column(df_k, ["inicio", "start"]) or None
        fin_col_k = find_column(df_k, ["fin", "end"]) or None

        if fecha_col_k == "" or equipo_col_k == "":
            st.warning("tbl_bitacora no tiene columnas Fecha o Equipo reconocibles. Seleccione otra hoja.")
        else:
            df_k["__fecha_parsed"] = pd.to_datetime(df_k[fecha_col_k], errors="coerce")
            df_k["__fecha_date"] = df_k["__fecha_parsed"].dt.date

            start = st.date_input("Fecha inicio", value=df_k["__fecha_date"].min(), key="kpi_start")
            end = st.date_input("Fecha fin", value=df_k["__fecha_date"].max(), key="kpi_end")

            mask = (df_k["__fecha_date"] >= start) & (df_k["__fecha_date"] <= end)
            period = df_k[mask].copy()

            if period.empty:
                st.info("No hay datos en el rango seleccionado.")
            else:
                period["__downtime_min"] = period.apply(lambda r: compute_downtime_minutes(r, det_min_col_k, inicio_col_k, fin_col_k), axis=1)
                total_downtime = period["__downtime_min"].sum()
                event_count = len(period)
                period_minutes = ((end - start).days + 1) * 24 * 60
                mttr = (total_downtime / event_count) if event_count > 0 else 0.0
                mtbf = (period_minutes / event_count) if event_count > 0 else math.nan
                availability = ((period_minutes - total_downtime) / period_minutes) * 100 if period_minutes > 0 else math.nan

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Downtime total (min)", f"{total_downtime:.1f}")
                c2.metric("Eventos", f"{event_count}")
                c3.metric("MTTR (min)", f"{mttr:.1f}")
                c4.metric("MTBF (min)", f"{mtbf:.1f}" if not math.isnan(mtbf) else "N/A")
                c5.metric("Disponibilidad (%)", f"{availability:.2f}%")

                st.markdown("---")
                grouped = period.groupby(equipo_col_k).agg(events=(fecha_col_k, "count"), downtime_total=("__downtime_min", "sum")).reset_index()
                grouped = grouped.sort_values(by="downtime_total", ascending=False)
                st.subheader("Top equipos por downtime")
                st.dataframe(grouped.head(50))
                st.download_button("Descargar CSV - KPI por equipo", data=grouped.to_csv(index=False, encoding="utf-8-sig"), file_name="kpi_por_equipo.csv", mime="text/csv")

                # Top 5 equipos por intervenciones con mini-pies
                top5 = grouped.nlargest(5, "events")
                if not top5.empty:
                    st.subheader("Top 5 — Intervenciones y disponibilidad")
                    cols = st.columns(min(5, len(top5)))
                    try:
                        import plotly.express as px
                        for (i, row), col in zip(top5.iterrows(), cols):
                            eq = row[equipo_col_k]
                            ev = int(row["events"]) if not pd.isna(row["events"]) else 0
                            down = float(row["downtime_total"]) if not pd.isna(row["downtime_total"]) else 0.0
                            # estimate availability percent for mini-pie
                            # use period_minutes as same used above
                            avail_pct = max(0.0, 100.0 - (down / (period_minutes if period_minutes>0 else 1)) * 100.0)
                            fig = px.pie(values=[avail_pct, 100 - avail_pct], names=["Disponible", "Downtime"], hole=0.4)
                            fig.update_traces(textinfo='percent', hoverinfo='label+percent')
                            fig.update_layout(margin=dict(t=20, b=20, l=10, r=10), showlegend=False)
                            col.markdown(f"**{eq}**\nEventos: {ev}")
                            # use unique key per mini-chart to avoid Streamlit auto-id collisions
                            try:
                                col.plotly_chart(fig, width='stretch', key=f"mini_pie_{i}_{str(eq)}")
                            except TypeError:
                                # older streamlit versions may not support width param; fallback to use_container_width
                                col.plotly_chart(fig, use_container_width=True, key=f"mini_pie_{i}_{str(eq)}")
                    except Exception as e:
                        # fallback: simple table view with clear message
                        st.warning(f"plotly no disponible o error al generar gráficos: {e}. Mostrando tabla en su lugar.")
                        try:
                            if equipo_col_k and equipo_col_k in top5.columns:
                                st.dataframe(top5[[equipo_col_k, 'events', 'downtime_total']])
                            else:
                                st.dataframe(top5)
                        except Exception:
                            st.dataframe(top5.reset_index(drop=True))

    # Por Fecha/Turno
    if selection == "Bitácora":
        st.subheader("Bitácora")
        fecha_col = find_column(df, ["fecha", "date"]) or ""
        if fecha_col == "":
            st.error("La hoja `tbl_bitacora` no contiene una columna de fecha reconocible.")
        else:
            df_local = df.copy()
            df_local["__fecha_parsed"] = pd.to_datetime(df_local[fecha_col], errors="coerce")
            df_local["__fecha_date"] = df_local["__fecha_parsed"].dt.date
            max_date = df_local["__fecha_date"].max()
            # automatic update when choosing a date/turno (use unique keys to avoid widget id collision)
            date_selected = st.date_input("Fecha", value=max_date, key="bit_fecha")
            turno_col = find_column(df_local, ["turno", "shift"]) or None
            turno_selected = "Todos"
            if turno_col:
                turnos = df_local[df_local["__fecha_date"] == date_selected][turno_col].dropna().unique()
                options = ["Todos"] + sorted([str(t) for t in turnos])
                turno_selected = st.selectbox("Turno", options, key="bit_turno")

            expand = st.checkbox("Expandir vista completa", value=False, key="bit_expand")
            height = 1100 if expand else 420

            # apply filter automatically (no button)
            filtered = filter_by_date_and_turn(df_local, date_selected, turno_selected)
            if filtered.empty:
                st.warning("No hay registros para los parámetros seleccionados.")
            else:
                # Preparar columnas a mostrar y formatear fecha
                display = filtered.copy()
                display["Fecha"] = display["__fecha_parsed"].dt.strftime("%d/%m/%y")
                # columnas adicionales comunes
                cols_to_try = [turno_col, find_column(filtered, ["ubic", "equipo"]), find_column(filtered, ["especial", "tipo"]), find_column(filtered, ["observ", "desc"]) ]
                display_cols = [c for c in ["Fecha"] + cols_to_try if c and c in display.columns]
                display = display[display_cols]

                # Try to use st_aggrid if available for better UX (wrap text + per-column autoHeight)
                desc_col_name = find_column(display, ["observ", "desc", "observaciones"]) or None
                try:
                    from st_aggrid import AgGrid, GridOptionsBuilder
                    gb = GridOptionsBuilder.from_dataframe(display)
                    # enable wrapping globally
                    gb.configure_default_column(wrapText=True)
                    # if a description-like column exists, enable autoHeight for it
                    if desc_col_name:
                        try:
                            gb.configure_column(desc_col_name, autoHeight=True, wrapText=True)
                        except Exception:
                            pass
                    # let grid auto-size vertically when possible
                    gb.configure_grid_options(domLayout='autoHeight')
                    gridOptions = gb.build()
                    # estimate a reasonable max height (cap to avoid huge frames)
                    est_rows = max(10, min(1000, display.shape[0]))
                    max_h = min(2000, 40 + est_rows * 28)
                    AgGrid(display, gridOptions=gridOptions, enable_enterprise_modules=False, fit_columns_on_grid_load=True, height=max_h)
                except Exception:
                    # Renderizar tabla completa sin índice usando HTML (permite mostrar todo el contenido)
                    # estimate iframe height so rows can expand to show full content
                    def estimate_table_height(df_local, text_col=None):
                        rows = len(df_local)
                        base = 28
                        extra = 0
                        if text_col and text_col in df_local.columns:
                            for val in df_local[text_col].astype(str).fillna(""):
                                l = len(val)
                                # assume ~80 chars per wrapped line
                                lines = max(1, (l // 80) + 1)
                                extra += (lines - 1) * 16
                        # also account for other cells with long text
                        for col in df_local.columns:
                            if col == text_col:
                                continue
                            for val in df_local[col].astype(str).fillna(""):
                                if len(val) > 120:
                                    extra += 8
                        estimated = min(3000, max(300, rows * base + extra))
                        return estimated

                    html = display.to_html(index=False, escape=False)
                    # force inline styles on table elements so iframe displays white text
                    html = html.replace('<table', '<table style="color:#ffffff; background:transparent;"')
                    html = html.replace('<th', '<th style="color:#ffffff; background:transparent;"')
                    html = html.replace('<td', '<td style="color:#ffffff; background:transparent;"')
                    height_est = estimate_table_height(display, desc_col_name)
                    styled = (
                        """
                    <style>
                    html, body {background-color: #0f1720; color: #fff;}
                    table {border-collapse: collapse; width: 100%; font-size: 12px; font-family: Helvetica, Arial, sans-serif;}
                    th {background: #1f2933; color: #fff; padding: 8px;}
                    td {border: 1px solid #2b2b2b; padding: 8px; text-align: left; vertical-align: top; white-space: pre-wrap; word-break: break-word;}
                    /* ensure links inside iframe are readable */
                    a { color: #93c5fd !important; }
                    </style>
                    """ + html)
                    import streamlit.components.v1 as components
                    components.html(styled, height=int(height_est), scrolling=True)

                # Descarga CSV
                st.download_button("Descargar CSV", data=display.to_csv(index=False, encoding="utf-8-sig"), file_name="bitacora_reporte.csv", mime="text/csv")

                # Exportar a PDF (intenta usar reportlab)
                temp_pdf = Path("bitacora_reporte.pdf")
                ok = generate_pdf_from_dataframe(display, str(temp_pdf))
                if ok:
                    with open(temp_pdf, "rb") as f:
                        st.download_button("Descargar PDF (snapshot)", data=f, file_name="bitacora_reporte.pdf", mime="application/pdf")
                    try:
                        os.remove(temp_pdf)
                    except Exception:
                        pass
                else:
                    st.info("Para exportar a PDF instale la dependencia opcional 'reportlab' (pip install reportlab). El CSV sigue disponible.")

    # Disponibilidad (tab3)
    if selection == "Disponibilidad":
        st.subheader("Disponibilidad por equipo")
        if "tbl_bitacora" not in sheets:
            st.info("No existe la hoja 'tbl_bitacora' en el archivo. Seleccione otra hoja en la caja superior.")
        else:
            df_bit = sheets["tbl_bitacora"].copy()
            fecha_col_b = find_column(df_bit, ["fecha", "date"]) or ""
            equipo_col_b = find_column(df_bit, ["ubic", "equipo"]) or ""
            if fecha_col_b == "" or equipo_col_b == "":
                st.error("tbl_bitacora no contiene 'Fecha' o 'Equipo' reconocibles.")
            else:
                df_bit["__fecha_parsed"] = pd.to_datetime(df_bit[fecha_col_b], errors="coerce")
                df_bit["__fecha_date"] = df_bit["__fecha_parsed"].dt.date
                s = st.date_input("Fecha inicio", value=df_bit["__fecha_date"].min(), key="disp_start")
                e = st.date_input("Fecha fin", value=df_bit["__fecha_date"].max(), key="disp_end")
                mask = (df_bit["__fecha_date"] >= s) & (df_bit["__fecha_date"] <= e)
                period = df_bit[mask].copy()
                if period.empty:
                    st.info("No hay datos en el rango seleccionado.")
                else:
                    det_col = find_column(period, ["detenci", "detencion", "downtime", "min"]) or None
                    inicio = find_column(period, ["inicio", "start"]) or None
                    fin = find_column(period, ["fin", "end"]) or None
                    period["__downtime_min"] = period.apply(lambda r: compute_downtime_minutes(r, det_col, inicio, fin), axis=1)
                    grouped = period.groupby(equipo_col_b).agg(events=(fecha_col_b, "count"), total_downtime_min=("__downtime_min", "sum")).reset_index()
                    period_minutes = ((e - s).days + 1) * 24 * 60
                    grouped["availability_pct"] = ((period_minutes - grouped["total_downtime_min"]) / period_minutes).clip(lower=0) * 100
                    grouped = grouped.sort_values(by="total_downtime_min", ascending=False)

                    # Mostrar tabla sin índice como HTML (para que el contenido completo sea visible)
                    display_g = grouped.rename(columns={equipo_col_b: "Ubicación/Equipo"})
                    htmlg = display_g.to_html(index=False, escape=False)
                    # force inline white text for iframe
                    htmlg = htmlg.replace('<table', '<table style="color:#ffffff; background:transparent;"')
                    htmlg = htmlg.replace('<th', '<th style="color:#ffffff; background:transparent;"')
                    htmlg = htmlg.replace('<td', '<td style="color:#ffffff; background:transparent;"')
                    styled_g = (
                        """
                    <style>
                    table {border-collapse: collapse; width: 100%;}
                    th, td {border: 1px solid #444; padding: 8px; text-align: left; vertical-align: top; white-space: pre-wrap; word-break: break-word;}
                    a { color: #93c5fd !important; }
                    </style>
                    """ + htmlg)
                    import streamlit.components.v1 as components
                    components.html(styled_g, height=360, scrolling=True)

                    st.download_button("Descargar CSV de disponibilidad", data=grouped.to_csv(index=False, encoding="utf-8-sig"), file_name="disponibilidad_por_equipo.csv", mime="text/csv")

                    # Sección: gráficos circulares por equipo (selección)
                    st.markdown("---")
                    st.subheader("Gráficos circulares por equipo")
                    equipos = list(grouped[equipo_col_b].astype(str))
                    default_sel = equipos[:6]
                    sel = st.multiselect("Seleccionar equipos (múltiple)", options=equipos, default=default_sel)
                    if sel:
                        # intentar usar plotly, si no está disponible mostrar barras como fallback
                        try:
                            import plotly.express as px
                            for eq in sel:
                                row = grouped[grouped[equipo_col_b].astype(str) == eq]
                                if row.empty:
                                    continue
                                avail = float(row["availability_pct"].iloc[0])
                                down = float(row["total_downtime_min"].iloc[0])
                                fig = px.pie(values=[avail, 100 - avail], names=["Disponible (%)", "Downtime (%)"], title=f"{eq} — Disponibilidad {avail:.1f}%")
                                # ensure each chart has unique key and uses new `width` param
                                try:
                                    st.plotly_chart(fig, width='stretch', key=f"disp_pie_{str(eq)}")
                                except TypeError:
                                    st.plotly_chart(fig, use_container_width=True, key=f"disp_pie_{str(eq)}")
                        except Exception:
                            # fallback: mostrar barras
                            st.warning("plotly no disponible, mostrando barras en su lugar.")
                            st.bar_chart(grouped.set_index(equipo_col_b)["availability_pct"].loc[sel])


if __name__ == "__main__":
    main()
