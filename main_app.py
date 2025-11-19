import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
# Importa tus clases de gestión de datos
from data_manager import DataManager 
from pdf_generator import PDFGenerator 
import io 

# --- CONSTANTE DE RECARGO ---
RECARGO_TARJETA = 0.005  # 0.5% de recargo

# ====================================================================
# CONFIGURACIÓN E INICIALIZACIÓN DEL ESTADO DE STREAMLIT
# ====================================================================

# Configuración inicial de la página
st.set_page_config(
    page_title="Farmacia Jerusalén | Gestión Web", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar DataManager y PDFGenerator en el estado de la sesión
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()
    
if 'pdf_generator' not in st.session_state:
    st.session_state.pdf_generator = PDFGenerator() # Lo mantengo para reutilizar la lógica de reportes

# Inicializar el estado de la venta actual
if 'venta_actual' not in st.session_state:
    st.session_state.venta_actual = []

# Inicializar el No. de Venta
try:
    if 'no_venta' not in st.session_state:
        st.session_state.no_venta = st.session_state.data_manager.obtener_siguiente_no_venta()
except Exception:
    st.session_state.no_venta = 1000 # Fallback 

# ====================================================================
# FUNCIONES DE AYUDA Y CÁLCULO
# ====================================================================

def _actualizar_total_venta():
    """Calcula y devuelve el total de la venta actual, aplicando recargo."""
    subtotal = sum(item['total_linea'] for item in st.session_state.venta_actual)
    
    # Usar el estado de la sesión para el método de pago
    metodo_pago = st.session_state.get('metodo_pago_radio', 'Efectivo') 
    recargo = 0.0
    
    if metodo_pago == 'Tarjeta':
        recargo = subtotal * RECARGO_TARJETA
        
    total = subtotal + recargo
    
    return subtotal, recargo, total

# ====================================================================
# PANTALLA 1: VENTA Y FACTURACIÓN (MIGRADA)
# ====================================================================

def pantalla_venta():
    st.header(f"🛒 Venta y Facturación | No. {st.session_state.no_venta}")
    st.markdown("---")
    
    # ----------------------- INPUTS DE PRODUCTO -----------------------
    col1, col2, col3, col4 = st.columns([3, 1, 1.5, 2])
    
    with col1:
        concepto = st.text_input("Concepto:", key="venta_concepto")
    with col2:
        cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1, key="venta_cantidad")
    with col3:
        precio_unitario = st.number_input("Precio Unitario (Q):", min_value=0.01, value=10.00, step=0.50, key="venta_precio")
    with col4:
        categoria = st.selectbox("Categoría:", ['Farmacia', 'Tienda', 'Inyecciones'], key="venta_categoria")
        
    # --- MÉTODO DE PAGO Y BOTONES DE ACCIÓN ---
    col_pago, col_add, col_reset = st.columns([1.5, 1, 1.5])
    
    with col_pago:
        # El valor por defecto de Radio es asignado a la clave 'metodo_pago_radio'
        st.radio(
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
                st.session_state.venta_actual.append({
                    'concepto': concepto, 
                    'cantidad': cantidad, 
                    'precio_unitario': precio_unitario, 
                    'total_linea': total_linea,
                    'categoria': categoria,
                })
                st.toast(f"Producto '{concepto}' agregado.", icon='✅')

    with col_reset:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ CANCELAR/LIMPIAR VENTA", key="btn_reset_venta", use_container_width=True):
            st.session_state.venta_actual = []
            st.session_state.no_venta = st.session_state.data_manager.obtener_siguiente_no_venta()
            st.toast("Venta cancelada y limpiada.", icon='🗑️')
            st.experimental_rerun() # Refresca para limpiar inputs si es necesario

    st.markdown("---")
    
    # ----------------------- TABLA Y TOTALES -----------------------
    st.subheader("Artículos en Venta")
    if st.session_state.venta_actual:
        df_venta = pd.DataFrame(st.session_state.venta_actual)
        df_display = df_venta[['cantidad', 'concepto', 'precio_unitario', 'total_linea']].copy()
        df_display.columns = ['Cant', 'Concepto del Producto', 'Precio Unitario (Q)', 'Total Línea (Q)']
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("La venta actual está vacía.")
    
    subtotal, recargo, total_final = _actualizar_total_venta()
    
    st.markdown("---")
    
    col_total, col_finish, col_reporte = st.columns([2.5, 1, 1.5])
    
    with col_total:
        st.markdown(f"**SUBTOTAL:** Q **{subtotal:.2f}**")
        if recargo > 0:
            st.markdown(f"**RECARGO (0.5%):** Q **{recargo:.2f}** *(Tarjeta)*")
        st.success(f"## TOTAL A PAGAR: Q {total_final:.2f}")

    with col_finish:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ FINALIZAR VENTA", key="btn_finalizar", use_container_width=True):
            if not st.session_state.venta_actual:
                st.warning("No hay productos para finalizar la venta.")
                return
            
            # 1. Guardar la venta
            no_venta = st.session_state.data_manager.guardar_venta(st.session_state.venta_actual, recargo_aplicado=recargo)
            
            # 2. Actualizar inventario (Llamada asumida a función)
            st.session_state.data_manager.actualizar_inventario_por_venta(st.session_state.venta_actual) 

            st.success(f"Venta No. {no_venta} registrada. Total Final: Q {total_final:.2f}")
            
            # 3. Resetear el estado
            st.session_state.venta_actual = []
            st.session_state.no_venta = st.session_state.data_manager.obtener_siguiente_no_venta()
            st.experimental_rerun() # Recarga la página para mostrar nuevo NoVenta

    with col_reporte:
        st.markdown("<br>", unsafe_allow_html=True)
        # 4. Generación de Reporte PDF (Adaptada a Streamlit)
        try:
            df_ventas = st.session_state.data_manager.leer_ventas()
            hoy = datetime.now().strftime('%Y-%m-%d')
            ventas_hoy = df_ventas[df_ventas['Fecha'].astype(str) == hoy] 
            
            if not ventas_hoy.empty:
                # Usar la función de PDFGenerator para crear el contenido binario
                pdf_data = st.session_state.pdf_generator.generar_reporte_diario_binario(ventas_hoy) 
                
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
            st.error(f"Error al preparar PDF: {e}")

# ====================================================================
# PANTALLA 2: INGRESO DE MERCADERÍA (MIGRADA)
# ====================================================================

def pantalla_ingreso():
    st.header("📦 Ingreso de Mercadería")
    
    with st.expander("Registro de Nuevos Productos y Facturas", expanded=True):
        
        # --- DATOS DE LA FACTURA ---
        st.subheader("Datos de la Factura de Compra")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            no_factura = st.text_input("No. Factura:", key="ingreso_no_factura")
        with col_f2:
            proveedor = st.text_input("Proveedor:", key="ingreso_proveedor")
        with col_f3:
            # Reemplaza DateEntry de Tkinter con st.date_input
            fecha_pago = st.date_input("Fecha Venc. Pago:", datetime.now().date() + timedelta(days=30), key="ingreso_fecha_pago")

        st.markdown("---")
        
        # --- DATOS DEL PRODUCTO ---
        st.subheader("Datos del Producto Ingresado")
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        
        with col_p1:
            concepto = st.text_input("Concepto/Nombre:", key="ingreso_concepto")
        with col_p2:
            cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1, key="ingreso_cantidad")
        with col_p3:
            costo_unitario = st.number_input("Costo Unitario (Q):", min_value=0.01, value=5.00, step=0.10, key="ingreso_costo")
        with col_p4:
            categoria = st.selectbox("Categoría:", ['Farmacia', 'Tienda'], key="ingreso_categoria")
        
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            lote = st.text_input("Lote:", key="ingreso_lote")
        with col_l2:
            fecha_vencimiento = st.date_input("Fecha Venc. Producto:", datetime.now().date() + timedelta(days=365), key="ingreso_fecha_vencimiento")

        # --- BOTÓN DE REGISTRO ---
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 REGISTRAR INGRESO Y FACTURA", key="btn_registrar_ingreso", use_container_width=True):
            
            # Validación de datos
            if not all([no_factura, proveedor, concepto, lote]):
                st.error("Por favor, complete todos los campos de texto.")
                return

            try:
                cantidad_int = int(cantidad)
                costo_float = float(costo_unitario)
                monto_total = cantidad_int * costo_float 
                
                # --- LÓGICA DE REGISTRO ---
                
                # 1. ACTUALIZAR INVENTARIO
                df_inventario = st.session_state.data_manager.leer_inventario()
                concepto_lower = concepto.strip().lower()

                if concepto_lower in df_inventario['Concepto'].str.lower().values:
                    # Producto existe: actualizar stock
                    idx = df_inventario.index[df_inventario['Concepto'].str.lower() == concepto_lower].tolist()[0]
                    df_inventario.loc[idx, 'Stock'] += cantidad_int
                    df_inventario.loc[idx, 'CostoUnitario'] = costo_float 
                    df_inventario.loc[idx, 'Lote'] = lote # Actualizar lote
                    df_inventario.loc[idx, 'FechaVencimiento'] = fecha_vencimiento.strftime('%Y-%m-%d') # Actualizar fecha
                else:
                    # Nuevo producto
                    nuevo_id = df_inventario['ID'].max() + 1 if not df_inventario.empty else 1
                    nuevo_producto = pd.DataFrame([{
                        'ID': nuevo_id,
                        'Concepto': concepto.strip(),
                        'Categoria': categoria,
                        'Stock': cantidad_int,
                        'CostoUnitario': costo_float,
                        'PrecioVenta': costo_float * 1.30, 
                        'Lote': lote,
                        'FechaVencimiento': fecha_vencimiento.strftime('%Y-%m-%d')
                    }])
                    df_inventario = pd.concat([df_inventario, nuevo_producto], ignore_index=True)

                st.session_state.data_manager.guardar_inventario(df_inventario)
                
                # 2. REGISTRAR FACTURA
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

                st.success(f"✅ Producto '{concepto}' y Factura '{no_factura}' registrados. Monto: Q {monto_total:.2f}")
                # Recargar la página para limpiar los campos de entrada
                st.experimental_rerun() 

            except ValueError:
                 st.error("Error: Cantidad o Costo deben ser números válidos.")
            except Exception as e:
                st.error(f"Error desconocido al registrar: {e}")

# ====================================================================
# PANTALLA 3: VALIDACIÓN DE FACTURAS (MIGRADA - Parcial)
# ====================================================================

def pantalla_validacion():
    st.header("✅ Validación de Facturas")
    st.markdown("---")
    
    # --- FILTRO ---
    filtro = st.radio(
        "Mostrar Facturas:",
        ('PENDIENTE', 'PAGADA'),
        key='filtro_facturas_radio',
        horizontal=True
    )
    
    df_facturas = st.session_state.data_manager.leer_facturas()
    
    if df_facturas.empty:
        st.info("No hay facturas registradas.")
        return

    # Aplicar filtro
    df_filtrado = df_facturas[df_facturas['Estado'] == filtro].copy()
    
    if filtro == 'PENDIENTE':
        # Replicar la lógica de obtener_facturas_pendientes
        df_filtrado['FechaVencimientoPago'] = pd.to_datetime(df_filtrado['FechaVencimientoPago'])
        df_filtrado['DiasRestantes'] = (df_filtrado['FechaVencimientoPago'].dt.date - datetime.now().date()).dt.days
        df_display = df_filtrado[['NoFactura', 'Proveedor', 'FechaVencimientoPago', 'MontoTotal', 'DiasRestantes']].sort_values(by='DiasRestantes')
        df_display.columns = ['No. Factura', 'Proveedor', 'Fecha Venc.', 'Monto (Q)', 'Días Restantes']
        
        # Aplicar formato condicional (solo visualmente en Streamlit)
        def highlight_urgente(s):
            return ['background-color: #F1C40F' if v < 30 else '' for v in s]
        
        st.dataframe(df_display.style.apply(highlight_urgente, subset=['Días Restantes']), use_container_width=True, hide_index=True)
        
        # --- MARCAR COMO PAGADA ---
        st.subheader("Marcar Factura como Pagada")
        col_pago_factura, col_btn_pago = st.columns([2, 1])
        
        with col_pago_factura:
            factura_seleccionada = st.selectbox(
                "Seleccione la Factura a Pagar:", 
                df_filtrado['NoFactura'].tolist(), 
                key='factura_a_pagar_select'
            )
            
        with col_btn_pago:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💵 MARCAR COMO PAGADA", key="btn_marcar_pagada", use_container_width=True, disabled=df_filtrado.empty):
                idx = df_facturas.index[df_facturas['NoFactura'] == factura_seleccionada].tolist()
                if idx:
                    df_facturas.loc[idx[0], 'Estado'] = 'PAGADA'
                    df_facturas.loc[idx[0], 'FechaPago'] = datetime.now().strftime('%Y-%m-%d')
                    st.session_state.data_manager.guardar_factura(df_facturas)
                    st.success(f"Factura {factura_seleccionada} marcada como PAGADA.")
                    st.experimental_rerun()
                else:
                    st.error("Error al encontrar la factura para pagar.")
    
    else: # Facturas PAGADAS
        df_display = df_filtrado[['NoFactura', 'Proveedor', 'FechaEmision', 'FechaVencimientoPago', 'MontoTotal', 'FechaPago']]
        df_display.columns = ['No. Factura', 'Proveedor', 'Emisión', 'Vencimiento', 'Monto (Q)', 'Fecha Pago']
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)


# ====================================================================
# PANTALLA 4: PRODUCTOS A VENCER (MIGRADA - Parcial)
# ====================================================================

def pantalla_vencer():
    st.header("🗓️ Productos a Vencer")
    
    df_inventario = st.session_state.data_manager.leer_inventario()
    
    if df_inventario.empty:
        st.info("No hay inventario registrado.")
        return
        
    # Replicar la lógica de obtener_productos_a_vencer
    df_inventario['FechaVencimiento'] = pd.to_datetime(df_inventario['FechaVencimiento'], errors='coerce')
    df_inventario.dropna(subset=['FechaVencimiento'], inplace=True)

    hoy = datetime.now().date()
    df_inventario['DiasRestantes'] = (df_inventario['FechaVencimiento'].dt.date - hoy).dt.days
    
    # Filtrar solo productos con fecha de vencimiento en el futuro o muy cerca
    df_vencimiento = df_inventario[df_inventario['DiasRestantes'] >= 0].sort_values(by='DiasRestantes')
    
    # Filtrar solo productos que vencen en los próximos 180 días (6 meses)
    df_vencimiento_alerta = df_vencimiento[df_vencimiento['DiasRestantes'] <= 180].copy()
    
    if df_vencimiento_alerta.empty:
        st.success("¡No hay productos que venzan en los próximos 6 meses!")
        return

    df_display = df_vencimiento_alerta[['Concepto', 'Lote', 'FechaVencimiento', 'Stock', 'DiasRestantes']]
    df_display.columns = ['Concepto', 'Lote', 'Fecha Venc.', 'Stock', 'Días Restantes']
    
    # Aplicar formato condicional (Alerta si vence en menos de 90 días)
    def highlight_alerta(s):
        return ['background-color: #F1C40F' if v < 90 else '' for v in s]
    
    st.dataframe(
        df_display.style.apply(highlight_alerta, subset=['Días Restantes']), 
        use_container_width=True, 
        hide_index=True
    )
    st.markdown(f"**Total de productos que vencerán en los próximos 180 días:** {len(df_vencimiento_alerta)}")


# ====================================================================
# FUNCIÓN PRINCIPAL DE NAVEGACIÓN
# ====================================================================

def main():
    
    st.sidebar.title("📜 Farmacia Jerusalén")
    st.sidebar.markdown("---")
    
    # Menú de navegación en el sidebar
    page = st.sidebar.radio(
        "Menú de Gestión",
        ("🛒 Venta y Facturación", "📦 Ingreso de Mercadería", "✅ Validación de Facturas", "🗓️ Productos a Vencer")
    )
    
    st.title(f"Sistema de Gestión: {page}")

    if page == "🛒 Venta y Facturación":
        pantalla_venta()
    elif page == "📦 Ingreso de Mercadería":
        pantalla_ingreso()
    elif page == "✅ Validación de Facturas":
        pantalla_validacion()
    elif page == "🗓️ Productos a Vencer":
        pantalla_vencer()

if __name__ == '__main__':
    main()