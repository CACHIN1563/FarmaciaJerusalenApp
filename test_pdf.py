# test_pdf.py
from fpdf import FPDF
import pandas as pd
from datetime import datetime

# --- CLASE GENERADORA DE PDF (Copiada de web_app.py) ---
class PDFGenerator(FPDF):
    
    # ... (Copia aquí todo el contenido de la clase PDFGenerator) ...
    # Asegúrate de incluir los métodos header(), footer() y generar_reporte_diario_binario()

    # (Solo para fines de prueba, usa esta versión mínima)
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'TEST REPORTE', 0, 1, 'C') 

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

    def generar_reporte_diario_binario(self, ventas_del_dia, total_efectivo, total_tarjeta_neto, recargo_dia, total_dia):
        self.add_page()
        self.set_font('Arial', '', 10)
        self.cell(0, 10, f'Total: Q {total_dia:.2f}', 0, 1, 'L')
        
        # EL PUNTO CRÍTICO
        return self.output(dest='S') # <--- Esto es lo que devuelve el 'bytearray'
# -------------------------------------------------------------

# --- LÓGICA DE PRUEBA ---
if __name__ == '__main__':
    # 1. Datos simulados (no importa mucho el contenido, solo la estructura)
    df_ventas = pd.DataFrame([
        {'NoVenta': 1, 'Cantidad': 2, 'Concepto': 'P1', 'PrecioUnitario': 5.0, 'TotalLinea': 10.0, 'EsAntibiotico': False},
    ])
    total = 10.0

    # 2. Instanciar y generar
    pdf_reporte = PDFGenerator(orientation='P', unit='mm', format='Letter')
    pdf_data = pdf_reporte.generar_reporte_diario_binario(df_ventas, total, 0.0, 0.0, total)
    
    # 3. Imprimir el tipo de dato y los primeros bytes
    print(f"Tipo de dato devuelto: {type(pdf_data)}")
    print(f"Primeros 20 bytes: {pdf_data[:20]}") 

    # 4. Intentar guardar en un archivo para verificar que se generó correctamente
    try:
        with open("prueba_salida.pdf", "wb") as f:
            f.write(pdf_data)
        print("✅ Archivo 'prueba_salida.pdf' generado con éxito. Revísalo.")
    except Exception as e:
        print(f"❌ Error al escribir el archivo: {e}")