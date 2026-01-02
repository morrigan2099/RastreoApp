import streamlit as st
import pandas as pd
from pyairtable import Api
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader
import folium
from streamlit_folium import st_folium

# ==========================================
# 🔐 ZONA DE CONFIGURACIÓN (TUS DATOS AQUÍ)
# ==========================================

# 1. AIRTABLE
AIRTABLE_API_KEY = "patyclv7hDjtGHB0F.19829008c5dee053cba18720d38c62ed86fa76ff0c87ad1f2d71bfe853ce9783"  # Pega tu token que empieza con pat...
AIRTABLE_BASE_ID = "appglio1RmA0AoWTP"  # El ID de la base (está en la URL: appXXXXXX)
AIRTABLE_TABLE_NAME = "Rutas_Vivo"

# 2. CLOUDINARY (Pega los datos que me diste antes)
CLOUDINARY_CLOUD_NAME = "dlj0pdv6i" 
CLOUDINARY_API_KEY = "847419449273122" 
CLOUDINARY_API_SECRET = "TU_SECRET_AQUI" # <--- Pega aquí el secret que borraste

# 3. GOOGLE SHEETS (Credenciales JSON completas)
# Borra las llaves vacías {} de abajo y pega TODO el contenido de tu archivo .json
GOOGLE_JSON_DATA = {
    "type": "service_account",
    "project_id": "tu-project-id",
    "private_key_id": "...",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
    "client_email": "tu-cuenta@tu-proyecto.iam.gserviceaccount.com",
    "client_id": "...",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "..."
}

# 4. ADMIN
EMAIL_ADMIN = "tucorreo@gmail.com" # Para que el sistema te comparta el Excel

# ==========================================
# FIN DE CONFIGURACIÓN
# ==========================================

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor de Reparto Pro", layout="wide")

# --- CONEXIÓN A SERVICIOS ---
try:
    # Conexión Airtable
    api = Api(AIRTABLE_API_KEY)
    table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
    
    # Conexión Google Sheets (Usando el diccionario directo)
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(GOOGLE_JSON_DATA, scopes=scopes)
    gc = gspread.authorize(creds)
    
    # Conexión Cloudinary
    cloudinary.config( 
        cloud_name = CLOUDINARY_CLOUD_NAME, 
        api_key = CLOUDINARY_API_KEY, 
        api_secret = CLOUDINARY_API_SECRET,
        secure = True
    )
except Exception as e:
    st.error(f"Error de conexión con las credenciales: {e}")
    st.stop()

st.title("🚚 Monitor de Reparto & Cloudinary")

tab1, tab2 = st.tabs(["📍 En Vivo", "☁️ Procesar y Archivar"])

# ==========================================
# PESTAÑA 1: MAPA + GALERÍA
# ==========================================
with tab1:
    col_kpi, col_btn = st.columns([4,1])
    with col_btn:
        if st.button("🔄 Refrescar"):
            st.rerun()

    # Intentar leer Airtable
    try:
        records = table.all()
    except Exception as e:
        st.error(f"Error leyendo Airtable: {e}")
        records = []

    if records:
        data = [r['fields'] for r in records]
        df = pd.DataFrame(data)
        
        # Separar lógica (GPS vs FOTOS)
        # Validamos que exista la columna 'Tipo', si no, asumimos que todo es GPS
        if 'Tipo' not in df.columns:
            df['Tipo'] = 'GPS'

        df_gps = df[df['Tipo'] != 'FOTO']
        df_fotos = df[df['Tipo'] == 'FOTO']
        
        st.metric("📦 Paquetes/Evidencias hoy", len(df_fotos))
        
        # Visualización de Mapa (Simple usando st.map para rapidez)
        # Asegurar que Lat/Lon sean floats
        if not df_gps.empty and 'Latitud' in df_gps.columns:
            df_gps['Latitud'] = df_gps['Latitud'].astype(float)
            df_gps['Longitud'] = df_gps['Longitud'].astype(float)
            st.map(df_gps, latitude='Latitud', longitude='Longitud')

        # Galería simple
        if not df_fotos.empty:
            st.subheader("Últimas Evidencias")
            cols = st.columns(4)
            # Mostramos las últimas fotos
            for i, (idx, row) in enumerate(df_fotos.tail(8).iterrows()):
                col = cols[i % 4]
                if 'Foto' in row and isinstance(row['Foto'], list):
                    # Airtable devuelve lista de dicts
                    url_img = row['Foto'][0]['url']
                    caption = f"{row.get('Usuario', '')} - {row.get('Etiqueta_Foto', '')}"
                    col.image(url_img, caption=caption)

# ==========================================
# PESTAÑA 2: EL MOTOR DE MIGRACIÓN
# ==========================================
with tab2:
    st.header("🗃️ Cierre del Día: Migración a Cloudinary")
    st.info("Este proceso sube las fotos a la nube permanente y limpia Airtable.")
    
    if st.button("🚀 INICIAR PROCESAMIENTO Y ARCHIVADO", type="primary"):
        records = table.all()
        
        if not records:
            st.warning("No hay datos en Airtable.")
        else:
            bar = st.progress(0)
            status = st.status("Iniciando motor...", expanded=True)
            
            # Preparar datos
            data = [r['fields'] for r in records]
            df = pd.DataFrame(data)
            fecha = df['Fecha'].iloc[0] if 'Fecha' in df.columns else "General"
            nombre_libro = f"Reparto_{fecha}"
            
            # 1. Crear/Abrir Google Sheet
            try:
                sh = gc.open(nombre_libro)
                status.write(f"📂 Libro encontrado: {nombre_libro}")
            except gspread.exceptions.SpreadsheetNotFound:
                sh = gc.create(nombre_libro)
                sh.share(EMAIL_ADMIN, perm_type='user', role='writer')
                status.write(f"✨ Libro CREADO: {nombre_libro}")
            
            # 2. Procesar Usuarios
            if 'Usuario' in df.columns:
                usuarios = df['Usuario'].unique()
            else:
                usuarios = ["Desconocido"]

            total_pasos = len(records)
            pasos_completados = 0

            for usuario in usuarios:
                status.write(f"🔄 Procesando: **{usuario}**")
                
                if 'Usuario' in df.columns:
                    df_u = df[df['Usuario'] == usuario].copy()
                else:
                    df_u = df.copy()
                
                # FUNCIÓN DE SUBIDA A CLOUDINARY
                def procesar_imagen_cloudinary(row):
                    if row.get('Tipo') != 'FOTO' or 'Foto' not in row or not isinstance(row['Foto'], list):
                        return ""
                    try:
                        airtable_url = row['Foto'][0]['url']
                        nombre_archivo = f"{fecha}_{usuario}_{row.get('Hora','').replace(':','')}"
                        
                        # Subir a Cloudinary
                        res = cloudinary.uploader.upload(
                            airtable_url, 
                            public_id=nombre_archivo,
                            folder="repartos_evidencia",
                            format="webp"
                        )
                        return res['secure_url']
                    except Exception as e:
                        return f"Error: {e}"

                # Ejecutar subida (esto tarda un poco)
                df_u['Foto_Link_Cloudinary'] = df_u.apply(procesar_imagen_cloudinary, axis=1)
                
                # Columnas finales
                cols = ['Hora', 'Tipo', 'Etiqueta_Foto', 'Latitud', 'Longitud', 'Zona', 'Foto_Link_Cloudinary']
                # Rellenar faltantes
                for c in cols:
                    if c not in df_u.columns: df_u[c] = ""
                
                datos_finales = df_u[cols].values.tolist()
                
                # Escribir en hoja del usuario
                try:
                    ws = sh.add_worksheet(title=str(usuario), rows=1000, cols=10)
                    ws.append_row(cols)
                except:
                    ws = sh.worksheet(str(usuario))
                
                ws.append_rows(datos_finales)
                
                pasos_completados += len(df_u)
                bar.progress(min(pasos_completados / total_pasos, 1.0))

            # 3. Borrar Airtable
            status.write("🗑️ Limpiando Airtable...")
            ids = [r['id'] for r in records]
            table.batch_delete(ids)
            
            status.update(label="¡Completado!", state="complete")
            st.success(f"Archivo guardado: {sh.url}")
            st.balloons()
