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
    .stButton>button { border-radius: 20px; width: 100%; }
    .stat-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border: 1px solid #e1e4e8; text-align: center; }
    .catch-up { background-color: #fff3cd; padding: 15px; border-radius: 10px; border: 1px solid #ffeeba; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤝 PactaLoopa")

if "grupo_id" not in st.session_state:
    st.session_state.grupo_id = None
    st.session_state.vista = "inicio"
    st.session_state.mi_nombre = ""

# --- NAVEGACIÓN INICIAL ---
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
            res = supabase.table("grupos").insert({
                "nombre": nombre_pacto, 
                "monto_cuota": monto, 
                "frecuencia": frecuencia.lower(), 
                "codigo": codigo, 
                "password": pass_pacto
            }).execute()
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
            st.session_state.vista = "seleccionar_usuario"; st.rerun()
        else: st.error("Datos incorrectos")

elif st.session_state.vista == "seleccionar_usuario":
    p_db = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).execute()
    nombres = [p['nombre_usuario'] for p in p_db.data]
    sel = st.selectbox("¿Quién eres?", ["-- Nuevo --"] + nombres)
    if sel == "-- Nuevo --":
        nuevo = st.text_input("Tu nombre").strip()
        if st.button("Unirme") and nuevo:
            max_pos = max([p['posicion_orden'] for p in p_db.data]) if p_db.data else -1
            supabase.table("participantes").insert({"grupo_id": st.session_state.grupo_id, "nombre_usuario": nuevo, "posicion_orden": max_pos + 1}).execute()
            st.session_state.mi_nombre = nuevo
            st.session_state.vista = "dashboard"; st.rerun()
    else:
        if st.button(f"Entrar como {sel}"):
            st.session_state.mi_nombre = sel
            st.session_state.vista = "dashboard"; st.rerun()

# --- DASHBOARD PRINCIPAL ---
elif st.session_state.vista == "dashboard":
    g_res = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
    grupo = g_res.data[0]
    
    p_admin_check = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("id").execute()
    admin_nombre = p_admin_check.data[0]['nombre_usuario']
    
    p_res = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("posicion_orden").execute()
    participantes = p_res.data
    es_admin = (st.session_state.mi_nombre == admin_nombre)

    # Cálculo de fechas y periodos
    f_inicio = datetime.fromisoformat(grupo['creado_en'].split('T')[0])
    dias_periodo = {"semanal": 7, "quincenal": 15, "mensual": 30}[grupo['frecuencia']]
    hoy = datetime.now()

    with st.sidebar:
        st.write(f"### 🛡️ {grupo['nombre']}")
        st.info(f"Código: **{grupo['codigo']}**")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.grupo_id = None
            st.session_state.mi_nombre = ""
            st.session_state.vista = "inicio"
            st.rerun()

    t1, t2, t3 = st.tabs(["🔄 El Loop", "💰 Mi Pago", "⚙️ Admin" if es_admin else "ℹ️ Info"])

    with t1:
        st.subheader("Estado del Grupo")
        cobrados = [p for p in participantes if p['completado']]
        pendientes = [p for p in participantes if not p['completado']]
        
        # Identificar quién debería estar cobrando ahora
        indice_actual = len(cobrados)
        fecha_actual_pago = f_inicio + timedelta(days=indice_actual * dias_periodo)
        
        st.metric("Próximo Pozo", f"{fecha_actual_pago.strftime('%d %b')}")
        
        st.write("---")
        for i, p in enumerate(participantes):
            f_pago = f_inicio + timedelta(days=i * dias_periodo)
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.write(f"**{i+1}. {p['nombre_usuario']}**")
                st.caption(f"📅 {f_pago.strftime('%d %b %Y')}")
            with col_b:
                if p['completado']: st.success("✅")
                elif p['aviso_pago']: st.warning("🔔")
                else: st.info("⏳")

    with t2:
        yo = next(p for p in participantes if p['nombre_usuario'] == st.session_state.mi_nombre)
        st.subheader(f"Resumen de {st.session_state.mi_nombre}")
        
        # ¿Es tiempo de pagar? Bloqueamos si hoy es mucho antes de la fecha de inicio del pago actual
        # Permitimos reportar si hoy es mayor o igual a la fecha de inicio del ciclo del grupo
        puede_reportar = hoy >= f_inicio 

        if not yo['completado']:
            if len(cobrados) > 0:
                st.warning(f"Debes ponerte al día con los {len(cobrados)} que ya cobraron.")
            
            if yo['aviso_pago']:
                st.info("Esperando validación del administrador...")
                if st.button("❌ Cancelar reporte"):
                    supabase.table("participantes").update({"aviso_pago": False}).eq("id", yo['id']).execute()
                    st.rerun()
            else:
                if puede_reportar:
                    st.write(f"Cuota: **${grupo['monto_cuota']}**")
                    if st.button("📢 REPORTAR PAGO REALIZADO"):
                        supabase.table("participantes").update({"aviso_pago": True}).eq("id", yo['id']).execute()
                        st.rerun()
                else:
                    st.error("El periodo de pagos aún no ha comenzado.")
        else:
            st.success("Ya has recibido tu parte del pacto en este ciclo.")

    if es_admin:
        with t3:
            st.subheader("Validaciones")
            avisos = [p for p in participantes if p['aviso_pago'] and not p['completado']]
            for a in avisos:
                col1, col2 = st.columns([2, 1])
                col1.write(f"Confirmar pago de **{a['nombre_usuario']}**")
                if col2.button("Validar ✅", key=f"v_{a['id']}"):
                    supabase.table("participantes").update({"completado": True, "aviso_pago": False}).eq("id", a['id']).execute()
                    st.rerun()
            
            st.write("---")
            st.subheader("Gestión de Miembros")
            # Eliminar Miembros
            miembros_para_eliminar = [p['nombre_usuario'] for p in participantes if p['nombre_usuario'] != admin_nombre]
            if miembros_para_eliminar:
                u_eliminar = st.selectbox("Seleccionar para eliminar:", miembros_para_eliminar)
                if st.button("🗑️ Eliminar Miembro"):
                    # Eliminar de la DB
                    supabase.table("participantes").delete().eq("grupo_id", st.session_state.grupo_id).eq("nombre_usuario", u_eliminar).execute()
                    # Re-ordenar posiciones de los que quedan
                    restantes = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("posicion_orden").execute()
                    for i, r in enumerate(restantes.data):
                        supabase.table("participantes").update({"posicion_orden": i}).eq("id", r['id']).execute()
                    st.success(f"{u_eliminar} eliminado y orden ajustado.")
                    st.rerun()

            st.write("---")
            st.subheader("Reordenar")
            pend_nombres = [p['nombre_usuario'] for p in participantes if not p['completado']]
            if len(pend_nombres) > 1:
                nuevo_orden = st.multiselect("Cambiar orden de pendientes:", pend_nombres, default=pend_nombres)
                if st.button("💾 Guardar"):
                    orden_fijo = [p['nombre_usuario'] for p in participantes if p['completado']] + nuevo_orden
                    for i, nombre in enumerate(orden_fijo):
                        supabase.table("participantes").update({"posicion_orden": i}).eq("grupo_id", st.session_state.grupo_id).eq("nombre_usuario", nombre).execute()
                    st.rerun()

            with st.expander("Zona de Peligro"):
                if st.button("BORRAR PACTO"):
                    supabase.table("participantes").delete().eq("grupo_id", st.session_state.grupo_id).execute()
                    supabase.table("grupos").delete().eq("id", st.session_state.grupo_id).execute()
                    st.session_state.vista = "inicio"; st.rerun()
    else:
        with t3:
            st.write(f"Admin: {admin_nombre}")
            st.write(f"Frecuencia: {grupo['frecuencia']}")
