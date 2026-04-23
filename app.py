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
    .info-card { background-color: #f8f9fa; padding: 15px; border-radius: 15px; border-left: 5px solid #1a73e8; margin-bottom: 20px; }
    .status-badge { padding: 2px 8px; border-radius: 5px; font-size: 0.8em; font-weight: bold; }
    .pago-si { background-color: #d4edda; color: #155724; }
    .pago-no { background-color: #fff3cd; color: #856404; }
    .danger-zone { border: 1px solid #ff4b4b; padding: 15px; border-radius: 10px; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤝 PactaLoopa")

# Inicializar estados
if "grupo_id" not in st.session_state:
    st.session_state.update({"grupo_id": None, "vista": "inicio", "mi_nombre": "", "mostrar_exito": False, "nuevo_codigo": ""})

# --- DIÁLOGO DE ÉXITO ---
@st.dialog("🚀 ¡Pacto Creado con Éxito!")
def mostrar_credenciales_nuevas(codigo, password):
    st.write("Comparte estos datos con tu grupo:")
    st.code(f"Código: {codigo}\nContraseña: {password}", language=None)
    if st.button("Entrar al Dashboard"):
        st.session_state.mostrar_exito = False
        st.rerun()

if st.session_state.mostrar_exito:
    mostrar_credenciales_nuevas(st.session_state.nuevo_codigo, st.session_state.nueva_pass)

# --- NAVEGACIÓN ---
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
            st.session_state.update({"grupo_id": gid, "mi_nombre": tu_nombre, "vista": "dashboard", "mostrar_exito": True, "nuevo_codigo": codigo, "nueva_pass": pass_pacto})
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

# --- DASHBOARD ---
elif st.session_state.vista == "dashboard":
    g_res = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
    if not g_res.data: st.session_state.update({"grupo_id": None, "vista": "inicio"}); st.rerun()
    grupo = g_res.data[0]
    p_res = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("posicion_orden").execute()
    participantes = p_res.data
    admin_nombre = participantes[0]['nombre_usuario'] if participantes else ""
    es_admin = (st.session_state.mi_nombre == admin_nombre)
    yo = next((p for p in participantes if p['nombre_usuario'] == st.session_state.mi_nombre), None)

    # Lógica de fechas
    beneficiario = next((p for p in participantes if not p.get('recibio_pozo', False)), None)
    idx_periodo = participantes.index(beneficiario) if beneficiario else 0
    salto = {"semanal": 7, "quincenal": 15, "mensual": 30}.get(grupo['frecuencia'], 30)
    fecha_entrega = date.fromisoformat(grupo['fecha_inicio']) + timedelta(days=idx_periodo * salto)

    with st.sidebar:
        st.write(f"### 🛡️ {grupo['nombre']}")
        st.info(f"Usuario: **{st.session_state.mi_nombre}**")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.update({"grupo_id": None, "mi_nombre": "", "vista": "inicio"})
            st.rerun()

    t1, t2, t3 = st.tabs(["🔄 El Loop", "💰 Mi Pago", "⚙️ Admin" if es_admin else "ℹ️ Info"])

    with t1:
        st.subheader("Estado del Pacto")
        st.markdown(f"""
        <div class="info-card">
            📅 <b>Ciclo:</b> Cada {grupo['frecuencia']}<br>
            👤 <b>Beneficiario actual:</b> {beneficiario['nombre_usuario'] if beneficiario else 'Ciclo finalizado'}<br>
            💰 <b>Pozo estimado:</b> ${grupo['monto_cuota'] * (len(participantes)-1)}<br>
            🗓️ <b>Fecha de entrega:</b> {fecha_entrega.strftime('%d de %B de %Y')}
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
                st.success("¡Este periodo te toca recibir el pozo! No debes pagar cuota.")
            else:
                if yo.get('pago_cuota'):
                    st.success("✅ Tu cuota de este mes ya fue validada.")
                elif yo.get('aviso_pago'):
                    st.warning("🔔 Pago reportado. Esperando validación del administrador.")
                    if st.button("Cancelar Reporte"):
                        supabase.table("participantes").update({"aviso_pago": False}).eq("id", yo['id']).execute()
                        st.rerun()
                else:
                    st.info(f"💵 Monto a pagar: **${grupo['monto_cuota']}**")
                    st.warning(f"⚠️ Fecha límite de pago: **{fecha_entrega.strftime('%d de %B')}**")
                    if st.button("📢 YA DEPOSITÉ MI CUOTA"):
                        supabase.table("participantes").update({"aviso_pago": True}).eq("id", yo['id']).execute()
                        st.rerun()

    with t3:
        if es_admin:
            # Sección Admin (igual que tenías pero bien organizada)
            st.subheader("🔑 Acceso")
            st.write(f"Código: `{grupo['codigo']}` | Pass: `{grupo['password']}`")
            # [Aquí iría el resto de la lógica de admin de tu versión anterior]
            st.subheader("✅ Validar Cuotas")
            for a in [p for p in participantes if p.get('aviso_pago')]:
                if st.button(f"Confirmar pago de {a['nombre_usuario']}"):
                    supabase.table("participantes").update({"aviso_pago": False, "pago_cuota": True}).eq("id", a['id']).execute()
                    st.rerun()
            # ... (Resto de botones de admin)
        else:
            st.subheader("📅 Cronograma del Pacto")
            st.write(f"**Frecuencia:** {grupo['frecuencia'].capitalize()}")
            st.write(f"**Inicio oficial:** {date.fromisoformat(grupo['fecha_inicio']).strftime('%d de %B de %Y')}")
            st.write("El ciclo de pagos se reinicia cada vez que el beneficiario recibe el pozo.")
            st.write(f"**Frecuencia:** {grupo['frecuencia']}")
            st.write(f"**Inicio:** {grupo['fecha_inicio']}")
