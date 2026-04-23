import streamlit as st
import pandas as pd
from supabase import create_client, Client
import random
import string
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN
st.set_page_config(page_title="PactaLoopa", page_icon="🤝", layout="centered")

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

# 3. ESTILO
st.markdown("""
    <style>
    .stButton>button { border-radius: 20px; }
    .status-box { padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; }
    .admin-confirm { background-color: #d1fae5; border-left: 5px solid #10b981; }
    .user-pending { background-color: #fef3c7; border-left: 5px solid #f59e0b; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤝 PactaLoopa")

if "grupo_id" not in st.session_state:
    st.session_state.grupo_id = None
    st.session_state.vista = "inicio"
    st.session_state.mi_nombre = ""

# --- NAVEGACIÓN INICIO (Crear/Unirse) se mantiene igual ---
if st.session_state.vista == "inicio":
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✨ Crear Nuevo Pacto"): st.session_state.vista = "crear"; st.rerun()
    with col2:
        if st.button("🤝 Entrar a un Pacto"): st.session_state.vista = "unirse"; st.rerun()

elif st.session_state.vista == "crear":
    if st.button("⬅️ Volver"): st.session_state.vista = "inicio"; st.rerun()
    st.subheader("Configurar Pacto")
    nombre_pacto = st.text_input("Nombre del Pacto")
    monto = st.number_input("Cuota ($)", min_value=1, value=100)
    frecuencia = st.selectbox("Frecuencia", ["Semanal", "Quincenal", "Mensual"])
    pass_pacto = st.text_input("Contraseña", type="password")
    tu_nombre = st.text_input("Tu nombre (Admin)").strip()
    
    if st.button("🚀 Crear Pacto"):
        if nombre_pacto and tu_nombre and pass_pacto:
            codigo = generar_codigo()
            res = supabase.table("grupos").insert({"nombre": nombre_pacto, "monto_cuota": monto, "frecuencia": frecuencia.lower(), "codigo": codigo, "password": pass_pacto}).execute()
            gid = res.data[0]['id']
            supabase.table("participantes").insert({"grupo_id": gid, "nombre_usuario": tu_nombre, "posicion_orden": 0}).execute()
            st.session_state.update({"grupo_id": gid, "mi_nombre": tu_nombre, "vista": "dashboard"})
            st.rerun()

elif st.session_state.vista == "unirse":
    if st.button("⬅️ Volver"): st.session_state.vista = "inicio"; st.rerun()
    c_in = st.text_input("Código").upper().strip()
    p_in = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        g = supabase.table("grupos").select("*").eq("codigo", c_in).eq("password", p_in).execute()
        if g.data:
            st.session_state.grupo_id = g.data[0]['id']
            st.session_state.vista = "seleccionar_usuario"
            st.rerun()
        else: st.error("Datos incorrectos")

elif st.session_state.vista == "seleccionar_usuario":
    p_db = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).execute()
    nombres = [p['nombre_usuario'] for p in p_db.data]
    sel = st.selectbox("¿Quién eres?", ["-- Nuevo --"] + nombres)
    if sel == "-- Nuevo --":
        nuevo = st.text_input("Tu nombre").strip()
        if st.button("Unirme") and nuevo:
            supabase.table("participantes").insert({"grupo_id": st.session_state.grupo_id, "nombre_usuario": nuevo, "posicion_orden": len(nombres)}).execute()
            st.session_state.mi_nombre = nuevo
            st.session_state.vista = "dashboard"; st.rerun()
    else:
        if st.button(f"Entrar como {sel}"):
            st.session_state.mi_nombre = sel
            st.session_state.vista = "dashboard"; st.rerun()

# --- DASHBOARD PRINCIPAL ---
elif st.session_state.vista == "dashboard":
    # Cargar datos
    g_res = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
    grupo = g_res.data[0]
    p_res = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("posicion_orden").execute()
    participantes = p_res.data
    
    es_admin = (participantes[0]['nombre_usuario'] == st.session_state.mi_nombre)

    with st.sidebar:
        st.write(f"### {grupo['nombre']}")
        st.write(f"Código: `{grupo['codigo']}`")
        if st.button("🚪 Salir"): st.session_state.vista = "inicio"; st.rerun()

    t1, t2, t3 = st.tabs(["🔄 El Loop", "💰 Mi Pago", "⚙️ Admin" if es_admin else "ℹ️ Info"])

    # TAB 1: EL LOOP & CALENDARIO
    with t1:
        st.subheader("Orden y Fechas")
        f_inicio = datetime.fromisoformat(grupo['creado_en'].split('T')[0])
        dias = {"semanal": 7, "quincenal": 15, "mensual": 30}[grupo['frecuencia']]
        
        for i, p in enumerate(participantes):
            f_pago = f_inicio + timedelta(days=i * dias)
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.write(f"**{i+1}. {p['nombre_usuario']}**")
                st.caption(f"📅 {f_pago.strftime('%d %b')}")
            with col_b:
                if p['completado']: st.success("Confirmado")
                elif p['aviso_pago']: st.warning("Pend. Confirmar")
                else: st.info("Pendiente")

    # TAB 2: MI PAGO (Doble Check)
    with t2:
        yo = next(p for p in participantes if p['nombre_usuario'] == st.session_state.mi_nombre)
        st.subheader("Gestión de mi cuota")
        st.metric("Monto a pagar", f"${grupo['monto_cuota']}")
        
        if yo['completado']:
            st.success("✅ ¡Pago confirmado por el administrador!")
        elif yo['aviso_pago']:
            st.warning("⏳ Ya avisaste del pago. Esperando confirmación del administrador.")
            if st.button("Cancelar aviso de pago"):
                supabase.table("participantes").update({"aviso_pago": False}).eq("id", yo['id']).execute()
                st.rerun()
        else:
            if st.button("🔔 Marcar como PAGADO (Avisar al admin)"):
                supabase.table("participantes").update({"aviso_pago": True}).eq("id", yo['id']).execute()
                st.rerun()

    # TAB 3: ADMIN (Confirmar pagos y Reordenar)
    if es_admin:
        with t3:
            st.subheader("🛡️ Panel de Control")
            
            # Sub-sección: Confirmar Pagos
            st.write("---")
            st.write("#### Confirmar Avisos de Usuarios")
            avisos = [p for p in participantes if p['aviso_pago'] and not p['completado']]
            if avisos:
                for a in avisos:
                    col1, col2 = st.columns([2, 1])
                    col1.write(f"¿Confirmas el pago de **{a['nombre_usuario']}**?")
                    if col2.button("✅ Confirmar", key=f"conf_{a['id']}"):
                        supabase.table("participantes").update({"completado": True}).eq("id", a['id']).execute()
                        st.rerun()
            else:
                st.info("No hay avisos de pago pendientes.")

            # Sub-sección: Reordenar
            st.write("---")
            st.write("#### Cambiar Orden del Loop")
            nombres_orden = [p['nombre_usuario'] for p in participantes]
            nuevo_orden = st.multiselect("Arrastra o selecciona en el nuevo orden:", nombres_orden, default=nombres_orden)
            
            if st.button("💾 Guardar Nuevo Orden"):
                if len(nuevo_orden) == len(nombres_orden):
                    for idx, nombre in enumerate(nuevo_orden):
                        supabase.table("participantes").update({"posicion_orden": idx}).eq("grupo_id", st.session_state.grupo_id).eq("nombre_usuario", nombre).execute()
                    st.success("Orden actualizado")
                    st.rerun()
                else: st.error("Debes incluir a todos los participantes en la lista.")

            # Sub-sección: Eliminar
            st.write("---")
            if st.checkbox("Mostrar opciones de eliminación"):
                if st.button("🔥 ELIMINAR TODO EL PACTO"):
                    supabase.table("participantes").delete().eq("grupo_id", st.session_state.grupo_id).execute()
                    supabase.table("grupos").delete().eq("id", st.session_state.grupo_id).execute()
                    st.session_state.vista = "inicio"; st.rerun()
