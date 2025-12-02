import pandas as pd
from pathlib import Path
import sys

def export_excel_to_csv():
    workspace = Path(__file__).parent
    xls_path = workspace / "BBDD_MANTENCION.xlsm"
    csv_path = workspace / "tbl_bitacora.csv"

    if not xls_path.exists():
        print(f"ERROR: No se encontró el archivo {xls_path}")
        sys.exit(1)

    print(f"Leyendo archivo Excel: {xls_path.name}...")
    try:
        # Leer solo la hoja necesaria
        df = pd.read_excel(xls_path, sheet_name="tbl_bitacora", engine="openpyxl")
        
        print(f"Exportando {len(df)} filas a CSV...")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"¡Éxito! Archivo creado: {csv_path.name}")
    except Exception as e:
        print(f"ERROR al procesar el archivo: {e}")
        sys.exit(1)

if __name__ == "__main__":
    export_excel_to_csv()
