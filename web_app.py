import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from data_manager import DataManager 
from fpdf import FPDF 
import os 
import numpy as np 
import random 
import sys # Importación necesaria para PyInstaller y rutas dinámicas (aunque no se usa en este script, es buena práctica)

# ====================================================================
# CONFIGURACIÓN DE UTILIDADES
# ====================================================================

# --- LISTA DE VERSÍCULOS BÍBLICOS CORTOS ---
VERSICULOS_BIBLICOS = [
    "La fe viene por el oír, y el oír, por la palabra de Dios. (Romanos 10:17)",
    "Confía en el Señor de todo corazón, y no en tu propia inteligencia. (Proverbios 3:5)",
    "Todo lo puedo en Cristo que me fortalece. (Filipenses 4:13)",
    "Jesús le dijo: Yo soy el camino, y la verdad, y la vida. (Juan 14:6)",
    "Amados, amémonos unos a otros; porque el amor es de Dios. (1 Juan 4:7)",
    "El Señor es mi pastor; nada me faltará. (Salmo 23:1)",
    "Mas buscad primeramente el reino de Dios y su justicia. (Mateo 6:33)",
    "Estén siempre alegres. Oren sin cesar. (1 Tesalonicenses 5:16-17)",
    "Porque contigo está el manantial de la vida. (Salmo 36:9)",
    "Dios es amor. (1 Juan 4:8)",
]

# --- FUNCIÓN PARA OBTENER EL VERSÍCULO DIARIO ---
@st.cache_data(ttl=timedelta(hours=24))
def get_daily_verse():
    """Selecciona un versículo bíblico al azar."""
    return random.choice(VERSICULOS_BIBLICOS)


# --- CLASE GENERADORA DE PDF ---
class PDFGenerator(FPDF):
    """Clase personalizada para generar reportes en PDF."""
    
    def header(self):
        """Define el encabezado del PDF."""
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'FARMACIA JERUSALÉN - REPORTE DE VENTA', 0, 1, 'C') 
        self.set_font('Arial', '', 10)
        self.cell(0, 5, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'R')
        self.ln(5)

    def footer(self):
        """Define el pie de página del PDF."""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

    def generar_reporte_diario_binario(self, ventas_del_dia, total_efectivo, total_tarjeta_neto, recargo_dia, total_dia):
        """Genera el contenido del reporte de ventas y lo devuelve como bytes."""
        
        self.add_page()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_font('Arial', 'B', 12)
        
        # 1. Resumen de Totales
        self.cell(0, 10, 'RESUMEN DEL DÍA', 0, 1, 'L')
        self.set_font('Arial', '', 10)
        
        self.cell(0, 5, f"Total en Efectivo: Q {total_efectivo:.2f}", 0, 1, 'L')
        self.cell(0, 5, f"Total con Tarjeta (Neto): Q {total_tarjeta_neto:.2f}", 0, 1, 'L')

        if recargo_dia > 0:
            self.cell(0, 5, f"Monto de Recargo por Tarjeta (0.5%): Q {recargo_dia:.2f}", 0, 1, 'L')
        
        self.set_font('Arial', 'B', 10)
        self.cell(0, 5, f"TOTAL NETO DEL DÍA: Q {total_dia:.2f}", 0, 1, 'L')
        self.ln(5)
        
        # 2. Detalle de Transacciones
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'DETALLE DE TRANSACCIONES', 0, 1, 'L')
        
        # Definir el ancho de las columnas
        col_widths = [15, 30, 75, 20, 30] # NoVenta, Cantidad, Concepto, Precio, Total
        self.set_font('Arial', 'B', 8)
        self.cell(col_widths[0], 7, 'No. Venta', 1, 0, 'C')
        self.cell(col_widths[1], 7, 'Cant.', 1, 0, 'C')
        self.cell(col_widths[2], 7, 'Concepto', 1, 0, 'L')
        self.cell(col_widths[3], 7, 'P. Unitario', 1, 0, 'R')
        self.cell(col_widths[4], 7, 'TOTAL', 1, 1, 'R') 
        
        ventas_grouped = ventas_del_dia.sort_values(by='NoVenta')

        for index, row in ventas_grouped.iterrows():
            es_antibiotico = bool(row.get('EsAntibiotico', False))
            
            if es_antibiotico:
                self.set_fill_color(255, 255, 102) 
                self.set_draw_color(255, 165, 0)   
                self.set_font('Arial', 'U', 8)     
                fill = True
                concepto_display = f"{str(row['Concepto'])} (ANTIBIÓTICO)"
            else:
                self.set_fill_color(255, 255, 255) 
                self.set_draw_color(0, 0, 0)       
                self.set_font('Arial', '', 8)      
                fill = False
                concepto_display = str(row['Concepto'])

            self.cell(col_widths[0], 5, str(row['NoVenta']), 1, 0, 'C', fill=fill)
            self.cell(col_widths[1], 5, str(int(row['Cantidad'])), 1, 0, 'C', fill=fill)
            
            self.cell(col_widths[2], 5, concepto_display, 1, 0, 'L', fill=fill)
            
            if es_antibiotico:
                self.set_font('Arial', '', 8)
                
            self.cell(col_widths[3], 5, f"Q {row['PrecioUnitario']:.2f}", 1, 0, 'R', fill=fill)
            self.cell(col_widths[4], 5, f"Q {row['TotalLinea']:.2f}", 1, 1, 'R', fill=fill)

        # CORRECCIÓN CLAVE: Convertir la salida a 'bytes' explícitamente para Streamlit
        return bytes(self.output(dest='S'))


# --- CONSTANTE DE RECARGO ---
RECARGO_TARJETA = 0.005  # 0.5% de recargo

# ====================================================================
# CONFIGURACIÓN E INICIALIZACIÓN DEL ESTADO DE STREAMLIT
# ====================================================================

st.set_page_config(
    page_title="Farmacia Jerusalén | Gestión Web", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# Inicializar DataManager en el estado de la sesión
@st.cache_resource
def load_data_manager():
    return DataManager()

# Inicializar DataManager si no está en el estado de sesión (usando la función decorada)
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = load_data_manager()

# Inicializar el estado de la venta actual
if 'venta_actual' not in st.session_state:
    st.session_state.venta_actual = []

# Inicializar el No. de Venta y Lote
try:
    if 'no_venta' not in st.session_state:
        st.session_state.no_venta = st.session_state.data_manager.obtener_siguiente_no_venta()
    if 'lote_autogenerado' not in st.session_state:
        st.session_state.lote_autogenerado = st.session_state.data_manager.generar_siguiente_lote()
except Exception:
    st.session_state.no_venta = 1000 
    st.session_state.lote_autogenerado = "000001"
    
# Inicializar la página de navegación si no existe
if 'page' not in st.session_state:
    st.session_state['page'] = "🛒 Venta y Facturación"


# ====================================================================
# FUNCIONES DE AYUDA Y CÁLCULO
# ====================================================================

def _actualizar_total_venta():
    """Calcula y devuelve el total de la venta actual, aplicando recargo."""
    subtotal = sum(item['total_linea'] for item in st.session_state.venta_actual)
    
    recargo_total = sum(item.get('recargo_aplicado_linea', 0.0) for item in st.session_state.venta_actual)
        
    total = subtotal 
    
    subtotal_sin_recargo = total - recargo_total
    
    return subtotal_sin_recargo, recargo_total, total


# ====================================================================
# PANTALLA 1: VENTA Y FACTURACIÓN 
# ====================================================================

def pantalla_venta():
    # --- CSS para estilizar el total final ---
    st.markdown("""
        <style>
        /* Estilo para el contenedor del total final */
        .total-box {
            background-color: #F0F2F6; 
            border: 2px solid #28A745; 
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
            text-align: center;
        }
        /* Estilo para el texto grande del Total */
        .total-text {
            font-size: 2.5em; 
            font-weight: bold;
            color: #28A745; 
        }
        /* Estilo para los subtotales y recargo */
        .subtotal-text {
            font-size: 1.1em;
            color: #555555;
            margin-bottom: 5px;
        }
        </style>
        """, unsafe_allow_html=True)
    # ---------------------------------------------
    
    st.subheader(f"🛒 Venta y Facturación | No. {st.session_state.no_venta}")
    st.markdown("---")
    
    # ----------------------- INPUTS DE PRODUCTO -----------------------
    col1, col2, col3, col4, col_radio = st.columns([3, 1, 1.5, 1.5, 2])
    
    with col1:
        concepto = st.text_input("Concepto:", key="venta_concepto")
    with col2:
        cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1, key="venta_cantidad")
    with col3:
        precio_unitario = st.number_input("Precio Unitario (Q):", min_value=0.01, value=10.00, step=0.50, format="%.2f", key="venta_precio")
    with col4:
        categoria = st.selectbox("Categoría:", ['Farmacia', 'Tienda', 'Inyecciones'], key="venta_categoria")
    
    # NUEVO RADIOBUTTON PARA ANTIBIÓTICO
    with col_radio:
         st.markdown("Es Antibiótico:")
         es_antibiotico_val = st.radio(
            "", 
            ('NO', 'SÍ'),
            key="es_antibiotico_radio",
            horizontal=True
        )
         es_antibiotico = (es_antibiotico_val == 'SÍ')

        
    # --- MÉTODO DE PAGO Y BOTONES DE ACCIÓN ---
    col_pago, col_add, col_reset = st.columns([1.5, 1, 1.5])
    
    with col_pago:
        metodo_pago_val = st.radio(
            "Método de Pago:", 
            ('Efectivo', 'Tarjeta'),
            key="metodo_pago_radio"
        )
        
    with col_add:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ AGREGAR PRODUCTO", key="btn_agregar", use_container_width=True):
            if not concepto or cantidad <= 0 or precio_unitario <= 0:
                st.error("Verifique los datos de Concepto, Cantidad y Precio.")
            else:
                total_linea = cantidad * precio_unitario
                recargo_linea = 0.0
                
                if metodo_pago_val == 'Tarjeta':
                     recargo_linea = (cantidad * precio_unitario) * RECARGO_TARJETA
                     total_linea += recargo_linea
                     
                st.session_state.venta_actual.append({
                    'concepto': concepto, 
                    'cantidad': cantidad, 
                    'precio_unitario': precio_unitario, 
                    'total_linea': total_linea,
                    'categoria': categoria,
                    'metodo_pago': metodo_pago_val,
                    'es_antibiotico': es_antibiotico, 
                    'recargo_aplicado_linea': recargo_linea 
                })
                st.toast(f"Producto '{concepto}' agregado.", icon='✅', duration=5000) 

    with col_reset:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ CANCELAR/LIMPIAR VENTA", key="btn_reset_venta", use_container_width=True):
            st.session_state.venta_actual = []
            try:
                st.session_state.no_venta = st.session_state.data_manager.obtener_siguiente_no_venta()
            except:
                st.session_state.no_venta = 1000 
            st.toast("Venta cancelada y limpiada.", icon='🗑️', duration=5000) 
            st.rerun() 

    st.markdown("---")
    
    # ----------------------- TABLA DE ARTÍCULOS -----------------------
    st.subheader("Artículos en Venta")
    if st.session_state.venta_actual:
        df_venta = pd.DataFrame(st.session_state.venta_actual)
        
        df_venta['Antibiótico'] = df_venta['es_antibiotico'].apply(lambda x: 'SÍ' if x else 'NO')
        
        df_display = df_venta[['cantidad', 'concepto', 'precio_unitario', 'Antibiótico', 'total_linea']].copy()
        df_display.columns = ['Cant', 'Concepto del Producto', 'Precio Unitario (Q)', 'Antibiótico', 'Total (Q)']
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("La venta actual está vacía.")
    
    subtotal_sin_recargo, recargo_total, total_final = _actualizar_total_venta()
    
    st.markdown("---")
    
    # ----------------------- TOTALES Y BOTONES MEJORADOS -----------------------
    col_total, col_finish, col_reporte = st.columns([2.5, 1, 1.5])
    
    with col_total:
        st.markdown('<div class="total-box">', unsafe_allow_html=True)
                
        st.markdown(f'<p class="subtotal-text">SUBTOTAL (Productos): Q <strong>{subtotal_sin_recargo:.2f}</strong></p>', unsafe_allow_html=True)
        if recargo_total > 0:
            st.markdown(f'<p class="subtotal-text">RECARGO (0.5%): Q <strong>{recargo_total:.2f}</strong> <i>(Tarjeta)</i></p>', unsafe_allow_html=True)
            
        st.markdown(f'<p class="total-text">TOTAL A PAGAR: Q {total_final:.2f}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


    with col_finish:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ FINALIZAR VENTA", key="btn_finalizar", use_container_width=True):
            if not st.session_state.venta_actual:
                st.warning("No hay productos para finalizar la venta.")
                return
            
            try:
                # 1. Guardar la venta
                no_venta = st.session_state.data_manager.guardar_venta(st.session_state.venta_actual, recargo_aplicado=recargo_total)
                
                # 2. Actualizar inventario
                st.session_state.data_manager.actualizar_inventario_por_venta(st.session_state.venta_actual) 

                st.success(f"Venta No. {no_venta} registrada. Total Final: Q {total_final:.2f}")
                
                # 3. Resetear el estado
                st.session_state.venta_actual = []
                st.session_state.no_venta = st.session_state.data_manager.obtener_siguiente_no_venta()
                
                st.rerun() 
            except Exception as e:
                st.error(f"Error al finalizar la venta o actualizar inventario: {e}")


    with col_reporte:
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 4. Generación de Reporte PDF
        try:
            df_ventas = st.session_state.data_manager.leer_ventas()
            hoy = datetime.now().strftime('%Y-%m-%d')
            ventas_hoy = df_ventas[df_ventas['Fecha'].astype(str) == hoy]
            
            if not ventas_hoy.empty:
                
                ventas_efectivo = ventas_hoy[ventas_hoy['MetodoPago'] == 'Efectivo']
                ventas_tarjeta = ventas_hoy[ventas_hoy['MetodoPago'] == 'Tarjeta']
                
                total_efectivo = ventas_efectivo['TotalLinea'].apply(pd.to_numeric, errors='coerce').sum()
                recargo_dia = ventas_hoy['RecargoAplicado'].apply(pd.to_numeric, errors='coerce').sum()

                total_tarjeta_sum = ventas_tarjeta['TotalLinea'].apply(pd.to_numeric, errors='coerce').sum()
                recargo_tarjeta_sum = ventas_tarjeta['RecargoAplicado'].apply(pd.to_numeric, errors='coerce').sum()
                total_tarjeta_neto = total_tarjeta_sum - recargo_tarjeta_sum
                
                total_dia = total_efectivo + total_tarjeta_neto + recargo_dia 

                pdf_reporte = PDFGenerator(orientation='P', unit='mm', format='Letter') 

                pdf_reporte.set_author("Sistema de Gestión Farmacia Jerusalén")
                # Aquí 'pdf_data' ya es el objeto 'bytes' corregido.
                pdf_data = pdf_reporte.generar_reporte_diario_binario(
                    ventas_hoy, 
                    total_efectivo=total_efectivo,       
                    total_tarjeta_neto=total_tarjeta_neto, 
                    recargo_dia=recargo_dia,             
                    total_dia=total_dia                  
                ) 
                
                st.download_button(
                    label="📄 DESCARGAR PDF DEL DÍA",
                    data=pdf_data,
                    file_name=f"Reporte_Diario_Ventas_{hoy}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                 st.button("📄 NO HAY VENTAS HOY", key="btn_no_pdf", disabled=True, use_container_width=True)

        except Exception as e:
             st.button("❌ ERROR AL GENERAR PDF", key="btn_pdf_fail", disabled=True, use_container_width=True)
             st.error(f"Error en la generación del PDF: {e}") 


# ====================================================================
# PANTALLA 2: INGRESO DE MERCADERÍA 
# ====================================================================

def pantalla_ingreso():
    st.subheader("📦 Ingreso de Mercadería")
    
    with st.expander("Registro de Nuevos Productos y Facturas", expanded=True):
        
        # --- DATOS DE LA FACTURA ---
        st.subheader("Datos de la Factura de Compra")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            no_factura = st.text_input("No. Factura:", key="ingreso_no_factura").strip()
        with col_f2:
            proveedor = st.text_input("Proveedor:", key="ingreso_proveedor").strip()
        with col_f3:
            monto_calculado = st.empty() 
            fecha_pago = st.date_input("Fecha Venc. Pago:", datetime.now().date() + timedelta(days=30), key="ingreso_fecha_pago")

        st.markdown("---")
        
        # --- DATOS DEL PRODUCTO ---
        st.subheader("Datos del Producto Ingresado")
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        
        with col_p1:
            concepto = st.text_input("Concepto/Nombre:", key="ingreso_concepto").strip()
        with col_p2:
            cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1, key="ingreso_cantidad")
        with col_p3:
            costo_unitario = st.number_input("Costo Unitario (Q):", min_value=0.01, value=5.00, step=0.10, format="%.2f", key="ingreso_costo")
        with col_p4:
            categoria = st.selectbox("Categoría:", ['Farmacia', 'Tienda'], key="ingreso_categoria")
        
        col_l1, col_l2, col_anti = st.columns([1, 1, 1])
        with col_l1:
            lote_usar = st.session_state.data_manager.generar_siguiente_lote()
            st.text_input("Lote (Auto-Generado):", value=lote_usar, disabled=True, key="ingreso_lote_display")
        with col_l2:
            fecha_vencimiento = st.date_input("Fecha Venc. Producto:", datetime.now().date() + timedelta(days=365), key="ingreso_fecha_vencimiento")
        
        # NUEVO RADIOBUTTON PARA ANTIBIÓTICO en Ingreso
        with col_anti:
             st.markdown("Es Antibiótico:")
             es_antibiotico_ingreso_val = st.radio(
                "", 
                ('NO', 'SÍ'),
                key="es_antibiotico_ingreso_radio_input", 
                horizontal=True
            )
             es_antibiotico_ingreso = (es_antibiotico_ingreso_val == 'SÍ')

        # Cálculo del monto total y actualización del placeholder
        try:
            cantidad_num = float(cantidad)
            costo_num = float(costo_unitario)
            monto_total = cantidad_num * costo_num
            monto_calculado.info(f"Monto Total de la Factura: Q {monto_total:.2f}")
        except ValueError:
            monto_calculado.info("Monto Total: Q 0.00")
            monto_total = 0.0
            

        # --- BOTÓN DE REGISTRO ---
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 REGISTRAR INGRESO Y FACTURA", key="btn_registrar_ingreso", use_container_width=True):
            
            # 1. Validación de campos
            if not all([no_factura, proveedor, concepto]): 
                st.error("Por favor, complete los campos de No. Factura, Proveedor y Concepto.")
                return

            try:
                cantidad_int = int(cantidad)
                costo_float = float(costo_unitario)
                
                # 2. VALIDACIÓN DE FACTURA DUPLICADA
                if st.session_state.data_manager.verificar_factura_existente(no_factura):
                    st.error(f"¡Error! La Factura **{no_factura}** ya existe en el sistema.")
                    return
                
                # --- LÓGICA DE REGISTRO ---
                
                # 3. ACTUALIZAR INVENTARIO
                df_inventario = st.session_state.data_manager.leer_inventario()

                df_inventario['Concepto_Upper_Strip'] = df_inventario['Concepto'].astype(str).str.strip().str.upper()
                concepto_upper_strip = concepto.upper()
                idx_list = df_inventario.index[df_inventario['Concepto_Upper_Strip'] == concepto_upper_strip].tolist()
                
                
                if idx_list:
                    # Producto existe: actualizar stock, costo, lote y vencimiento
                    idx = idx_list[0]
                    stock_actual = pd.to_numeric(df_inventario.loc[idx, 'Stock'], errors='coerce').fillna(0)
                    df_inventario.loc[idx, 'Stock'] = stock_actual + cantidad_int
                    df_inventario.loc[idx, 'CostoUnitario'] = costo_float 
                    df_inventario.loc[idx, 'Lote'] = lote_usar 
                    df_inventario.loc[idx, 'FechaVencimiento'] = fecha_vencimiento.strftime('%Y-%m-%d') 
                    df_inventario.loc[idx, 'EsAntibiotico'] = es_antibiotico_ingreso # Actualiza el estado
                else:
                    # Nuevo producto
                    df_inventario['ID'] = pd.to_numeric(df_inventario['ID'], errors='coerce').fillna(0)
                    nuevo_id = df_inventario['ID'].max() + 1 if not df_inventario.empty else 1
                    
                    nuevo_producto = pd.DataFrame([{
                        'ID': nuevo_id,
                        'Concepto': concepto, 
                        'Categoria': categoria,
                        'Stock': cantidad_int,
                        'CostoUnitario': costo_float,
                        'PrecioVenta': costo_float * 1.30, 
                        'Lote': lote_usar, 
                        'FechaVencimiento': fecha_vencimiento.strftime('%Y-%m-%d'),
                        'EsAntibiotico': es_antibiotico_ingreso # NUEVO CAMPO
                    }])
                    df_inventario = pd.concat([df_inventario, nuevo_producto], ignore_index=True)

                if 'Concepto_Upper_Strip' in df_inventario.columns:
                    df_inventario = df_inventario.drop(columns=['Concepto_Upper_Strip'])

                st.session_state.data_manager.guardar_inventario(df_inventario)
                
                # 4. REGISTRAR FACTURA 
                df_facturas = st.session_state.data_manager.leer_facturas()
                nueva_factura = pd.DataFrame([{
                    'NoFactura': no_factura, 
                    'Proveedor': proveedor, 
                    'FechaEmision': datetime.now().strftime('%Y-%m-%d'), 
                    'FechaVencimientoPago': fecha_pago.strftime('%Y-%m-%d'), 
                    'MontoTotal': monto_total,
                    'Estado': 'PENDIENTE', 
                    'FechaPago': ''
                }])
                df_facturas = pd.concat([df_facturas, nueva_factura], ignore_index=True)
                st.session_state.data_manager.guardar_factura(df_facturas)
                
                # 5. Forzar la regeneración del lote
                st.session_state.lote_autogenerado = st.session_state.data_manager.generar_siguiente_lote()
                
                st.toast(f"✅ Producto '{concepto}' (Lote: {lote_usar}) y Factura '{no_factura}' registrados. Monto: Q {monto_total:.2f}", icon='✅', duration=5000)
                
                st.rerun() 

            except ValueError:
                 st.error("Error: Cantidad o Costo deben ser números válidos.")
            except Exception as e:
                st.error(f"Error desconocido al registrar: {e}") 

# ====================================================================
# PANTALLA 3: VALIDACIÓN DE FACTURAS 
# ====================================================================

def pantalla_validacion():
    st.subheader("✅ Validación de Facturas")
    st.markdown("---")
        
    filtro = st.radio(
        "Mostrar Facturas:",
        ('PENDIENTE', 'PAGADA'),
        key='filtro_facturas_radio',
        horizontal=True
    )
    
    facturas_a_pagar = []
    
    if filtro == 'PENDIENTE':
        
        df_filtrado_completo = st.session_state.data_manager.obtener_facturas_pendientes()
        
        if df_filtrado_completo.empty or 'NoFactura' not in df_filtrado_completo.columns:
            st.info("No hay facturas pendientes de pago.")
            return 
        
        else: 
            df_filtrado_completo['NoFactura'] = df_filtrado_completo['NoFactura'].astype(str)
            
            has_dias_restantes = 'DiasRestantes' in df_filtrado_completo.columns and not df_filtrado_completo['DiasRestantes'].isnull().all()
            
            if not has_dias_restantes:
                 st.warning("⚠️ Las facturas se cargaron, pero no se pudo calcular la columna 'Días Restantes'. Verifique el formato de las fechas en el Excel ('FechaVencimientoPago').")

            search_query = st.text_input("🔍 Buscar por No. Factura o Proveedor:", key='factura_search_query').strip().upper()
            
            if search_query:
                df_filtrado_completo = df_filtrado_completo[
                    df_filtrado_completo['NoFactura'].astype(str).str.contains(search_query) |
                    df_filtrado_completo['Proveedor'].astype(str).str.upper().str.contains(search_query)
                ]
                if df_filtrado_completo.empty:
                    st.info(f"No se encontraron facturas pendientes que coincidan con '{search_query}'.")
                    return 

            display_cols = ['NoFactura', 'Proveedor', 'FechaVencimientoPago', 'MontoTotal']
            if has_dias_restantes:
                display_cols.append('DiasRestantes')
            
            df_display = df_filtrado_completo[
                [col for col in display_cols if col in df_filtrado_completo.columns]
            ].copy()

            column_mapping = {
                'NoFactura': 'No. Factura', 
                'Proveedor': 'Proveedor', 
                'FechaVencimientoPago': 'Fecha Venc.', 
                'MontoTotal': 'Monto (Q)',
                'DiasRestantes': 'Días Restantes'
            }
            df_display.rename(columns={k: v for k, v in column_mapping.items() if k in df_display.columns}, inplace=True)
            
            df_display.insert(0, 'Seleccionar', False)
            
            column_config = {
                "Seleccionar": st.column_config.CheckboxColumn(
                    "Seleccionar para Pagar",
                    help="Marque la casilla para seleccionar la factura para pago.",
                    default=False,
                )
            }
            
            st.markdown("### Facturas Pendientes")
            
            # Usar st.data_editor
            if 'Días Restantes' in df_display.columns:
                def highlight_urgente(s):
                    is_numeric = s.apply(lambda x: np.issubdtype(type(x), np.number))
                    
                    def get_style(val):
                        if not np.issubdtype(type(val), np.number) or pd.isna(val) or val > 180:
                            return ''
                        if val <= 0:
                            return 'background-color: #E74C3C; color: white' # Vencido
                        if val <= 30:
                            return 'background-color: #F1C40F' # Urgente (30 días)
                        return ''
                        
                    return [get_style(val) for val in s]
                    

                edited_df = st.data_editor(
                    df_display.style.apply(highlight_urgente, subset=['Días Restantes']), 
                    use_container_width=True, 
                    hide_index=True,
                    column_config=column_config,
                    key="facturas_editor" 
                )
            else:
                 edited_df = st.data_editor(
                    df_display, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config=column_config,
                    key="facturas_editor" 
                )

            facturas_a_pagar = edited_df[edited_df['Seleccionar'] == True]['No. Factura'].astype(str).tolist()
        
        st.subheader("Marcar Factura(s) como Pagada(s)")
        
        if not facturas_a_pagar:
             st.info("Seleccione al menos una factura de la tabla para marcarla como Pagada.")
        
        if st.button(f"💵 MARCAR {len(facturas_a_pagar)} FACTURA(S) COMO PAGADA(S)", key="btn_marcar_pagada", use_container_width=True, disabled=(len(facturas_a_pagar) == 0)):
            
            # st.session_state.data_manager.obtener_facturas_pendientes.cache_clear() # CORRECCIÓN: Se debe limpiar el caché del cargador de facturas, no la función de obtención.
            
            df_facturas_original = st.session_state.data_manager.leer_facturas() 
            
            df_facturas_original['NoFactura'] = df_facturas_original['NoFactura'].astype(str)
            
            facturas_pagadas = []
            
            for factura_num_str in facturas_a_pagar:
                # Asegurarse de que el número de factura sea una cadena
                factura_num_str = str(factura_num_str).strip()
                
                idx = df_facturas_original.index[df_facturas_original['NoFactura'] == factura_num_str].tolist()
                
                if idx:
                    df_facturas_original.loc[idx[0], 'Estado'] = 'PAGADA'
                    df_facturas_original.loc[idx[0], 'FechaPago'] = datetime.now().strftime('%Y-%m-%d')
                    facturas_pagadas.append(factura_num_str) 

            st.session_state.data_manager.guardar_factura(df_facturas_original)
            
            if facturas_pagadas:
                # CORRECCIÓN: Nos aseguramos que 'facturas_pagadas' sea una lista de STR para el join.
                st.toast(f"✅ Facturas {', '.join(facturas_pagadas)} marcadas como PAGADAS.", icon='✅', duration=5000) 
            
            if 'facturas_editor' in st.session_state:
                del st.session_state['facturas_editor']
                
            st.rerun()
        

    else: # Facturas PAGADAS
        if 'facturas_editor' in st.session_state:
            del st.session_state['facturas_editor']

        df_facturas_raw = st.session_state.data_manager.leer_facturas()
        df_filtrado_pagadas = df_facturas_raw[df_facturas_raw['Estado'].astype(str).str.upper().str.strip() == 'PAGADA'].copy()

        if df_filtrado_pagadas.empty:
            st.info("No hay facturas marcadas como pagadas.")
            return

        df_display = df_filtrado_pagadas[['NoFactura', 'Proveedor', 'FechaEmision', 'FechaVencimientoPago', 'MontoTotal', 'FechaPago']]
        df_display.columns = ['No. Factura', 'Proveedor', 'Emisión', 'Vencimiento', 'Monto (Q)', 'Fecha Pago']
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)


# ====================================================================
# PANTALLA 4: PRODUCTOS A VENCER
# ====================================================================

def pantalla_vencer():
    st.subheader("🗓️ Productos a Vencer")
    
    df_vencimiento_alerta = st.session_state.data_manager.obtener_productos_a_vencer(meses=6) 
    
    if df_vencimiento_alerta.empty:
        st.success("¡No hay productos que venzan en los próximos 180 días!")
        return

    df_display = df_vencimiento_alerta[['Concepto', 'Lote', 'FechaVencimiento', 'Stock', 'DiasRestantes', 'EsAntibiotico']].copy()
    df_display['Antibiótico'] = df_display['EsAntibiotico'].apply(lambda x: 'SÍ' if x else 'NO')
    df_display = df_display.drop(columns=['EsAntibiotico'])
    
    df_display.columns = ['Concepto', 'Lote', 'Fecha Venc.', 'Stock', 'Días Restantes', 'Antibiótico']
    
    def highlight_alerta(s):
        return [
            ('background-color: #E74C3C; color: white' if v <= 30 else 
             'background-color: #F1C40F') 
            if pd.notna(v) and v > 0 and v <= 180 else '' for v in s
        ]
    
    st.dataframe(
        df_display.style.apply(highlight_alerta, subset=['Días Restantes']), 
        use_container_width=True, 
        hide_index=True
    )
    st.markdown(f"**Total de productos que vencerán en los próximos 180 días:** **{len(df_vencimiento_alerta)}**")

# ====================================================================
# PANTALLA 5: INVENTARIO / BÚSQUEDA 
# ====================================================================

def pantalla_inventario():
    st.subheader("🔍 Inventario y Búsqueda de Stock")
    st.markdown("---")
    
    df_inventario = st.session_state.data_manager.leer_inventario()
    
    if df_inventario.empty:
        st.info("El inventario está vacío.")
        return
        
    # --- FILTROS Y BÚSQUEDA ---
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_query = st.text_input("Buscar por Concepto, Categoría o Lote:", key='inventario_search_query').strip().upper()
    with col2:
        df_inventario['EsAntibiotico'] = df_inventario.get('EsAntibiotico', False) 
        filtro_antibiotico = st.selectbox(
            "Filtrar por Antibiótico:",
            ['Todos', 'Solo Antibióticos', 'Solo No Antibióticos'],
            key='inventario_filtro_antibiotico'
        )

    df_filtrado = df_inventario.copy()

    # Aplicar búsqueda
    if search_query:
        df_filtrado = df_filtrado[
            df_filtrado['Concepto'].astype(str).str.upper().str.contains(search_query) |
            df_filtrado['Categoria'].astype(str).str.upper().str.contains(search_query) |
            df_filtrado['Lote'].astype(str).str.upper().str.contains(search_query)
        ]

    # Aplicar filtro de antibiótico
    if filtro_antibiotico == 'Solo Antibióticos':
        df_filtrado = df_filtrado[df_filtrado['EsAntibiotico'] == True]
    elif filtro_antibiotico == 'Solo No Antibióticos':
        df_filtrado = df_filtrado[df_filtrado['EsAntibiotico'] == False]
        
    if df_filtrado.empty:
        st.info("No se encontraron productos con esos criterios de búsqueda/filtro.")
        return

    # Preparar el DataFrame para visualización
    df_display = df_filtrado[[
        'ID', 'Concepto', 'Categoria', 'Stock', 'PrecioVenta', 'Lote', 'FechaVencimiento', 'EsAntibiotico'
    ]].copy()
    
    # Renombrar columnas
    df_display.columns = [
        'ID', 'Concepto', 'Categoría', 'Stock', 'Precio Venta (Q)', 'Lote', 'Fecha Venc.', 'Antibiótico'
    ]
    
    df_display['Antibiótico'] = df_display['Antibiótico'].apply(lambda x: 'SÍ' if x else 'NO')
    
    st.markdown(f"**Total de productos encontrados:** **{len(df_filtrado)}**")
    
    # Función de formato condicional: Stock bajo
    def highlight_stock(s):
        return ['background-color: #F8D7DA' if v <= 10 else '' for v in s] 

    st.dataframe(
        df_display.style.apply(highlight_stock, subset=['Stock']), 
        use_container_width=True, 
        hide_index=True
    )

# ====================================================================
# FUNCIÓN PRINCIPAL DE NAVEGACIÓN (CON MENU LATERAL)
# ====================================================================

def main():
    
    # --- 0. CSS CLAVE: ELIMINAR ESPACIO SUPERIOR ---
    st.markdown("""
        <style>
            /* Elimina el margen superior por defecto de la aplicación */
            .main .block-container {
                padding-top: 1rem; /* Puedes ajustar este valor: 0.5rem o 0rem para menos espacio */
                padding-bottom: 0rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # --- 1. RELOJ EN ESQUINA ---
    st.markdown("""
        <style>
        .reloj-container {
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 5px 10px;
            background-color: #1A3E59; 
            color: white;
            border-radius: 8px;
            font-size: 1.2em;
            font-weight: bold;
            z-index: 1000; 
        }
        </style>
        <div class="reloj-container">
            <span id="live-time">Cargando...</span>
        </div>
        <script>
            function updateTime() {
                const now = new Date();
                const hours = now.getHours().toString().padStart(2, '0');
                const minutes = now.getMinutes().toString().padStart(2, '0');
                const seconds = now.getSeconds().toString().padStart(2, '0');
                document.getElementById('live-time').textContent = hours + ':' + minutes + ':' + seconds;
            }
            setInterval(updateTime, 1000); 
            updateTime(); 
        </script>
    """, unsafe_allow_html=True)
    
    # st.title("Sistema de Gestión: Farmacia Jerusalén 💊") # LÍNEA ELIMINADA A PETICIÓN DEL USUARIO

    with st.sidebar:
        st.markdown("---")
        st.markdown("#### Menú de Gestión")
        
        # Mantenemos el radio para la navegación con el menú lateral
        page = st.radio(
            "Seleccione una opción:",
            [
                "🛒 Venta y Facturación", 
                "📦 Ingreso de Mercadería", 
                "✅ Validación de Facturas", 
                "🗓️ Productos a Vencer", 
                "🔍 Inventario/Búsqueda"
            ],
            key='page_radio_menu'
        )
        
        st.session_state['page'] = page
        
        if 'facturas_editor' in st.session_state and st.session_state['page'] != "✅ Validación de Facturas":
             del st.session_state['facturas_editor']
        
        st.markdown("---")
        
        # --- 2. VERSÍCULO BÍBLICO DIARIO ---
        versiculo = get_daily_verse()
        st.markdown(f"""
            <div style="background-color: #FFFFFF; border: 1px solid #DCDCDC; border-radius: 5px; padding: 10px; font-size: 0.9em;">
                <p style="font-weight: bold; color: #4CAF50; margin-bottom: 5px;">📖 Versículo del Día</p>
                <p style="font-style: italic; margin: 0;">"{versiculo}"</p>
            </div>
        """, unsafe_allow_html=True)

    # Contenido de la página
    if st.session_state['page'] == "🛒 Venta y Facturación":
        pantalla_venta()
    elif st.session_state['page'] == "📦 Ingreso de Mercadería":
        pantalla_ingreso()
    elif st.session_state['page'] == "✅ Validación de Facturas":
        pantalla_validacion()
    elif st.session_state['page'] == "🗓️ Productos a Vencer":
        pantalla_vencer()
    elif st.session_state['page'] == "🔍 Inventario/Búsqueda": 
        pantalla_inventario()

if __name__ == '__main__':
    main()

