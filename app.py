import streamlit as st
from pathlib import Path
import pandas as pd
from typing import Dict, Optional, List
import math
import io
import os
import datetime
import plotly.graph_objects as go
import plotly.express as px

# Página ancha y título
st.set_page_config(layout="wide", page_title="Dashboard")

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


@st.cache_data(ttl=600)
def load_sheets(xls_path: Path) -> Dict[str, pd.DataFrame]:
    # 0. Try loading from Google Sheets (Cloud / Secrets)
    # Check if secrets are nested under [gcp_service_account] or at root
    creds_dict = None
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    elif "type" in st.secrets and st.secrets["type"] == "service_account":
        # Fallback: User pasted JSON content directly without header
        creds_dict = dict(st.secrets)

    if creds_dict:
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(creds)
            
            # Open the Google Sheet by Key (more reliable)
            sheet_key = "1Xxl5G53qe8zjRy2XAkscrCBKp6_OTMHTlcKdCJshWYU"
            try:
                sh = client.open_by_key(sheet_key)
            except gspread.SpreadsheetNotFound:
                st.error(f"No se encontró el Google Sheet con ID '{sheet_key}'. Asegúrate de compartirlo con el email del robot: {creds_dict.get('client_email', 'unknown')}")
                return {}

            # Read specific worksheets
            sheets_to_load = ["tbl_bitacora", "OM", "Presupuesto", "Otros_Gastos"]
            loaded_data = {}
            
            for sheet_name in sheets_to_load:
                try:
                    ws = sh.worksheet(sheet_name)
                    data = ws.get_all_records()
                    # If data is empty, create empty DataFrame
                    if not data:
                        loaded_data[sheet_name] = pd.DataFrame()
                    else:
                        loaded_data[sheet_name] = pd.DataFrame(data)
                except gspread.WorksheetNotFound:
                    if sheet_name == "tbl_bitacora":
                        # Fallback for main sheet
                        try:
                            ws = sh.get_worksheet(0)
                            data = ws.get_all_records()
                            loaded_data[sheet_name] = pd.DataFrame(data)
                            st.warning(f"No se encontró 'tbl_bitacora', usando la primera hoja: '{ws.title}'")
                        except:
                            loaded_data[sheet_name] = pd.DataFrame()
                    else:
                        # Optional sheets return empty if missing
                        loaded_data[sheet_name] = pd.DataFrame()

            return loaded_data

        except Exception as e:
            st.error(f"Error conectando a Google Sheets: {e}")
            # Fallthrough to local files if GSheets fails
            pass
    else:
        if not xls_path.exists():
            st.warning("No se detectaron credenciales de Google Sheets en st.secrets. Verifica la configuración en 'Advanced Settings'.")
            # Debug: Show what keys are actually present to help the user fix it
            st.info(f"Depuración: Las claves encontradas en 'Secrets' son: {list(st.secrets.keys())}")

    # Performance: avoid loading the whole workbook (xlsm) which can be large and slow
    # Fast path: use a cached CSV if present.
    # In cloud deployment, xls_path might not exist, so we rely on CSV.
    csv_cache = xls_path.parent / "tbl_bitacora.csv"
    
    # 1. Try loading CSV first
    if csv_cache.exists():
        # If Excel exists, check timestamps to ensure CSV is fresh
        if xls_path.exists():
            if csv_cache.stat().st_mtime >= xls_path.stat().st_mtime:
                try:
                    df = pd.read_csv(csv_cache, parse_dates=True, encoding="utf-8-sig")
                    return {"tbl_bitacora": df}
                except Exception:
                    pass
        else:
            # Excel missing (Cloud scenario), just use CSV
            try:
                df = pd.read_csv(csv_cache, parse_dates=True, encoding="utf-8-sig")
                return {"tbl_bitacora": df}
            except Exception:
                pass

    # 2. If CSV failed or is old, try reading Excel (if it exists)
    if xls_path.exists():
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
    
    return {}


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
    # Force dayfirst=True here as well
    df2["__fecha_parsed"] = pd.to_datetime(df2[fecha_col], errors="coerce", dayfirst=True)
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
    
    # Load data (Google Sheets -> CSV -> Excel)
    sheets = load_sheets(xls)
    
    # Debug: Show loaded sheets and columns (Temporary for verification)
    with st.expander("Debug: Ver datos cargados (Google Sheets)", expanded=False):
        st.write("Hojas cargadas:", list(sheets.keys()))
        for name, data in sheets.items():
            st.write(f"**{name}**: {data.shape[0]} filas, {data.shape[1]} columnas")
            if not data.empty:
                st.write(list(data.columns))
    
    # Check if we got any data
    if not sheets or "tbl_bitacora" not in sheets:
        st.error("No se encontraron datos. Asegúrese de que la conexión a Google Sheets esté configurada o que exista 'tbl_bitacora.csv' localmente.")
        return

    df = sheets["tbl_bitacora"].copy()

    # Use explicit radio selector for sections to keep selection stable across reruns
    selection = st.radio("Sección", ["KPI Dashboard", "Control Presupuestario", "Bitácora", "Disponibilidad"], index=0, key="app_tab")

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
            # Force dayfirst=True to handle DD/MM/YYYY correctly
            df_k["__fecha_parsed"] = pd.to_datetime(df_k[fecha_col_k], errors="coerce", dayfirst=True)
            df_k["__fecha_date"] = df_k["__fecha_parsed"].dt.date

            valid_dates = df_k["__fecha_date"].dropna()
            if valid_dates.empty:
                st.warning("No se encontraron fechas válidas en la columna de fecha.")
                default_start = datetime.date.today()
                default_end = datetime.date.today()
            else:
                default_start = valid_dates.min()
                default_end = valid_dates.max()

            start = st.date_input("Fecha inicio", value=default_start, key="kpi_start")
            end = st.date_input("Fecha fin", value=default_end, key="kpi_end")

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

    # Control Presupuestario
    elif selection == "Control Presupuestario":
        st.subheader("Control Presupuestario (Budget vs Actual)")
        
        # 1. Load DataFrames
        df_om = sheets.get("OM", pd.DataFrame())
        df_presupuesto = sheets.get("Presupuesto", pd.DataFrame())
        df_otros = sheets.get("Otros_Gastos", pd.DataFrame())
        
        # 2. Validate Columns
        # Check OM columns
        om_date_col = find_column(df_om, ["fecha entrada", "fecha inicio", "date"])
        om_rep_col = find_column(df_om, ["costo repuestos", "repuestos"])
        om_serv_col = find_column(df_om, ["costo servicios", "servicios"])
        
        # Check Presupuesto columns
        pre_year_col = find_column(df_presupuesto, ["año", "year"])
        pre_month_col = find_column(df_presupuesto, ["mes", "month"])
        pre_amount_col = find_column(df_presupuesto, ["monto", "presupuesto", "budget"])
        
        # Check Otros_Gastos columns
        og_date_col = find_column(df_otros, ["fecha", "date"])
        og_amount_col = find_column(df_otros, ["monto", "amount", "valor"])
        og_cat_col = find_column(df_otros, ["categoria", "category", "tipo"])
        
        if df_presupuesto.empty or not (pre_year_col and pre_month_col and pre_amount_col):
            st.warning("⚠️ La hoja 'Presupuesto' está vacía o le faltan columnas (Año, Mes, Monto_Presupuesto). Por favor complétala en Google Sheets.")
        else:
            # --- PROCESS DATA ---
            
            # A. Process Budget (Presupuesto)
            # Filter by Year (assume current year or let user select)
            current_year = datetime.date.today().year
            years_avail = sorted(df_presupuesto[pre_year_col].unique())
            selected_year = st.selectbox("Seleccionar Año", years_avail, index=len(years_avail)-1 if years_avail else 0)
            
            budget_df = df_presupuesto[df_presupuesto[pre_year_col] == selected_year].copy()
            
            # Map month names to numbers if necessary, or ensure they are consistent
            # For simplicity, let's assume they are strings like "Enero", "Febrero" or numbers 1-12
            # We will try to standardize to Month Number for sorting
            month_map = {
                "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
                "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
            }
            
            def get_month_num(val):
                if isinstance(val, int): return val
                s = str(val).lower().strip()
                return month_map.get(s, 0)

            budget_df["_month_num"] = budget_df[pre_month_col].apply(get_month_num)
            budget_df = budget_df.sort_values("_month_num")
            
            def clean_currency(val):
                if pd.isna(val): return 0.0
                if isinstance(val, (int, float)): return float(val)
                s = str(val).replace("$", "").replace(".", "").replace(",", ".") # Remove $ and thousands separator, fix decimal
                try:
                    return float(s)
                except:
                    return 0.0

            # B. Process Actuals (Gastos)
            actuals = []
            
            # B1. From OM (Repuestos & Servicios)
            if not df_om.empty and om_date_col:
                # Clean and parse dates
                df_om["_date"] = pd.to_datetime(df_om[om_date_col], errors="coerce", dayfirst=True)
                df_om["_year"] = df_om["_date"].dt.year
                df_om["_month"] = df_om["_date"].dt.month
                
                # Filter by selected year
                df_om_year = df_om[df_om["_year"] == selected_year].copy()
                
                # Sum Repuestos
                if om_rep_col:
                    # Clean currency column
                    df_om_year[om_rep_col] = df_om_year[om_rep_col].apply(clean_currency)
                    rep_sum = df_om_year.groupby("_month")[om_rep_col].sum().reset_index()
                    for _, r in rep_sum.iterrows():
                        actuals.append({"Month": r["_month"], "Category": "Repuestos y Mat.", "Amount": r[om_rep_col]})
                
                # Sum Servicios
                if om_serv_col:
                    # Clean currency column
                    df_om_year[om_serv_col] = df_om_year[om_serv_col].apply(clean_currency)
                    serv_sum = df_om_year.groupby("_month")[om_serv_col].sum().reset_index()
                    for _, r in serv_sum.iterrows():
                        actuals.append({"Month": r["_month"], "Category": "Contratistas", "Amount": r[om_serv_col]})

            # B2. From Otros_Gastos
            if not df_otros.empty and og_date_col and og_amount_col:
                df_otros["_date"] = pd.to_datetime(df_otros[og_date_col], errors="coerce", dayfirst=True)
                df_otros["_year"] = df_otros["_date"].dt.year
                df_otros["_month"] = df_otros["_date"].dt.month
                
                df_otros_year = df_otros[df_otros["_year"] == selected_year].copy()
                
                # Clean amount column
                df_otros_year[og_amount_col] = df_otros_year[og_amount_col].apply(clean_currency)
                
                # Group by Month and Category
                if og_cat_col:
                    og_sum = df_otros_year.groupby(["_month", og_cat_col])[og_amount_col].sum().reset_index()
                    for _, r in og_sum.iterrows():
                        actuals.append({"Month": r["_month"], "Category": r[og_cat_col], "Amount": r[og_amount_col]})
                else:
                    # If no category, group all as "Otros"
                    og_sum = df_otros_year.groupby("_month")[og_amount_col].sum().reset_index()
                    for _, r in og_sum.iterrows():
                        actuals.append({"Month": r["_month"], "Category": "Otros Gastos", "Amount": r[og_amount_col]})

            # Create DataFrame for Actuals
            df_actuals = pd.DataFrame(actuals)
            
            if df_actuals.empty:
                st.info("No hay gastos registrados para este año.")
            else:
                # --- VISUALIZATION ---
                
                # 1. Annual Waterfall (Budget vs Months)
                month_names = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 
                               7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
                
                # Calculate Annual Budget
                total_annual_budget = budget_df[pre_amount_col].sum()
                
                # Calculate Monthly Expenses
                monthly_expenses = df_actuals.groupby("Month")["Amount"].sum().reset_index()
                monthly_expenses["MonthName"] = monthly_expenses["Month"].map(month_names)
                monthly_expenses = monthly_expenses.sort_values("Month")
                
                # --- WATERFALL CHART ---
                st.markdown(f"### Flujo de Caja Anual - {selected_year}")
                
                # Prepare data for Waterfall
                # Start: Annual Budget
                # Decrements: Months
                # End: Available
                
                measure = ["absolute"]  # For Budget
                x_data = ["Presupuesto"]
                y_data = [total_annual_budget]
                text_data = [f"${total_annual_budget:,.0f}"]
                
                total_spent = 0
                
                # Add months
                for _, row in monthly_expenses.iterrows():
                    m_name = row["MonthName"]
                    amt = row["Amount"]
                    measure.append("relative")
                    x_data.append(m_name)
                    y_data.append(-amt) # Negative because it's a cost
                    text_data.append(f"-${amt:,.0f}")
                    total_spent += amt
                
                # Final: Available
                available = total_annual_budget - total_spent
                measure.append("total")
                x_data.append("Disponible")
                y_data.append(None)
                text_data.append(f"${available:,.0f}")
                
                # Create Figure with White Background style to match reference
                fig = go.Figure(go.Waterfall(
                    name = "20", orientation = "v",
                    measure = measure,
                    x = x_data,
                    textposition = "outside",
                    text = text_data,
                    y = y_data,
                    connector = {"line":{"color":"#333333", "width": 1}},
                    decreasing = {"marker":{"color":"#c00000"}}, # Dark Red for costs
                    increasing = {"marker":{"color":"#0f52ba"}}, # Dark Blue for budget
                    totals = {"marker":{"color":"#0f52ba"}},     # Dark Blue for result
                    textfont = {"size": 14, "color": "black", "family": "Arial"}
                ))
                
                fig.update_layout(
                    title = dict(text=f"Presupuesto vs Gastos ({selected_year})", font=dict(size=20, color="black")),
                    showlegend = False,
                    plot_bgcolor = "white",
                    paper_bgcolor = "white",
                    font = dict(color="black", size=12),
                    xaxis = dict(tickfont=dict(size=12, color="black"), showgrid=False),
                    yaxis = dict(tickfont=dict(size=12, color="black"), title="Monto ($)", showgrid=True, gridcolor="#e5e5e5"),
                    autosize=True,
                    height=500,
                    bargap=0.2
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # --- SUMMARY TABLE ---
                st.markdown("### Resumen Anual")
                
                # Pivot table: Rows = Month, Cols = Category
                pivot_df = df_actuals.pivot_table(index="Month", columns="Category", values="Amount", aggfunc="sum", fill_value=0)
                
                # Add Budget Column
                budget_map = budget_df.set_index("_month_num")[pre_amount_col]
                pivot_df["Presupuesto"] = pivot_df.index.map(budget_map).fillna(0)
                
                # Add Total Spent
                cat_cols = [c for c in pivot_df.columns if c != "Presupuesto"]
                pivot_df["Total Gastos"] = pivot_df[cat_cols].sum(axis=1)
                
                # Add Available
                pivot_df["Disponible"] = pivot_df["Presupuesto"] - pivot_df["Total Gastos"]
                
                # Rename Index to Names
                pivot_df.index = pivot_df.index.map(lambda x: month_names.get(x, x))
                
                # Format as currency (optional, string conversion)
                st.dataframe(pivot_df.style.format("${:,.0f}"))

    # Por Fecha/Turno
    elif selection == "Bitácora":
        st.subheader("Bitácora")
        fecha_col = find_column(df, ["fecha", "date"]) or ""
        if fecha_col == "":
            st.error("La hoja `tbl_bitacora` no contiene una columna de fecha reconocible.")
        else:
            df_local = df.copy()
            # Force dayfirst=True to handle DD/MM/YYYY correctly
            df_local["__fecha_parsed"] = pd.to_datetime(df_local[fecha_col], errors="coerce", dayfirst=True)
            df_local["__fecha_date"] = df_local["__fecha_parsed"].dt.date
            
            valid_dates = df_local["__fecha_date"].dropna()
            if valid_dates.empty:
                max_date = datetime.date.today()
            else:
                max_date = valid_dates.max()

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
                # Force dayfirst=True
                df_bit["__fecha_parsed"] = pd.to_datetime(df_bit[fecha_col_b], errors="coerce", dayfirst=True)
                df_bit["__fecha_date"] = df_bit["__fecha_parsed"].dt.date
                
                valid_dates = df_bit["__fecha_date"].dropna()
                if valid_dates.empty:
                    default_s = datetime.date.today()
                    default_e = datetime.date.today()
                else:
                    default_s = valid_dates.min()
                    default_e = valid_dates.max()

                s = st.date_input("Fecha inicio", value=default_s, key="disp_start")
                e = st.date_input("Fecha fin", value=default_e, key="disp_end")
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
