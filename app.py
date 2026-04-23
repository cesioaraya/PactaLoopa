import streamlit as st
import pandas as pd
from supabase import create_client, Client
import random
import string
from datetime import datetime, date, timedelta

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

# 3. ESTILO MEJORADO
st.markdown("""
    <style>
    .stButton>button { border-radius: 20px; width: 100%; }
    .days-badge { background-color: #e8f0fe; color: #1a73e8; padding: 5px 10px; border-radius: 10px; font-weight: bold; }
    .info-card { background-color: #f8f9fa; padding: 15px; border-radius: 15px; border-left: 5px solid #1a73e8; margin-bottom: 20px; }
    .status-badge { padding: 2px 8px; border-radius: 5px; font-size: 0.8em; font-weight: bold; }
    .pago-si { background-color: #d4edda; color: #155724; }
    .pago-no { background-color: #fff3cd; color: #856404; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤝 PactaLoopa")

if "grupo_id" not in st.session_state:
    st.session_state.update({"grupo_id": None, "vista": "inicio", "mi_nombre": ""})

# --- LÓGICA DE NAVEGACIÓN (CREAR/UNIRSE) ---
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
    monto = st.number_input("Cuota Mensual ($)", min_value=1, value=100)
    frecuencia = st.selectbox("Frecuencia", ["Semanal", "Quincenal", "Mensual"])
    fecha_inicio = st.date_input("Fecha primer pozo", value=date.today())
    pass_pacto = st.text_input("Contraseña del grupo", type="password")
    tu_nombre = st.text_input("Tu nombre (Admin)").strip()
    
    if st.button("🚀 Crear Pacto"):
        if nombre_pacto and tu_nombre and pass_pacto:
            codigo = generar_codigo()
            res = supabase.table("grupos").insert({
                "nombre": nombre_pacto, "monto_cuota": monto, 
                "frecuencia": frecuencia.lower(), "fecha_inicio": fecha_inicio.isoformat(),
                "codigo": codigo, "password": pass_pacto, "abierto": True
            }).execute()
            gid = res.data[0]['id']
            # Importante: Agregamos columnas 'pago_cuota' y 'recibio_pozo' (booleanos) en tu DB
            supabase.table("participantes").insert({
                "grupo_id": gid, "nombre_usuario": tu_nombre, 
                "posicion_orden": 0, "pago_cuota": False, "recibio_pozo": False
            }).execute()
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
    opciones = ["-- Seleccionar --", "-- Nuevo Miembro --"] + nombres
    sel = st.selectbox("¿Quién eres?", opciones)
    
    if sel == "-- Nuevo Miembro --":
        nuevo = st.text_input("Tu nombre").strip()
        if st.button("Unirme") and nuevo:
            max_pos = max([p['posicion_orden'] for p in p_db.data]) if p_db.data else -1
            supabase.table("participantes").insert({
                "grupo_id": st.session_state.grupo_id, "nombre_usuario": nuevo, 
                "posicion_orden": max_pos + 1, "pago_cuota": False, "recibio_pozo": False
            }).execute()
            st.session_state.mi_nombre = nuevo; st.session_state.vista = "dashboard"; st.rerun()
    elif sel != "-- Seleccionar --":
        if st.button(f"Entrar como {sel}"):
            st.session_state.mi_nombre = sel; st.session_state.vista = "dashboard"; st.rerun()

# --- DASHBOARD PRINCIPAL ---
elif st.session_state.vista == "dashboard":
    g_res = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
    grupo = g_res.data[0]
    p_res = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("posicion_orden").execute()
    participantes = p_res.data
    
    admin_nombre = participantes[0]['nombre_usuario']
    es_admin = (st.session_state.mi_nombre == admin_nombre)
    yo = next(p for p in participantes if p['nombre_usuario'] == st.session_state.mi_nombre)

    # Lógica de Beneficiario (el primero que no ha recibido el pozo)
    beneficiario = next((p for p in participantes if not p['recibio_pozo']), None)
    idx_periodo = participantes.index(beneficiario) if beneficiario else 0
    salto = {"semanal": 7, "quincenal": 15, "mensual": 30}[grupo['frecuencia']]
    fecha_entrega = date.fromisoformat(grupo['fecha_inicio']) + timedelta(days=idx_periodo * salto)

    t1, t2, t3 = st.tabs(["🔄 El Loop", "💰 Mi Pago", "⚙️ Admin" if es_admin else "ℹ️ Info"])

    with t1:
        st.subheader("Estado del Pacto")
        st.markdown(f"""
        <div class="info-card">
            👤 Beneficiario este mes: <b>{beneficiario['nombre_usuario'] if beneficiario else 'Ciclo Completo'}</b><br>
            💰 Pozo acumulado: <b>${grupo['monto_cuota'] * (len(participantes)-1)}</b><br>
            📅 Fecha de entrega: <b>{fecha_entrega.strftime('%d %b %Y')}</b>
        </div>
        """, unsafe_allow_html=True)
        
        for p in participantes:
            col_u, col_p, col_r = st.columns([2, 2, 1])
            with col_u:
                st.write(f"{'⭐ ' if p == beneficiario else ''}{p['nombre_usuario']}")
            with col_p:
                if p == beneficiario: 
                    st.caption("Recibe pozo")
                else:
                    status = "PAGADO" if p['pago_cuota'] else "PENDIENTE"
                    clase = "pago-si" if p['pago_cuota'] else "pago-no"
                    st.markdown(f"<span class='status-badge {clase}'>{status}</span>", unsafe_allow_html=True)
            with col_r:
                if p['recibio_pozo']: st.write("🎁")

    with t2:
        st.subheader("Tu actividad este mes")
        if yo == beneficiario:
            st.success("Este mes te toca recibir el pozo. No debes pagar cuota.")
            st.info(f"Recibirás: **${grupo['monto_cuota'] * (len(participantes)-1)}**")
        else:
            if yo['pago_cuota']:
                st.success("✅ Tu cuota de este mes ya fue confirmada.")
            elif yo['aviso_pago']:
                st.warning("🔔 Pago reportado. Esperando que el administrador confirme.")
                if st.button("Cancelar Reporte"):
                    supabase.table("participantes").update({"aviso_pago": False}).eq("id", yo['id']).execute()
                    st.rerun()
            else:
                st.write(f"Debes pagar: **${grupo['monto_cuota']}** a {admin_nombre}")
                if st.button("📢 YA DEPOSITÉ MI CUOTA"):
                    supabase.table("participantes").update({"aviso_pago": True}).eq("id", yo['id']).execute()
                    st.rerun()

    if es_admin:
        with t3:
            st.subheader("Control de Admin")
            # 1. Validar cuotas individuales
            avisos = [p for p in participantes if p['aviso_pago']]
            if avisos:
                st.write("---")
                st.write("🔔 **Validar pagos recibidos:**")
                for a in avisos:
                    if st.button(f"Confirmar pago de {a['nombre_usuario']} ($ {grupo['monto_cuota']})"):
                        supabase.table("participantes").update({"aviso_pago": False, "pago_cuota": True}).eq("id", a['id']).execute()
                        st.rerun()
            
            # 2. Entregar Pozo (Cierre de mes)
            st.write("---")
            st.write("🎁 **Cierre de Periodo:**")
            # Todos los que NO son el beneficiario deben haber pagado
            otros_pagaron = all(p['pago_cuota'] for p in participantes if p != beneficiario)
            
            if beneficiario:
                if otros_pagaron:
                    st.success(f"¡Listo! Todos pagaron. Entrega el pozo a {beneficiario['nombre_usuario']}")
                    if st.button(f"CONFIRMAR ENTREGA DE POZO A {beneficiario['nombre_usuario']}"):
                        # 1. El beneficiario se marca como que ya recibió su pozo
                        # 2. Se resetean los 'pago_cuota' de todos para el siguiente mes
                        supabase.table("participantes").update({"recibio_pozo": True}).eq("id", beneficiario['id']).execute()
                        supabase.table("participantes").update({"pago_cuota": False, "aviso_pago": False}).eq("grupo_id", st.session_state.grupo_id).execute()
                        st.rerun()
                else:
                    st.warning("No puedes cerrar el mes hasta que todos los miembros paguen su cuota.")
            
            if st.button("♻️ Reiniciar Todo el Pacto (Cuidado)"):
                supabase.table("participantes").update({"pago_cuota": False, "aviso_pago": False, "recibio_pozo": False}).eq("grupo_id", st.session_state.grupo_id).execute()
                st.rerun()
