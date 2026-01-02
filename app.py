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
  "project_id": "rastreoreparto",
  "private_key_id": "bb56395c6228b29c8e86f572999a94b4d2ec196a",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCnjK8+VEoeWDtp\njsxBuX5W3IjQtijMco8pHmI5/kt84yZ50e8FHz249VBdyePjkCNVzmEANiRGf3RJ\nuSCo7v3JxqQOuwzF3uICXqII2272tP3WrPQKVzX2la4RUJ/FhlhHrS7GKKyQuqYm\nTMSscz+zT4z+Y2nKi6No9yOqc/kYb0eYH2maHAn+o2xeFxR0DDDdFPDhEMd/VTLi\nQ7bPewbDsqoipxFq6/QBGpOFgoOvLY9Q5BGsopAfdL4prR0u6Rkmyc4EPgyCF0YL\nf/J+t/odvk0ZH925w4iko8/ChJ9cXFMHTSwwHLis4tsLz0FLWc7ya0YVhlUvLOk0\nMOhTZA7zAgMBAAECggEAMQb4rItrmM+Gqw+u8zh9IJutqSz0aUbIX2bVpVSk8Clj\ns9fbUitfG0UlPBx8g7VEsbIPLkmpebuH4p66UNSGDMoEbY8MYMYkaj8YuPDE2ooB\nkRTQ4Em+r6YC5mwqJFl4cZjai/+Q51TGk4R5NGEQ7b5Eapfad/s+WNOgaxs+c4h6\nY3Eswx1WPqE1GMThw/bOMKK0VM41QsADH+82T8usa+97HYbGu2cbrns3ldNiIKbu\nZ6e0W+CbDkej9BesgPp/Il3MVyr+5yngQ5hSEq7x8m/dcb+f4Rb0Th4zzneU5RLb\n7sKncynHzzCLBioyeXbamaSF3yZ46lj5Jee9DDkRSQKBgQDpIPhbCBb4haABu+VT\niHe4k7KrBLI5+/auvDaZZ/ouMvKrryCPse3aGHG+t/t1T+/oh2pEKfzIEPgaor0l\nZtDUCAftmML+RdW+BaGPDHd0suppizGQRFgfeo4rJNHS0h/eZyztLvShrBORoy5n\nP3jgiup6mV/S1Oc64jcN/m1v3QKBgQC3/LESpsNpVqH/L2de5fBdVBdpCvbyooXb\nu/kWbCmUGho8FcLecdRX6JgXHyi6/d68r3hH4DamNEhpwTm6cjSK2HKE0TYeZjdC\nj2K5iTnZ94Fg184b5X1HwARzOlj62ngIlMVth4O05j1nCOW5yR1BiYrQNwlQNwgN\nyGmncdz1DwKBgCQLkfrZPFv+pSe/eoy42/Hw/D4PAtOOTqzjsvlzJy5/eB/tevZc\nx27iOqwHXFzeGDT2wwp5B3mTjhjoMqCWzhEKkNc+uF+CQrMXwcwRXGLxyua4u9gX\niRyM4XBwR/T1wjGr+DlP+kkJBxmMhn82RCVLtUdxcWxyuLHVCjgir58NAoGAdFic\nFSJVojBBguCUKsOXSz1ZDHj9jpPNuBVXP6GobVpQSrysHQS4ddrFCqIOnKjbiFAh\n7LnRdSrMu+uPuOJtbXvQd0LhSTn0KegIUzF+3uIP85CkaqmlnpDDf6ZfDErI6wxB\nCLFQTT3niFdtBh4ynPYATQjwn8QdGLIqddOgGWsCgYEA5KrYBB227E2yeh2/6MSw\npv44Hyc6q22ie+P7lFOCyG27OkRF227+w5k19WECmNTOOElOTUwM3NdAOC9w3inR\nNYmN5Vsal3FinKT764LX7KdIC1NEHB3pQMGs3UHdA0eDaOmKHcXDBAJhdU6wd82g\nwiYyxL97hGTx2+5vqkHhv1o=\n-----END PRIVATE KEY-----\n",
  "client_email": "gestor-reparto@rastreoreparto.iam.gserviceaccount.com",
  "client_id": "111821275315601188401",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/gestor-reparto%40rastreoreparto.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
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
