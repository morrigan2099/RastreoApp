import streamlit as st
import pandas as pd
from pyairtable import Api
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader
import json

# --- 1. CONFIGURACIÓN DE PÁGINA (Debe ir al principio) ---
st.set_page_config(page_title="Monitor de Reparto Pro", layout="wide")

# ==========================================
# 🔐 ZONA DE CONFIGURACIÓN
# ==========================================

# 1. AIRTABLE
# Pega tu token que empieza con pat...
AIRTABLE_API_KEY = "patTrMFsrNo8s08D4.2ea242addb56789c66594cf25aec786d96beaa419bc7a01766346a107f2be0dd"
AIRTABLE_BASE_ID = "appglio1RmA0AoWTP"
AIRTABLE_TABLE_NAME = "Rutas_Vivo"

# 2. CLOUDINARY
CLOUDINARY_CLOUD_NAME = "dlj0pdv6i"
CLOUDINARY_API_KEY = "847419449273122"
# ⚠️ Pega aquí tu SECRET real (el que empieza con i0c...)
CLOUDINARY_API_SECRET = "i0cJCELeYVAosiBL_ltjHkM_FV0" 

# 3. GOOGLE SHEETS
# Instrucción: Borra el texto de ejemplo y PEGA TU JSON COMPLETO entre las comillas triples.
GOOGLE_JSON_RAW = """{
  "type": "service_account",
  "project_id": "rastreoreparto",
  "private_key_id": "44ef539da139b22953aef118c402d64846a47c9e",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC1M2Scz1kgjLz+\naH7jKG05/Rw02o4jSY5T/8cPbbP/SpWvypFal15LKcMIqx0APvhvfmzXfPype1va\nOflJ107CmHT3mYxLbPNsI3kNzkfRXFFgSRPz9/2zTj9aWaRSkLo8MFe63bqBZhP+\nssAS06bRkZMtxbz3XXGCFxnTPwbZ0K5eYXSCrUSQ2Ve4y+hBa2U0MeimgQD0gFqu\nIm55aAk+E8lpIkGV5gQnmcafzvJTus5VGc2LlxAeQqwIcO9ZTdIkWmPaDr+NPjnR\nNvfaK+NCebx+i6Zn8jPGxjbvRCOpaXBHso0WKrusRPvWYtfo2BJJphg2edoBaLeZ\n1Y8tnhMrAgMBAAECggEACreRmwAH2U0pp8cTa35fyMm9H4J7sf+ZkO30XpJno9D2\nqHvhJqFZnOAennEhw9AgToEvkSaIem0G4jyCj4j8qgrCrvBLJBzmCtPQRu5Clic7\n0uePlrg+A5sRqSzbHgexqXoB06tl6rMDD2c6xVefqrki94FAq3AV6hKmtDVVQ5BN\nJe4xllyBiBpnK28axUO3jZUJK1+v0H2i8kces4d4HD+a8z6J0FJsugb7d34Nlf6f\n36MSwdxX0poE120lpEew3lOtTH6Pg0J+vNymIjF8aWW1SDGANZDYO0+I8KpVs9ac\n8ZyiV1YoOqPR5fCBSREXBE2FHcmSkJgECFnZg9twbQKBgQD9uax9K8MztLyhHZLW\nsRtOHQuRdadON9khXCxyyu6YxC79r5bRGxmnqEbhWojtlQFEGfoLhvHnZ+HGSkxT\nq6P0wzS80rurUbC+7Gaxkf4nVbDAY2wNzfdgz7rwn0tX0lYM2o33l/jvOFsK88/k\nfkMnpbuJnZ4lalMQApBJ/uRP9wKBgQC200SOmZ/ORMOiVJTCEM2ydnJA1zcd7Til\nt1Af2mehkOKR97n5mPnXQWd4CNHAt0UUNsTEMONwIeBpTqkRMAZRQ75DJZUOoXWB\nim2PZIxFIR4X7aINO14Ghkyb+FWhdgkLdkjx00Vo2U+lrRWSgIns9X1scVcNtNfn\n0/7SCsRxbQKBgFmr13RdlR2fENN4Wj8aVOYkicQc6sZQIqMRqnvfkLfZDiqGdizt\nAQIqDPL0RlSBRvNEowST6sa4BilIdPVVQhrtKqRZbg48TtULQ7gaOtK4DEHSYYv3\ncSh8AjuscLpXEiZ0z5vj0Azrw/F4/c5peV53ynH2jL/4debAoTIlrZc9AoGBAJ3L\nMnyxcxAgoYlV3x6wShkhyfLUzalyuVWuJeWYJ6F231aErWsT8W8r8BXV5tOiWmjb\n7HA4kdSSKJI7ZgiDnrA8+9YQddou2LB5vZ3pdnej4cldPGSXPMv81do4OBAnRB80\ndDjj1CBujyO7g8byUhjGuP4DxNL7pu1cN68pw+rxAoGBALJhR4dyZfo5q6JsxMJO\nfu3B1nt/ZOZ/rCMlMw4GFl/WA8GcqzBTgPVndgLL/a0ffRplzpSb3+jCHGIjsyGR\na2OpzEtKPIinXIK+2EcVnWW+IpjcjiqKY53t6uBTbC6JPdo0ld8s06fmrCu9Z7HA\nq5VHTHW2o4xLvqiAiOl0OePY\n-----END PRIVATE KEY-----\n",
  "client_email": "gestor-reparto@rastreoreparto.iam.gserviceaccount.com",
  "client_id": "111821275315601188401",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/gestor-reparto%40rastreoreparto.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}"""

# 4. ADMIN
EMAIL_ADMIN = "morrigan2099@gmail.com"

# ==========================================
# 🔌 CONEXIÓN A SERVICIOS
# ==========================================
try:
    # A) Procesar JSON de Google
    if "Pegar_Aqui" in GOOGLE_JSON_RAW:
        st.error("⚠️ Falta pegar el JSON de Google en el código (Variable GOOGLE_JSON_RAW).")
        st.stop()
        
    google_creds_dict = json.loads(GOOGLE_JSON_RAW)
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(google_creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)

    # B) Conectar Airtable
    api = Api(AIRTABLE_API_KEY)
    table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
    
    # C) Conectar Cloudinary
    cloudinary.config( 
        cloud_name = CLOUDINARY_CLOUD_NAME, 
        api_key = CLOUDINARY_API_KEY, 
        api_secret = CLOUDINARY_API_SECRET,
        secure = True
    )

except json.JSONDecodeError:
    st.error("Error de formato en el JSON de Google. Asegúrate de copiar TODO, incluyendo las llaves { }.")
    st.stop()
except Exception as e:
    st.error(f"Error de conexión general: {e}")
    st.stop()

# ==========================================
# 📱 INTERFAZ DE USUARIO
# ==========================================

st.title("🚚 Monitor de Reparto & Cloudinary")

tab1, tab2 = st.tabs(["📍 En Vivo", "☁️ Procesar y Archivar"])

# ------------------------------------------
# PESTAÑA 1: MAPA + GALERÍA
# ------------------------------------------
with tab1:
    col_kpi, col_btn = st.columns([4,1])
    with col_btn:
        if st.button("🔄 Refrescar"):
            st.rerun()

    # Intentar leer datos
    try:
        records = table.all()
    except Exception as e:
        st.error(f"Error leyendo Airtable: {e}")
        records = []

    if records:
        # 1. Crear DataFrame base
        data = [r['fields'] for r in records]
        df = pd.DataFrame(data)
        
        # 2. Normalización de Nombres (Para evitar errores de mayúsculas/minúsculas)
        # Esto soluciona el error "StreamlitAPIException"
        df.columns = [c.lower() for c in df.columns] # Todo a minúsculas
        
        rename_map = {}
        for col in df.columns:
            if 'lat' in col: rename_map[col] = 'Latitud'     # Detecta latitud, Latitude, lat
            if 'lon' in col: rename_map[col] = 'Longitud'    # Detecta longitud, Longitude, lon, lng
            if 'usu' in col: rename_map[col] = 'Usuario'     # Detecta usuario, Chofer
            if 'tipo' in col: rename_map[col] = 'Tipo'
            if 'foto' in col and 'etiq' not in col: rename_map[col] = 'Foto'
            if 'etiq' in col: rename_map[col] = 'Etiqueta_Foto'
            if 'fecha' in col: rename_map[col] = 'Fecha'
            if 'hora' in col: rename_map[col] = 'Hora'
            
        df = df.rename(columns=rename_map)

        # 3. Separar GPS y FOTOS
        if 'Tipo' not in df.columns:
            df['Tipo'] = 'GPS'

        df_gps = df[df['Tipo'] != 'FOTO'].copy()
        df_fotos = df[df['Tipo'] == 'FOTO'].copy()
        
        st.metric("📦 Paquetes/Evidencias hoy", len(df_fotos))
        
        # 4. MAPA A PRUEBA DE ERRORES
        if not df_gps.empty and 'Latitud' in df_gps.columns and 'Longitud' in df_gps.columns:
            # Forzar conversión a números (ignora errores de texto basura)
            df_gps['Latitud'] = pd.to_numeric(df_gps['Latitud'], errors='coerce')
            df_gps['Longitud'] = pd.to_numeric(df_gps['Longitud'], errors='coerce')
            
            # Eliminar filas donde no haya coordenadas válidas (NaN)
            df_gps = df_gps.dropna(subset=['Latitud', 'Longitud'])
            
            if not df_gps.empty:
                st.map(df_gps, latitude='Latitud', longitude='Longitud')
            else:
                st.warning("Hay datos GPS, pero las coordenadas no son válidas.")
        else:
            st.info("Esperando coordenadas GPS...")

        # 5. GALERÍA
        if not df_fotos.empty and 'Foto' in df_fotos.columns:
            st.subheader("Últimas Evidencias")
            cols = st.columns(4)
            for i, (idx, row) in enumerate(df_fotos.tail(8).iterrows()):
                col = cols[i % 4]
                if isinstance(row['Foto'], list) and len(row['Foto']) > 0:
                    url_img = row['Foto'][0]['url']
                    caption = f"{row.get('Usuario', '')} - {row.get('Etiqueta_Foto', '')}"
                    col.image(url_img, caption=caption)
    else:
        st.info("Airtable conectado, pero está vacío. Esperando datos de la App...")

# ------------------------------------------
# PESTAÑA 2: MOTOR DE MIGRACIÓN
# ------------------------------------------
with tab2:
    st.header("🗃️ Cierre del Día: Migración a Cloudinary")
    
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
            
            # Normalización rápida para el proceso de guardado
            df.columns = [c.lower() for c in df.columns]
            rename_map_save = {}
            for col in df.columns:
                if 'fecha' in col: rename_map_save[col] = 'Fecha'
                if 'usu' in col: rename_map_save[col] = 'Usuario'
                if 'hora' in col: rename_map_save[col] = 'Hora'
                if 'tipo' in col: rename_map_save[col] = 'Tipo'
                if 'foto' in col and 'etiq' not in col: rename_map_save[col] = 'Foto'
                if 'etiq' in col: rename_map_save[col] = 'Etiqueta_Foto'
                if 'lat' in col: rename_map_save[col] = 'Latitud'
                if 'lon' in col: rename_map_save[col] = 'Longitud'
                if 'zona' in col: rename_map_save[col] = 'Zona'
            
            df = df.rename(columns=rename_map_save)

            # Nombre del Libro
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
            
            if 'Usuario' in df.columns:
                usuarios = df['Usuario'].unique()
            else:
                usuarios = ["Desconocido"]

            total_pasos = len(records)
            pasos_completados = 0

            # 2. Procesar por Usuario
            for usuario in usuarios:
                status.write(f"🔄 Procesando: **{usuario}**")
                
                if 'Usuario' in df.columns:
                    df_u = df[df['Usuario'] == usuario].copy()
                else:
                    df_u = df.copy()
                
                # Función Cloudinary
                def procesar_imagen_cloudinary(row):
                    if row.get('Tipo') != 'FOTO' or 'Foto' not in row or not isinstance(row['Foto'], list):
                        return ""
                    try:
                        airtable_url = row['Foto'][0]['url']
                        nombre_archivo = f"{fecha}_{usuario}_{str(row.get('Hora','')).replace(':','')}"
                        
                        res = cloudinary.uploader.upload(
                            airtable_url, 
                            public_id=nombre_archivo,
                            folder="repartos_evidencia",
                            format="webp"
                        )
                        return res['secure_url']
                    except Exception as e:
                        return f"Error: {e}"

                df_u['Foto_Link_Cloudinary'] = df_u.apply(procesar_imagen_cloudinary, axis=1)
                
                # Columnas finales
                cols = ['Hora', 'Tipo', 'Etiqueta_Foto', 'Latitud', 'Longitud', 'Zona', 'Foto_Link_Cloudinary']
                # Rellenar vacíos
                for c in cols:
                    if c not in df_u.columns: df_u[c] = ""
                
                datos_finales = df_u[cols].values.tolist()
                
                # Escribir en Sheet
                try:
                    ws = sh.add_worksheet(title=str(usuario), rows=1000, cols=10)
                    ws.append_row(cols)
                except:
                    ws = sh.worksheet(str(usuario))
                
                ws.append_rows(datos_finales)
                pasos_completados += len(df_u)
                bar.progress(min(pasos_completados / total_pasos, 1.0))

            # 3. Limpiar Airtable
            status.write("🗑️ Limpiando Airtable...")
            ids = [r['id'] for r in records]
            table.batch_delete(ids)
            
            status.update(label="¡Completado!", state="complete")
            st.success(f"Archivo guardado: {sh.url}")
            st.balloons()
