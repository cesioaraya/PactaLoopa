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

# 3. ESTILO PERSONALIZADO
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #10b981; color: white; border: none; }
    .stButton>button:hover { background-color: #059669; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤝 PactaLoopa")

# --- LÓGICA DE ESTADO ---
if "grupo_id" not in st.session_state:
    st.session_state.grupo_id = None
    st.session_state.nombre_pacto = ""

# --- SIDEBAR ---
with st.sidebar:
    st.header("Menú Principal")
    modo = st.radio("¿Qué deseas hacer?", ["Crear Nuevo Pacto", "Unirse a un Pacto"])
    
    st.divider()

    if modo == "Crear Nuevo Pacto":
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
                    st.success(f"¡Pacto '{nombre_pacto_input}' creado!")
                    st.code(codigo_unico, language="text")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("Por favor, ponle un nombre al pacto.")
    
    else:
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
                    st.success(f"¡Unido a {st.session_state.nombre_pacto}!")
                    st.balloons()
                else:
                    st.error("Código no encontrado.")

# --- CUERPO PRINCIPAL ---
if st.session_state.grupo_id:
    st.subheader(f"Pacto: {st.session_state.nombre_pacto}")
    
    # Obtener participantes REALES
    participantes_db = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("id").execute()
    lista_p = participantes_db.data

    tab1, tab2 = st.tabs(["🔄 El Loop Actual", "📋 Gestión de Pagos"])

    with tab1:
        if not lista_p:
            st.info("Esperando participantes... comparte el código con tu grupo.")
        else:
            st.write("### 🏆 Orden de Beneficiarios")
            for idx, p in enumerate(lista_p):
                # Si ya cobró (completado), le ponemos un check
                icon = "✅" if p['completado'] else "⏳"
                st.write(f"{idx+1}. {icon} **{p['nombre_usuario']}**")

    with tab2:
        st.write("### ✅ Confirmar Pagos")
        if not lista_p:
            st.write("No hay participantes todavía.")
        else:
            # Diccionario para guardar los nuevos estados de los checkboxes
            nuevos_estados = {}
            
            for p in lista_p:
                # El valor inicial del checkbox viene de la base de datos (columna completado)
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
                    st.rerun() # Recarga la app para refrescar la lista de la Tab 1
                except Exception as e:
                    st.error(f"Error al actualizar: {e}")

else:
    st.info("👈 Selecciona 'Crear' o 'Unirse' en el menú lateral para empezar.")

st.markdown("---")
st.caption("PactaLoopa - Registro transparente para grupos de confianza.")
