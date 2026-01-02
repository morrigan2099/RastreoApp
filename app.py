import streamlit as st
import pandas as pd
from pyairtable import Api
import gspread
import folium
from streamlit_folium import st_folium

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor de Reparto", layout="wide")

# --- CONEXIÓN A SERVICIOS (SECRETS) ---
# Intentamos conectar, si falla mostramos aviso amigable
try:
    # 1. Airtable
    api = Api(st.secrets["AIRTABLE_KEY"])
    table = api.table(st.secrets["BASE_ID"], st.secrets["TABLE_NAME"])
    
    # 2. Google Sheets
    gc = gspread.service_account_from_dict(st.secrets["GCP_CREDENTIALS"])
    EMAIL_ADMIN = st.secrets["ADMIN_EMAIL"] # Tu correo para compartir el sheet
    
except Exception as e:
    st.error(f"Error de conexión: {e}. Revisa tus secrets.")
    st.stop()

# --- INTERFAZ PRINCIPAL ---
st.title("🚚 Monitor de Reparto & Archivo")

tab1, tab2 = st.tabs(["📍 Mapa en Vivo", "🗄️ Cierre y Archivo"])

# ==========================================
# PESTAÑA 1: MAPA EN VIVO (AIRTABLE)
# ==========================================
with tab1:
    if st.button("🔄 Actualizar Ubicaciones"):
        st.rerun()

    # Traer datos
    records = table.all()
    
    if records:
        # Limpieza de datos
        data = [r['fields'] for r in records]
        df = pd.DataFrame(data)
        
        # Validación básica
        required_cols = ['Latitud', 'Longitud', 'Usuario', 'Hora']
        if all(col in df.columns for col in required_cols):
            
            # Convertir a números
            df['Latitud'] = df['Latitud'].astype(float)
            df['Longitud'] = df['Longitud'].astype(float)
            
            st.metric("Puntos rastreados hoy", len(df))
            
            # Mapa simple
            st.map(df, latitude='Latitud', longitude='Longitud', size=20, color='#0000FF')
            
            # Tabla de datos recientes
            st.dataframe(df.sort_values(by='Hora', ascending=False).head(10))
            
        else:
            st.warning("Airtable tiene datos, pero faltan columnas (Latitud, Longitud, Usuario).")
    else:
        st.info("Esperando inicio de ruta... (Airtable vacío)")


# ==========================================
# PESTAÑA 2: CIERRE DEL DÍA (GOOGLE SHEETS)
# ==========================================
with tab2:
    st.header("Generar Libro del Día")
    st.markdown("""
    Este proceso:
    1. Crea un libro de Excel en Google Drive con la fecha de hoy.
    2. Crea una pestaña por cada repartidor.
    3. Mueve los datos y **limpia Airtable**.
    """)
    
    if st.button("🏁 CERRAR DÍA Y ARCHIVAR", type="primary"):
        records = table.all()
        
        if not records:
            st.error("No hay datos para archivar.")
        else:
            status = st.status("Iniciando proceso de archivado...", expanded=True)
            
            # Preparar datos
            data = [r['fields'] for r in records]
            df = pd.DataFrame(data)
            
            if 'Fecha' in df.columns and 'Usuario' in df.columns:
                fecha_reparto = df['Fecha'].iloc[0]
                nombre_libro = f"Reparto_{fecha_reparto}"
                
                # 1. Crear/Abrir Libro
                try:
                    sh = gc.open(nombre_libro)
                    status.write(f"📂 Abriendo libro existente: {nombre_libro}")
                except gspread.exceptions.SpreadsheetNotFound:
                    sh = gc.create(nombre_libro)
                    sh.share(EMAIL_ADMIN, perm_type='user', role='writer')
                    status.write(f"✨ Libro CREADO y compartido: {nombre_libro}")
                
                # 2. Procesar Usuarios
                usuarios = df['Usuario'].unique()
                for usuario in usuarios:
                    status.write(f"👤 Archivando ruta de: {usuario}...")
                    df_user = df[df['Usuario'] == usuario]
                    
                    # Seleccionar columnas ordenadas
                    cols_to_save = ['Hora', 'Latitud', 'Longitud', 'Zona']
                    # Asegurarse que existan, si no, rellenar con vacío
                    for c in cols_to_save:
                        if c not in df_user.columns: df_user[c] = ""
                    
                    datos_listos = df_user[cols_to_save].values.tolist()
                    
                    try:
                        ws = sh.add_worksheet(title=usuario, rows=1000, cols=10)
                        ws.append_row(cols_to_save)
                    except:
                        ws = sh.worksheet(usuario)
                    
                    ws.append_rows(datos_listos)
                
                # 3. Limpiar Airtable
                status.write("🗑️ Limpiando Airtable...")
                ids = [r['id'] for r in records]
                table.batch_delete(ids)
                
                status.update(label="¡Proceso Terminado!", state="complete")
                st.success(f"Archivo guardado. Link: {sh.url}")
                st.balloons()
                
            else:
                status.update(label="Error", state="error")
                st.error("Faltan columnas 'Fecha' o 'Usuario' en los datos.")