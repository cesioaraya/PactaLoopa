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
    
    <!-- Meta etiquetas para el icono al guardar en el móvil -->
    <link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/2163/2163154.png">
    <link rel="icon" href="https://cdn-icons-png.flaticon.com/512/2163/2163154.png">
    """, unsafe_allow_html=True)

st.title("🤝 PactaLoopa")

# --- LÓGICA DE ESTADO ---
if "grupo_id" not in st.session_state:
    st.session_state.grupo_id = None
    st.session_state.nombre_pacto = ""
    st.session_state.vista = "inicio"

# --- NAVEGACIÓN ---

# VISTA 1: PANTALLA DE INICIO (Botones principales)
if st.session_state.vista == "inicio":
    st.subheader("¿Qué deseas hacer hoy?")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✨ Crear Nuevo Pacto"):
            st.session_state.vista = "crear"
            st.rerun()
            
    with col2:
        if st.button("🤝 Unirse a un Pacto"):
            st.session_state.vista = "unirse"
            st.rerun()

# VISTA 2: CREAR NUEVO PACTO
elif st.session_state.vista == "crear":
    if st.button("⬅️ Volver"):
        st.session_state.vista = "inicio"
        st.rerun()
        
    st.subheader("Configurar Pacto")
    nombre_pacto_input = st.text_input("Nombre del Pacto", placeholder="Ej. Familia y Amigos")
    monto = st.number_input("Cuota por persona ($)", min_value=1, value=100)
    frecuencia = st.selectbox("Frecuencia", ["Semanal", "Quincenal", "Mensual"])
    
    if st.button("🚀 Crear y Generar Código"):
        if nombre_pacto_input:
            try:
                codigo_unico = generar_codigo()
                data = {
                    "nombre": nombre_pacto_input,
                    "monto_cuota": monto,
                    "frecuencia": frecuencia.lower(),
                    "codigo": codigo_unico
                }
                res = supabase.table("grupos").insert(data).execute()
                st.session_state.grupo_id = res.data[0]['id']
                st.session_state.nombre_pacto = nombre_pacto_input
                st.session_state.vista = "dashboard"
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
        else:
            st.warning("Por favor, ponle un nombre al pacto.")

# VISTA 3: UNIRSE A PACTO
elif st.session_state.vista == "unirse":
    if st.button("⬅️ Volver"):
        st.session_state.vista = "inicio"
        st.rerun()
        
    st.subheader("Unirse a un Pacto")
    codigo_input = st.text_input("Introduce el código").upper().strip()
    tu_nombre = st.text_input("Tu nombre o alias")
    
    if st.button("🤝 Unirme al Loop"):
        if codigo_input and tu_nombre:
            grupo = supabase.table("grupos").select("*").eq("codigo", codigo_input).execute()
            if len(grupo.data) > 0:
                id_g = grupo.data[0]['id']
                supabase.table("participantes").insert({"grupo_id": id_g, "nombre_usuario": tu_nombre}).execute()
                st.session_state.grupo_id = id_g
                st.session_state.nombre_pacto = grupo.data[0]['nombre']
                st.session_state.vista = "dashboard"
                st.rerun()
            else:
                st.error("Código no encontrado.")

# VISTA 4: DASHBOARD
elif st.session_state.vista == "dashboard":
    with st.sidebar:
        st.info(f"📍 Pacto: **{st.session_state.nombre_pacto}**")
        if st.button("🚪 Salir del Pacto"):
            st.session_state.grupo_id = None
            st.session_state.vista = "inicio"
            st.rerun()

    st.subheader(f"Pacto: {st.session_state.nombre_pacto}")
    
    participantes_db = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("id").execute()
    lista_p = participantes_db.data

    tab1, tab2 = st.tabs(["🔄 El Loop Actual", "📋 Gestión de Pagos"])

    with tab1:
        # --- NUEVO BLOQUE PARA MOSTRAR EL CÓDIGO SIEMPRE ---
        g_info = supabase.table("grupos").select("codigo").eq("id", st.session_state.grupo_id).execute()
        codigo_pacto = g_info.data[0]['codigo'] if g_info.data else "N/A"
        
        st.info(f"### 🆔 Código de Invitación: `{codigo_pacto}`")
        st.caption("Comparte este código con tus amigos para que se unan al pacto.")
        st.divider()
        # --------------------------------------------------

        if not lista_p:
            st.warning("Aún no hay participantes en este loop.")
        else:
            st.write("### 🏆 Orden de Beneficiarios")
            for idx, p in enumerate(lista_p):
                icon = "✅" if p['completado'] else "⏳"
                st.write(f"{idx+1}. {icon} **{p['nombre_usuario']}**")

    with tab2:
        st.write("### ✅ Confirmar Pagos")
        if not lista_p:
            st.write("No hay participantes todavía.")
        else:
            nuevos_estados = {}
            for p in lista_p:
                nuevos_estados[p['id']] = st.checkbox(
                    f"Pago recibido de: {p['nombre_usuario']}", 
                    value=p['completado'],
                    key=f"pago_id_{p['id']}"
                )
            
            if st.button("💾 Guardar Cambios en la Nube"):
                try:
                    for p_id, estado in nuevos_estados.items():
                        supabase.table("participantes").update({"completado": estado}).eq("id", p_id).execute()
                    st.success("¡Base de datos actualizada con éxito!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al actualizar: {e}")

# --- PIE DE PÁGINA ---
st.markdown("---")
st.markdown("""
<div style='text-align: center;'>
    <p style='color: gray; font-size: 0.8em;'>PactaLoopa - Registro transparente para grupos de confianza.</p>
    <p>PactaLoopa es una herramienta de uso libre y gratuito.</p>
    <p>¿Te ha servido? Puedes apoyar el proyecto invitándome a un café en: 
    <br>
    <a href='https://buymeacoffee.com/cesioaraya' target='_blank'>buymeacoffee.com/cesioaraya</a></p>
</div>
""", unsafe_allow_html=True)
