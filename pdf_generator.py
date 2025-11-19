from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from datetime import datetime
import pandas as pd

class PDFGenerator:
    def generar_reporte_diario(self, df_ventas_dia, no_venta_final):
        """Genera el PDF con las ventas del día, separadas por categoría."""
        
        fecha_reporte = datetime.now().strftime('%Y-%m-%d')
        filename = f"Reporte_Ventas_Dia_{fecha_reporte}.pdf"
        c = canvas.Canvas(filename, pagesize=letter)
        ancho, alto = letter

        # --- Título ---
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, alto - 50, f"REPORTE DE VENTAS DIARIAS DE FARMACIA")
        c.setFont("Helvetica", 12)
        c.drawString(50, alto - 70, f"Fecha: {fecha_reporte}")
        c.drawString(50, alto - 85, f"Total de Ventas: {no_venta_final}")

        y_pos = alto - 120
        
        # --- Resumen por Categoría y Pago ---
        resumen_categoria = df_ventas_dia.groupby('Categoria')['TotalLinea'].sum().reset_index()
        resumen_pago = df_ventas_dia.groupby('MetodoPago')['TotalLinea'].sum().reset_index()

        # 1. Resumen por Categoría
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "Resumen por Categoría:")
        y_pos -= 15
        
        data_categoria = [['Categoría', 'Total (Q)']]
        for index, row in resumen_categoria.iterrows():
            data_categoria.append([row['Categoria'], f"Q {row['TotalLinea']:.2f}"])
        
        data_categoria.append(['TOTAL GENERAL', f"Q {resumen_categoria['TotalLinea'].sum():.2f}"])
        
        tabla_categoria = Table(data_categoria, colWidths=[100, 100])
        tabla_categoria.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        tabla_categoria.wrapOn(c, ancho, alto)
        tabla_categoria.drawOn(c, 50, y_pos - tabla_categoria._height)
        y_pos -= tabla_categoria._height + 30

        # 2. Resumen por Método de Pago
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "Resumen por Método de Pago:")
        y_pos -= 15
        
        data_pago = [['Método de Pago', 'Total (Q)']]
        for index, row in resumen_pago.iterrows():
            data_pago.append([row['MetodoPago'], f"Q {row['TotalLinea'].sum():.2f}"])
        
        tabla_pago = Table(data_pago, colWidths=[100, 100])
        tabla_pago.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        tabla_pago.wrapOn(c, ancho, alto)
        tabla_pago.drawOn(c, 50, y_pos - tabla_pago._height)
        
        # --- Guardar y Finalizar ---
        c.save()
        return filename