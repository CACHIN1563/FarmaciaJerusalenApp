import pandas as pd
from datetime import datetime, date, timedelta
from functools import lru_cache
import os 
import streamlit as st # Necesario si se usa st.error o st.cache_data, aunque aquí usamos lru_cache

class DataManager:
    def __init__(self):
        # Definición de las rutas de los archivos
        self.inventario_path = 'Inventario.xlsx'
        self.ventas_path = 'VentasDiarias.xlsx'
        self.facturas_path = 'FacturasCuentasPorPagar.xlsx'
        self.lote_path = 'Lote_Control.xlsx'
        self._inicializar_archivos()

    def _inicializar_archivos(self):
        """Crea los archivos Excel si no existen con las columnas predefinidas."""
        
        # 1. Inventario (COLUMNA NUEVA: EsAntibiotico)
        if not os.path.exists(self.inventario_path):
            df_inventario = pd.DataFrame(columns=[
                'ID', 'Concepto', 'Categoria', 'Stock', 'CostoUnitario', 
                'PrecioVenta', 'Lote', 'FechaVencimiento', 'EsAntibiotico'
            ])
            df_inventario.to_excel(self.inventario_path, index=False)
        
        # 2. Ventas Diarias (COLUMNA NUEVA: EsAntibiotico)
        if not os.path.exists(self.ventas_path):
            df_ventas = pd.DataFrame(columns=[
                'NoVenta', 'Fecha', 'Concepto', 'Cantidad', 'PrecioUnitario', 
                'TotalLinea', 'RecargoAplicado', 'MetodoPago', 'EsAntibiotico'
            ])
            df_ventas.to_excel(self.ventas_path, index=False)

        # 3. Facturas Cuentas por Pagar
        if not os.path.exists(self.facturas_path):
            df_facturas = pd.DataFrame(columns=[
                'NoFactura', 'Proveedor', 'FechaEmision', 'FechaVencimientoPago', 
                'MontoTotal', 'Estado', 'FechaPago'
            ])
            df_facturas.to_excel(self.facturas_path, index=False)
            
        # 4. Control de Lote (para el autogenerado)
        if not os.path.exists(self.lote_path):
            df_lote = pd.DataFrame({'UltimoLote': ['000000']})
            df_lote.to_excel(self.lote_path, index=False)

    # ====================================================================
    # --- MÉTODOS DE LECTURA (Caché con lru_cache) ---
    # ====================================================================

    @lru_cache(maxsize=1)
    def leer_inventario(self):
        try:
            # Asegurar que la nueva columna exista al leer
            df = pd.read_excel(self.inventario_path)
            if 'EsAntibiotico' not in df.columns:
                df['EsAntibiotico'] = False
            return df
        except FileNotFoundError:
            return pd.DataFrame(columns=['ID', 'Concepto', 'Categoria', 'Stock', 'CostoUnitario', 'PrecioVenta', 'Lote', 'FechaVencimiento', 'EsAntibiotico'])
        except Exception:
            return pd.DataFrame(columns=['ID', 'Concepto', 'Categoria', 'Stock', 'CostoUnitario', 'PrecioVenta', 'Lote', 'FechaVencimiento', 'EsAntibiotico'])


    @lru_cache(maxsize=1)
    def leer_ventas(self):
        try:
            # Asegurar que la nueva columna exista al leer
            df = pd.read_excel(self.ventas_path)
            if 'EsAntibiotico' not in df.columns:
                 df['EsAntibiotico'] = False
            return df
        except FileNotFoundError:
             return pd.DataFrame(columns=['NoVenta', 'Fecha', 'Concepto', 'Cantidad', 'PrecioUnitario', 'TotalLinea', 'RecargoAplicado', 'MetodoPago', 'EsAntibiotico'])
        except Exception:
            return pd.DataFrame(columns=['NoVenta', 'Fecha', 'Concepto', 'Cantidad', 'PrecioUnitario', 'TotalLinea', 'RecargoAplicado', 'MetodoPago', 'EsAntibiotico'])


    @lru_cache(maxsize=1)
    def leer_facturas(self):
        try:
            return pd.read_excel(self.facturas_path)
        except FileNotFoundError:
             return pd.DataFrame(columns=['NoFactura', 'Proveedor', 'FechaEmision', 'FechaVencimientoPago', 'MontoTotal', 'Estado', 'FechaPago'])
        except Exception:
            return pd.DataFrame(columns=['NoFactura', 'Proveedor', 'FechaEmision', 'FechaVencimientoPago', 'MontoTotal', 'Estado', 'FechaPago'])

    # ====================================================================
    # --- MÉTODOS DE ESCRITURA --- (Iguales, pero el inventario y venta ahora contienen la nueva columna)
    # ====================================================================

    def guardar_inventario(self, df):
        df.to_excel(self.inventario_path, index=False)
        self.leer_inventario.cache_clear()

    def guardar_venta(self, lista_venta, recargo_aplicado):
        self.leer_ventas.cache_clear() # Limpiar caché ANTES de leer para asegurar la última versión
        df_ventas = self.leer_ventas()
        
        no_venta = self.obtener_siguiente_no_venta()
        
        nuevas_ventas = []
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        
        for item in lista_venta:
            nuevas_ventas.append({
                'NoVenta': no_venta,
                'Fecha': fecha_hoy,
                'Concepto': item['concepto'],
                'Cantidad': item['cantidad'],
                'PrecioUnitario': item['precio_unitario'],
                'TotalLinea': item['total_linea'],
                'RecargoAplicado': item.get('recargo_aplicado_linea', 0.0), # Se usa el recargo específico de la línea (si aplica)
                'MetodoPago': item['metodo_pago'],
                'EsAntibiotico': item.get('es_antibiotico', False) # NUEVO CAMPO
            })
            
        df_nuevas_ventas = pd.DataFrame(nuevas_ventas)
        df_final = pd.concat([df_ventas, df_nuevas_ventas], ignore_index=True)
        df_final.to_excel(self.ventas_path, index=False)
        
        self.leer_ventas.cache_clear() # Limpiar caché DESPUÉS de escribir
        
        return no_venta


    def guardar_factura(self, df):
        df.to_excel(self.facturas_path, index=False)
        self.leer_facturas.cache_clear() # Limpiar caché para que la siguiente lectura sea la versión guardada

    # ====================================================================
    # --- MÉTODOS DE LÓGICA DE NEGOCIO ---
    # ====================================================================

    def obtener_siguiente_no_venta(self):
        """Calcula el siguiente número de venta disponible."""
        df = self.leer_ventas()
        if df.empty or 'NoVenta' not in df.columns:
            return 1000 
        
        # Convertir a numérico de forma segura y encontrar el máximo
        df['NoVenta'] = pd.to_numeric(df['NoVenta'], errors='coerce')
        max_no_venta = df['NoVenta'].max()
        
        return int(max_no_venta + 1) if pd.notna(max_no_venta) else 1000

    
    def generar_siguiente_lote(self):
        """Genera y actualiza el siguiente número de lote (Lote_Control.xlsx)."""
        
        try:
            df_lote = pd.read_excel(self.lote_path)
        except (FileNotFoundError, Exception):
            df_lote = pd.DataFrame({'UltimoLote': ['000000']})

        # Obtener el último lote y asegurar que es un string de 6 dígitos
        ultimo_lote_str = str(df_lote.iloc[0]['UltimoLote']).zfill(6)
        
        try:
            # Incrementar el número de lote
            ultimo_lote_int = int(ultimo_lote_str)
            siguiente_lote = ultimo_lote_int + 1
        except ValueError:
            # Si el lote no es numérico, reiniciar
            siguiente_lote = 1

        siguiente_lote_str = str(siguiente_lote).zfill(6)
        
        # Guardar el siguiente lote para la próxima vez
        df_lote.loc[0, 'UltimoLote'] = siguiente_lote_str
        df_lote.to_excel(self.lote_path, index=False)
        
        return siguiente_lote_str

    
    def actualizar_inventario_por_venta(self, lista_venta):
        """Actualiza el stock del inventario después de una venta."""
        self.leer_inventario.cache_clear() # Limpiar caché antes de manipular
        df_inventario = self.leer_inventario()
        
        for item in lista_venta:
            concepto_upper = str(item['concepto']).strip().upper()
            cantidad_vendida = int(item['cantidad'])
            
            # Buscar el producto ignorando mayúsculas/minúsculas y espacios
            df_inventario['Concepto_Upper_Strip'] = df_inventario['Concepto'].astype(str).str.strip().str.upper()
            
            idx_list = df_inventario.index[df_inventario['Concepto_Upper_Strip'] == concepto_upper].tolist()
            
            if idx_list:
                idx = idx_list[0]
                stock_actual = pd.to_numeric(df_inventario.loc[idx, 'Stock'], errors='coerce').fillna(0)
                
                nuevo_stock = stock_actual - cantidad_vendida
                df_inventario.loc[idx, 'Stock'] = nuevo_stock
                
                if nuevo_stock < 0:
                    # No detenemos la ejecución, solo avisamos
                    st.warning(f"Advertencia: Stock negativo para '{item['concepto']}'. Stock actual: {stock_actual}. Venta: {cantidad_vendida}")
            else:
                 st.warning(f"Producto '{item['concepto']}' vendido no encontrado en inventario. Stock no actualizado.")
                 
        if 'Concepto_Upper_Strip' in df_inventario.columns:
            df_inventario = df_inventario.drop(columns=['Concepto_Upper_Strip'])

        self.guardar_inventario(df_inventario)
        

    def verificar_factura_existente(self, no_factura):
        """Verifica si un número de factura ya existe en el archivo."""
        # CRÍTICO: Limpiar el caché antes de leer
        self.leer_facturas.cache_clear() 
        
        df_facturas = self.leer_facturas()
        
        if df_facturas.empty:
            return False
        
        # Convertir a string para una comparación robusta
        existe = (df_facturas['NoFactura'].astype(str).str.strip().str.upper() == str(no_factura).strip().upper()).any()
        return existe

    def obtener_facturas_pendientes(self):
        """Retorna las facturas con estado 'PENDIENTE' y calcula días restantes."""
        self.leer_facturas.cache_clear()
        df_facturas = self.leer_facturas()
        
        # Aseguramos que la columna 'Estado' se maneje como string sin espacios
        df_filtrado = df_facturas[df_facturas['Estado'].astype(str).str.upper().str.strip() == 'PENDIENTE'].copy()
        
        if df_filtrado.empty:
            return pd.DataFrame()
        
        try:
            # Intentamos convertir la columna de fecha a datetime
            df_filtrado['FechaVencimientoPago'] = pd.to_datetime(df_filtrado['FechaVencimientoPago'], errors='coerce')
            
            # Eliminamos filas donde la conversión de fecha falló (NaT)
            df_filtrado = df_filtrado.dropna(subset=['FechaVencimientoPago'])
            
            if df_filtrado.empty:
                 # Si todas las fechas eran inválidas, retornamos el DF filtrado inicial sin las fechas inválidas
                 return df_facturas[df_facturas['Estado'].astype(str).str.upper().str.strip() == 'PENDIENTE']
            
            hoy = datetime.now().date()
            
            # Calcular los días restantes
            df_filtrado['DiasRestantes'] = (df_filtrado['FechaVencimientoPago'].dt.date - hoy).apply(lambda x: x.days if pd.notna(x) else None)
            
            # Ordenar: primero las que tienen menos días restantes (más urgentes)
            df_filtrado = df_filtrado.sort_values(by='DiasRestantes', ascending=True)
            
            return df_filtrado
            
        except Exception:
            # Si hay un error general en el cálculo, retornamos el DataFrame filtrado SIN la columna 'DiasRestantes'
            return df_facturas[df_facturas['Estado'].astype(str).str.upper().str.strip() == 'PENDIENTE']

    
    def obtener_productos_a_vencer(self, meses=6):
        """Retorna productos cuya fecha de vencimiento es en los próximos 'meses'."""
        df_inventario = self.leer_inventario()
        
        if df_inventario.empty:
            return pd.DataFrame()
            
        try:
            # 1. Asegurar formato de fecha
            df_inventario['FechaVencimiento'] = pd.to_datetime(df_inventario['FechaVencimiento'], errors='coerce')
            
            # Eliminar filas con fechas inválidas antes del cálculo
            df_inventario = df_inventario.dropna(subset=['FechaVencimiento'])
            
            fecha_limite = datetime.now().date() + timedelta(days=30 * meses)
            hoy = datetime.now().date()
            
            # 2. Filtrar por vencimiento
            df_vencer = df_inventario[
                (df_inventario['FechaVencimiento'].dt.date >= hoy) & 
                (df_inventario['FechaVencimiento'].dt.date <= fecha_limite)
            ].copy()
            
            if df_vencer.empty:
                return pd.DataFrame()
            
            # 3. Calcular días restantes
            df_vencer['DiasRestantes'] = (df_vencer['FechaVencimiento'].dt.date - hoy).apply(lambda x: x.days if pd.notna(x) else None)
            
            # 4. Ordenar por urgencia
            df_vencer = df_vencer.sort_values(by='DiasRestantes', ascending=True)
            
            return df_vencer
            
        except Exception as e:
            # Si hay error en la manipulación de fechas, retorna vacío.
            st.error(f"Error en el cálculo de productos a vencer. Revise el formato de FechaVencimiento en Inventario.xlsx. Error: {e}")
            return pd.DataFrame()