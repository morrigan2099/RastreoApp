import pydeck as pdk
import streamlit as st
import pandas as pd
from pyairtable import Api
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader
import json

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor de Reparto Pro", layout="wide")

# ==========================================
# 🔐 ZONA DE CONFIGURACIÓN
# ==========================================

# 1. AIRTABLE (Genera uno nuevo por seguridad)
AIRTABLE_API_KEY = "patyclv7hDjtGHB0F.19829008c5dee053cba18720d38c62ed86fa76ff0c87ad1f2d71bfe853ce9783"
AIRTABLE_BASE_ID = "appglio1RmA0AoWTP"
AIRTABLE_TABLE_NAME = "Rutas_Vivo"

# 2. CLOUDINARY (Genera uno nuevo por seguridad)
CLOUDINARY_CLOUD_NAME = "dlj0pdv6i"
CLOUDINARY_API_KEY = "847419449273122"
CLOUDINARY_API_SECRET = "i0cJCELeYVAosiBL_ltjHkM_FV0" 

# 3. GOOGLE SHEETS
# Instrucción: Pega el JSON nuevo. El código limpiará los errores de formato automático.
GOOGLE_JSON_RAW = """
{
  "type": "service_account",
  "project_id": "rastreoreparto",
  "private_key_id": "50aefda9bd4c6d17b1a293a43177b48e693d2cd1",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDNLffPRpFyktIB\nOGF6Z26VGvDCstA91dhOdRbZsXvcs1kBKW0sWoP0ocpM9qXzOM5pujGIFrpSXfQO\n2w6tacsJGMm/GBeK9ZRRRp6vlDsY85Zx1j+WxYJCbXh6sTj4y7GLJmPKuQnLcWiI\n80RFMnoG3dcUeJaYHOTlna3eisB4JjekX1cTlv+ZNr3xWLIUN9exS3hDe6LVZoiX\ndO90QUYGdoEsGwcNnqejC/zvW4bqvRXgs1qEqnakjbL+2d1N+qM94egsjeentzhZ\nueeUF4w4cQB0cbCcYdJXh0AQEjTNUMtus6Qp/T5UR5Y3y2c8ahRFhJXsmgRrtpzt\nP4oWTJpJAgMBAAECggEADaAZemkvKD7GBaj49zQWcL4r4iAWCl8wuMAXkwARb8X0\nuYom2vjNVcHnQW5pNZJOidCgsK8Cs0zUM+bZ7gvuHOXpouAukw6tKWsRR2tmc8kc\nUuW1jhWCaZcjtrEdbY84VHtpidk5JGqc9KhD/rzkA9/4RB6gcIxNqo5qsRJBhxDz\nFRVJfsBJxpYPbvBRlnbdQDgzhdj6NtniWMCTHXJuPgw9vnGyKMlLlY/+BSPNlfIb\nHHurHi6M1rjSJLwHlda+xBaHFSU2lxHtiEeNbeakA8sTdK6bINQM9wqjNy7rdzgH\nLeCTg6+biipMlRl41JnS1tsHFxX849jmZU0wh0ueYQKBgQD69uIoAEZgShBTCOKk\nToqjDBR4c0Yz3BnvpcWwbW+57VsVTGsyXR0vh5SW31cFkYMJpleufJX0ut94i1De\naWsPOYd6Ic5K+EbK3T/F5lHMMy8KCpYMDw9Cxai66HdaWmN79RBLf7WVpc9J1Zni\n4rzTiNKRc5KJLzhaadnamMGraQKBgQDRS+dllhp0Ak03gVMEOBK78+YzWIGaqLym\nFS5JgMSrOTPnTO4NBvJ1dhlYVaiJ7AFgfgurGWaOLQWuqG9pUu9v2fRv/NWcvf8b\n1jCqXmkLYe7465nCPwjpz9E52epT2z2UL0PPtIPdT58v5c+61GoHx5e0irrhzynB\nW6pXMT374QKBgQDz40MLDqFV6AQPPb5LYMyYASBPoe7ibQ6Ddz0z5FZEgKcYfqha\nTGUVkJPVPvxpu+x1T0M8nXR5XbXYhsMzMY1KQWUoSnwZHUhm0zarktWBNWiMQJdq\n5qO1BzOfWFTM6LRvfUu1o0mLQZS9sygWdrR8eiXwFjmcudfw/ZcqOXNUqQKBgCt7\nyaehd/2CPOi7RbQqsjm6gqlISiUHyan33JYI2tN4HwB/SzYJq3YcA0gHA+0jy2Vw\nypvRuyzuza9r7znCsVxbvB1IOllGYCo4ZgP/eXOT9UJiMJ/a2M87Dg0m6Thi5HhV\nGZGdv4fLcxdQd8gpOZ5EKZCpAgrIL7Sshsd2w5oBAoGBAMeP6SC7K2riOiicd5Rw\nW0DqYeB0NhhMQs67JNP6RWyOM9obD8/Av2NRdrz8O0MP2cmr9tdNp7BaKuVik+x8\nD/ixUmPkfmG2IxhUlS0+WJodq8H/SkYFYZAU+0dbFWCow2ngXNa4Cyc5CALjOShl\nk+/tFQRInEjuadSRWCkVZ0PC\n-----END PRIVATE KEY-----\n",
  "client_email": "gestor-reparto@rastreoreparto.iam.gserviceaccount.com",
  "client_id": "111821275315601188401",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/gestor-reparto%40rastreoreparto.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
"""

# 4. ADMIN
EMAIL_ADMIN = "morrigan2099@gmail.com"

# ==========================================
# 🔌 CONEXIÓN A SERVICIOS (CON LIMPIEZA AUTOMÁTICA)
# ==========================================
try:
    # A) Procesar JSON de Google con LIMPIEZA
    if "REEMPLAZA" in GOOGLE_JSON_RAW or len(GOOGLE_JSON_RAW) < 50:
        st.error("⚠️ Falta pegar el JSON de Google en la variable GOOGLE_JSON_RAW.")
        st.stop()
        
    # --- LA SOLUCIÓN AL ERROR ---
    # Limpiamos espacios "duros" (\xa0) y tabulaciones raras que rompen el JSON
    json_limpio = GOOGLE_JSON_RAW.replace('\xa0', ' ').replace('\\\n', '\\n')
    
    google_creds_dict = json.loads(json_limpio, strict=False)
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

except json.JSONDecodeError as e:
    st.error(f"Error de formato JSON: {e}")
    st.info("Consejo: Asegúrate de haber copiado desde la primera llave { hasta la última }")
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

    try:
        records = table.all()
    except Exception as e:
        st.error(f"Error leyendo Airtable: {e}")
        records = []

    if records:
        data = [r['fields'] for r in records]
        df = pd.DataFrame(data)
        
        # Normalización de Nombres
        df.columns = [c.lower() for c in df.columns]
        
        rename_map = {}
        for col in df.columns:
            if 'lat' in col: rename_map[col] = 'Latitud'
            if 'lon' in col: rename_map[col] = 'Longitud'
            if 'usu' in col: rename_map[col] = 'Usuario'
            if 'tipo' in col: rename_map[col] = 'Tipo'
            if 'foto' in col and 'etiq' not in col: rename_map[col] = 'Foto'
            if 'etiq' in col: rename_map[col] = 'Etiqueta_Foto'
            if 'fecha' in col: rename_map[col] = 'Fecha'
            if 'hora' in col: rename_map[col] = 'Hora'
            
        df = df.rename(columns=rename_map)

        if 'Tipo' not in df.columns: df['Tipo'] = 'GPS'

        df_gps = df[df['Tipo'] != 'FOTO'].copy()
        df_fotos = df[df['Tipo'] == 'FOTO'].copy()
        
        st.metric("📦 Paquetes/Evidencias hoy", len(df_fotos))
        
        # Mapa Protegido
        if not df_gps.empty and 'Latitud' in df_gps.columns and 'Longitud' in df_gps.columns:
            df_gps['Latitud'] = pd.to_numeric(df_gps['Latitud'], errors='coerce')
            df_gps['Longitud'] = pd.to_numeric(df_gps['Longitud'], errors='coerce')
            df_gps = df_gps.dropna(subset=['Latitud', 'Longitud'])
            
            if not df_gps.empty:
                import pydeck as pdk # Asegúrate de importar esto arriba, o déjalo aquí

            # 1. Calcular el centro del mapa automáticamente
            lat_center = df_gps['Latitud'].mean()
            lon_center = df_gps['Longitud'].mean()

            # 2. Configurar la Capa de Puntos (Scatterplot)
            layer = pdk.Layer(
                "ScatterplotLayer",
                df_gps,
                get_position='[Longitud, Latitud]', # Ojo: PyDeck pide Longitud primero
                get_color='[0, 100, 255, 160]',      # Azul brillante con transparencia
                get_radius=8,                        # Radio en METROS (ajusta esto si quieres más chicos)
                pickable=True,                       # Permite pasar el mouse y ver datos
                radius_min_pixels=3,                 # Tamaño mínimo en pantalla (para que no desaparezcan al alejar)
                radius_max_pixels=10,                # Tamaño máximo
            )

            # 3. Configurar la Vista Inicial
            view_state = pdk.ViewState(
                latitude=lat_center,
                longitude=lon_center,
                zoom=15, # Zoom cercano
                pitch=0, # Inclinación (0 es vista desde arriba, como mapa 2D)
            )

            # 4. Renderizar el Mapa
            st.pydeck_chart(pdk.Deck(
                map_style='mapbox://styles/mapbox/light-v9', # Estilo de mapa limpio
                layers=[layer],
                initial_view_state=view_state,
                tooltip={"text": "Chofer: {Usuario}\nHora: {Hora}"} # Lo que sale al pasar el mouse
            ))
            else:
                st.warning("Coordenadas inválidas detectadas.")
        else:
            st.info("Esperando coordenadas GPS...")

        # Galería
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
        st.info("Airtable conectado. Esperando datos...")

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
            
            data = [r['fields'] for r in records]
            df = pd.DataFrame(data)
            
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

            fecha = df['Fecha'].iloc[0] if 'Fecha' in df.columns else "General"
            nombre_libro = f"Reparto_{fecha}"
            
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

            for usuario in usuarios:
                status.write(f"🔄 Procesando: **{usuario}**")
                
                if 'Usuario' in df.columns:
                    df_u = df[df['Usuario'] == usuario].copy()
                else:
                    df_u = df.copy()
                
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
                
                cols = ['Hora', 'Tipo', 'Etiqueta_Foto', 'Latitud', 'Longitud', 'Zona', 'Foto_Link_Cloudinary']
                for c in cols:
                    if c not in df_u.columns: df_u[c] = ""
                
                datos_finales = df_u[cols].values.tolist()
                
                try:
                    ws = sh.add_worksheet(title=str(usuario), rows=1000, cols=10)
                    ws.append_row(cols)
                except:
                    ws = sh.worksheet(str(usuario))
                
                ws.append_rows(datos_finales)
                pasos_completados += len(df_u)
                bar.progress(min(pasos_completados / total_pasos, 1.0))

            status.write("🗑️ Limpiando Airtable...")
            ids = [r['id'] for r in records]
            table.batch_delete(ids)
            
            status.update(label="¡Completado!", state="complete")
            st.success(f"Archivo guardado: {sh.url}")
            st.balloons()
