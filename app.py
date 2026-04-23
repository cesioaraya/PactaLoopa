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

# 3. ESTILO
st.markdown("""
    <style>
    .stButton>button { border-radius: 20px; width: 100%; }
    .days-badge { background-color: #e8f0fe; color: #1a73e8; padding: 5px 10px; border-radius: 10px; font-weight: bold; }
    .info-card { background-color: #f8f9fa; padding: 15px; border-radius: 15px; border-left: 5px solid #1a73e8; margin-bottom: 20px; }
    .status-badge { padding: 2px 8px; border-radius: 5px; font-size: 0.8em; font-weight: bold; }
    .pago-si { background-color: #d4edda; color: #155724; }
    .pago-no { background-color: #fff3cd; color: #856404; }
    .danger-zone { border: 1px solid #ff4b4b; padding: 15px; border-radius: 10px; margin-top: 20px; }
    .share-box { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border: 2px dashed #1a73e8; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤝 PactaLoopa")

# Inicializar estados
if "grupo_id" not in st.session_state:
    st.session_state.update({"grupo_id": None, "vista": "inicio", "mi_nombre": "", "mostrar_exito": False, "nuevo_codigo": ""})

# --- DIÁLOGO DE ÉXITO (MOSTRAR CÓDIGO) ---
@st.dialog("🚀 ¡Pacto Creado con Éxito!")
def mostrar_credenciales_nuevas(codigo, password):
    st.markdown("### 📢 ¡Comparte esto con tu grupo!")
    st.write("Para que los demás se unan, dales el código y la contraseña:")
    
    st.info("💡 Haz clic en el icono de copiar a la derecha de los cuadros negros.")
    
    st.write("**Código del Pacto:**")
    st.code(codigo, language=None)
    
    st.write("**Contraseña:**")
    st.code(password, language=None)
    
    if st.button("Entrar al Dashboard"):
        st.session_state.mostrar_exito = False
        st.rerun()

if st.session_state.mostrar_exito:
    mostrar_credenciales_nuevas(st.session_state.nuevo_codigo, st.session_state.nueva_pass)

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
            supabase.table("participantes").insert({
                "grupo_id": gid, "nombre_usuario": tu_nombre, 
                "posicion_orden": 0, "pago_cuota": False, "recibio_pozo": False
            }).execute()
            
            # Guardar para mostrar el mensaje de éxito
            st.session_state.update({
                "grupo_id": gid, 
                "mi_nombre": tu_nombre, 
                "vista": "dashboard",
                "mostrar_exito": True,
                "nuevo_codigo": codigo,
                "nueva_pass": pass_pacto
            })
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
    g_db = supabase.table("grupos").select("abierto").eq("id", st.session_state.grupo_id).execute()
    grupo_abierto = g_db.data[0].get('abierto', True)
    
    nombres = [p['nombre_usuario'] for p in p_db.data]
    opciones = ["-- Seleccionar --"]
    if grupo_abierto: opciones.append("-- Nuevo Miembro --")
    opciones.extend(nombres)
    
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
    if not g_res.data:
        st.session_state.update({"grupo_id": None, "vista": "inicio"}); st.rerun()
    
    grupo = g_res.data[0]
    p_res = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("posicion_orden").execute()
    participantes = p_res.data
    
    admin_nombre = participantes[0]['nombre_usuario'] if participantes else ""
    es_admin = (st.session_state.mi_nombre == admin_nombre)
    yo = next((p for p in participantes if p['nombre_usuario'] == st.session_state.mi_nombre), None)

    with st.sidebar:
        st.write(f"### 🛡️ {grupo['nombre']}")
        st.info(f"Usuario: **{st.session_state.mi_nombre}**")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.update({"grupo_id": None, "mi_nombre": "", "vista": "inicio"})
            st.rerun()

    beneficiario = next((p for p in participantes if not p.get('recibio_pozo', False)), None)
    idx_periodo = participantes.index(beneficiario) if beneficiario else 0
    salto = {"semanal": 7, "quincenal": 15, "mensual": 30}.get(grupo['frecuencia'], 30)
    fecha_entrega = date.fromisoformat(grupo['fecha_inicio']) + timedelta(days=idx_periodo * salto)

    t1, t2, t3 = st.tabs(["🔄 El Loop", "💰 Mi Pago", "⚙️ Admin" if es_admin else "ℹ️ Info"])

    with t1:
        st.subheader("Estado del Pacto")
        st.markdown(f"""
        <div class="info-card">
            👤 Beneficiario este mes: <b>{beneficiario['nombre_usuario'] if beneficiario else 'Ciclo Completo'}</b><br>
            💰 Pozo: <b>${grupo['monto_cuota'] * (len(participantes)-1)}</b><br>
            📅 Fecha de entrega: <b>{fecha_entrega.strftime('%d %b %Y')}</b>
        </div>
        """, unsafe_allow_html=True)
        
        for p in participantes:
            col_u, col_p, col_r = st.columns([2, 2, 1])
            with col_u: st.write(f"{'⭐ ' if p == beneficiario else ''}{p['nombre_usuario']}")
            with col_p:
                if p == beneficiario: st.caption("Recibe pozo")
                else:
                    status = "PAGADO" if p.get('pago_cuota') else "PENDIENTE"
                    clase = "pago-si" if p.get('pago_cuota') else "pago-no"
                    st.markdown(f"<span class='status-badge {clase}'>{status}</span>", unsafe_allow_html=True)
            with col_r:
                if p.get('recibio_pozo'): st.write("🎁")

    with t2:
        st.subheader("Tu actividad")
        if yo:
            if yo == beneficiario:
                st.success("Este mes te toca recibir el pozo. ¡No debes pagar cuota!")
            else:
                if yo.get('pago_cuota'):
                    st.success("✅ Tu cuota de este mes ya fue confirmada.")
                elif yo.get('aviso_pago'):
                    st.warning("🔔 Pago reportado. Esperando validación.")
                    if st.button("Cancelar Reporte"):
                        supabase.table("participantes").update({"aviso_pago": False}).eq("id", yo['id']).execute()
                        st.rerun()
                else:
                    st.info(f"Monto a pagar: **${grupo['monto_cuota']}**")
                    if st.button("📢 YA DEPOSITÉ"):
                        supabase.table("participantes").update({"aviso_pago": True}).eq("id", yo['id']).execute()
                        st.rerun()

    with t3:
        if es_admin:
            st.subheader("🔑 Credenciales de Acceso")
            st.write("Comparte estos datos con los miembros:")
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.write("**Código**")
                st.code(grupo['codigo'], language=None)
            with col_c2:
                st.write("**Contraseña**")
                st.code(grupo['password'], language=None)

            st.write("---")
            st.subheader("✅ Validar Cuotas")
            avisos = [p for p in participantes if p.get('aviso_pago')]
            if not avisos: st.caption("No hay pagos pendientes.")
            for a in avisos:
                if st.button(f"Confirmar pago de {a['nombre_usuario']} ($ {grupo['monto_cuota']})"):
                    supabase.table("participantes").update({"aviso_pago": False, "pago_cuota": True}).eq("id", a['id']).execute()
                    st.rerun()

            st.write("---")
            st.subheader("🎁 Cerrar Mes")
            otros_pagaron = all(p.get('pago_cuota') for p in participantes if p != beneficiario)
            if beneficiario:
                if otros_pagaron:
                    if st.button(f"CONFIRMAR ENTREGA DE POZO A {beneficiario['nombre_usuario']}"):
                        supabase.table("participantes").update({"recibio_pozo": True}).eq("id", beneficiario['id']).execute()
                        supabase.table("participantes").update({"pago_cuota": False, "aviso_pago": False}).eq("grupo_id", st.session_state.grupo_id).execute()
                        st.rerun()
                else: st.warning("Aún faltan miembros por pagar.")

            st.write("---")
            st.subheader("🔄 Organizar Loop")
            nombres_p = [p['nombre_usuario'] for p in participantes]
            nuevo_orden = st.multiselect("Cambiar orden:", nombres_p, default=nombres_p)
            if st.button("💾 Guardar Orden"):
                for idx, nombre in enumerate(nuevo_orden):
                    supabase.table("participantes").update({"posicion_orden": idx}).eq("grupo_id", st.session_state.grupo_id).eq("nombre_usuario", nombre).execute()
                st.rerun()

            st.write("---")
            st.subheader("🗑️ Miembros")
            opciones_eliminar = [p['nombre_usuario'] for p in participantes if p['nombre_usuario'] != admin_nombre]
            if opciones_eliminar:
                u_elim = st.selectbox("Eliminar a:", opciones_eliminar)
                if st.button("Eliminar Miembro"):
                    supabase.table("participantes").delete().eq("grupo_id", st.session_state.grupo_id).eq("nombre_usuario", u_elim).execute()
                    st.rerun()

            st.write("---")
            st.markdown('<div class="danger-zone">', unsafe_allow_html=True)
            st.subheader("☢️ Zona Peligrosa")
            if st.button("🔥 ELIMINAR TODO EL PACTO"):
                supabase.table("participantes").delete().eq("grupo_id", st.session_state.grupo_id).execute()
                supabase.table("grupos").delete().eq("id", st.session_state.grupo_id).execute()
                st.session_state.update({"grupo_id": None, "mi_nombre": "", "vista": "inicio"})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.write(f"**Admin:** {admin_nombre}")
            st.write(f"**Frecuencia:** {grupo['frecuencia']}")
            st.write(f"**Inicio:** {grupo['fecha_inicio']}")
