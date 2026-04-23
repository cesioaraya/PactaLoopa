import streamlit as st
import pandas as pd
from supabase import create_client, Client
import random
import string

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PactaLoopa", page_icon="🤝", layout="centered")

# 2. CONEXIÓN A SUPABASE
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"].strip().replace("/rest/v1/", "").rstrip("/")
        key = st.secrets["SUPABASE_KEY"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error al conectar: {e}")
        return None

supabase = init_connection()

def generar_codigo():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# 3. ESTILO PERSONALIZADO E ICONO PARA MÓVIL
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #10b981; color: white; border: none; }
    .stButton>button:hover { background-color: #059669; color: white; }
    </style>
    <link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/2163/2163154.png">
    <link rel="icon" href="https://cdn-icons-png.flaticon.com/512/2163/2163154.png">
    """, unsafe_allow_html=True)

st.title("🤝 PactaLoopa")

# --- LÓGICA DE ESTADO ---
if "grupo_id" not in st.session_state:
    st.session_state.grupo_id = None
    st.session_state.nombre_pacto = ""
    st.session_state.vista = "inicio"
    st.session_state.mi_nombre = "" # Guardar el nombre del usuario actual

# --- NAVEGACIÓN ---

if st.session_state.vista == "inicio":
    st.subheader("¿Qué deseas hacer hoy?")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✨ Crear Nuevo Pacto"):
            st.session_state.vista = "crear"
            st.rerun()
            
    with col2:
        if st.button("🤝 Entrar a un Pacto"):
            st.session_state.vista = "unirse"
            st.rerun()

elif st.session_state.vista == "crear":
    if st.button("⬅️ Volver"):
        st.session_state.vista = "inicio"
        st.rerun()
        
    st.subheader("Configurar Pacto")
    nombre_pacto_input = st.text_input("Nombre del Pacto", placeholder="Ej. Familia y Amigos")
    monto = st.number_input("Cuota por persona ($)", min_value=1, value=100)
    frecuencia = st.selectbox("Frecuencia", ["Semanal", "Quincenal", "Mensual"])
    tu_nombre_admin = st.text_input("Tu nombre (serás el primero en la lista)")
    
    if st.button("🚀 Crear y Generar Código"):
        if nombre_pacto_input and tu_nombre_admin:
            try:
                codigo_unico = generar_codigo()
                data = {"nombre": nombre_pacto_input, "monto_cuota": monto, "frecuencia": frecuencia.lower(), "codigo": codigo_unico}
                res = supabase.table("grupos").insert(data).execute()
                
                gid = res.data[0]['id']
                # Auto-unirse como admin
                supabase.table("participantes").insert({"grupo_id": gid, "nombre_usuario": tu_nombre_admin}).execute()
                
                st.session_state.grupo_id = gid
                st.session_state.nombre_pacto = nombre_pacto_input
                st.session_state.mi_nombre = tu_nombre_admin
                st.session_state.vista = "dashboard"
                st.rerun()
            except Exception as e:
                st.error(f"Error al crear: {e}")
        else:
            st.warning("Completa el nombre del pacto y tu nombre.")

elif st.session_state.vista == "unirse":
    if st.button("⬅️ Volver"):
        st.session_state.vista = "inicio"
        st.rerun()
        
    st.subheader("Acceder al Pacto")
    codigo_input = st.text_input("Código de Invitación").upper().strip()
    tu_nombre = st.text_input("Tu nombre o alias")
    
    if st.button("🤝 Entrar"):
        if codigo_input and tu_nombre:
            grupo = supabase.table("grupos").select("*").eq("codigo", codigo_input).execute()
            if len(grupo.data) > 0:
                id_g = grupo.data[0]['id']
                
                # --- LÓGICA ANTI-DUPLICADOS ---
                # Buscamos si ya existe ese nombre en ese grupo
                existe = supabase.table("participantes").select("*").eq("grupo_id", id_g).eq("nombre_usuario", tu_nombre).execute()
                
                if len(existe.data) == 0:
                    # Si no existe, lo creamos
                    supabase.table("participantes").insert({"grupo_id": id_g, "nombre_usuario": tu_nombre}).execute()
                
                st.session_state.grupo_id = id_g
                st.session_state.nombre_pacto = grupo.data[0]['nombre']
                st.session_state.mi_nombre = tu_nombre
                st.session_state.vista = "dashboard"
                st.rerun()
            else:
                st.error("Código no encontrado.")

elif st.session_state.vista == "dashboard":
    with st.sidebar:
        st.info(f"👤 Usuario: **{st.session_state.mi_nombre}**\n\n📍 Pacto: **{st.session_state.nombre_pacto}**")
        if st.button("🚪 Salir del Pacto"):
            st.session_state.grupo_id = None
            st.session_state.vista = "inicio"
            st.rerun()

    # --- PESTAÑAS ---
    g_info = supabase.table("grupos").select("codigo").eq("id", st.session_state.grupo_id).execute()
    codigo_pacto = g_info.data[0]['codigo'] if g_info.data else "N/A"
    
    st.info(f"### 🆔 Código para compartir: `{codigo_pacto}`")

    participantes_db = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("id").execute()
    lista_p = participantes_db.data

    tab1, tab2 = st.tabs(["🔄 El Loop Actual", "📋 Gestión de Pagos"])

    with tab1:
        if not lista_p:
            st.info("Esperando participantes...")
        else:
            st.write("### 🏆 Orden de Beneficiarios")
            for idx, p in enumerate(lista_p):
                icon = "✅" if p['completado'] else "⏳"
                negrita = "**" if p['nombre_usuario'] == st.session_state.mi_nombre else ""
                st.write(f"{idx+1}. {icon} {negrita}{p['nombre_usuario']}{negrita}")

    with tab2:
        st.write("### ✅ Confirmar Pagos")
        # Aquí puedes decidir si CUALQUIERA marca pagos o solo un Admin. 
        # Por ahora, permitimos que cualquiera lo haga por transparencia.
        nuevos_estados = {}
        for p in lista_p:
            nuevos_estados[p['id']] = st.checkbox(f"Pago de: {p['nombre_usuario']}", value=p['completado'], key=f"p_id_{p['id']}")
        
        if st.button("💾 Guardar Cambios"):
            for p_id, estado in nuevos_estados.items():
                supabase.table("participantes").update({"completado": estado}).eq("id", p_id).execute()
            st.success("¡Sincronizado!")
            st.rerun()

# --- PIE DE PÁGINA ---
st.markdown("---")
st.markdown("""
<div style='text-align: center;'>
    <p>¿Te gusta la app? Apoya el proyecto en: <a href='https://buymeacoffee.com/cesioaraya' target='_blank'>buymeacoffee.com/cesioaraya</a></p>
</div>
""", unsafe_allow_html=True)
