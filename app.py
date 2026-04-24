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

def calcular_fecha_periodo(fecha_inicio, indice, frecuencia):
    """Calcula la fecha exacta del periodo ajustándose a meses si es mensual."""
    if frecuencia == "mensual":
        # Lógica para mantener el mismo día del mes
        meses = (fecha_inicio.month + indice - 1) % 12 + 1
        anios = fecha_inicio.year + (fecha_inicio.month + indice - 1) // 12
        # Intentamos mantener el día, si el mes tiene menos días (ej. 31 de feb), ajusta al último día
        dia = fecha_inicio.day
        try:
            return date(anios, meses, dia)
        except ValueError:
            # Caso 31 de febrero -> devuelve 28 o 29 de febrero
            import calendar
            ultimo_dia = calendar.monthrange(anios, meses)[1]
            return date(anios, meses, ultimo_dia)
    elif frecuencia == "quincenal":
        return fecha_inicio + timedelta(days=indice * 15)
    else:  # semanal
        return fecha_inicio + timedelta(days=indice * 7)

# 3. ESTILO
st.markdown("""
    <style>
    .stButton>button { border-radius: 20px; width: 100%; }
    .info-card { background-color: #f8f9fa; padding: 15px; border-radius: 15px; border-left: 5px solid #1a73e8; margin-bottom: 20px; }
    .status-badge { padding: 2px 8px; border-radius: 5px; font-size: 0.8em; font-weight: bold; }
    .pago-si { background-color: #d4edda; color: #155724; }
    .pago-no { background-color: #fff3cd; color: #856404; }
    .danger-zone { border: 1px solid #ff4b4b; padding: 15px; border-radius: 10px; margin-top: 20px; }
    [data-testid="stSidebarNav"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

st.title("🤝 PactaLoopa")

# Inicializar estados
if "grupo_id" not in st.session_state:
    st.session_state.update({"grupo_id": None, "vista": "inicio", "mi_nombre": "", "mostrar_exito": False, "nuevo_codigo": "", "periodo_seleccionado": 0})

# --- DIÁLOGO DE ÉXITO ---
@st.dialog("🚀 ¡Pacto Creado con Éxito!")
def mostrar_credenciales_nuevas(codigo, password):
    st.write("Comparte estos datos con tu grupo:")
    st.code(f"Código: {codigo}", language=None)
    st.write("Solo tú (Admin) necesitas la contraseña para gestionar el grupo.")
    st.code(f"Contraseña Admin: {password}", language=None)
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
    pass_pacto = st.text_input("Contraseña del administrador", type="password")
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
    c_in = st.text_input("Código de Grupo").upper().strip()
    p_in = st.text_input("Contraseña (Solo si eres el Admin)", type="password", help="Los miembros normales dejen este campo vacío")
    
    if st.button("Entrar"):
        query = supabase.table("grupos").select("*").eq("codigo", c_in)
        if p_in: # Si intenta entrar como admin
            query = query.eq("password", p_in)
        
        g = query.execute()
        if g.data:
            st.session_state.grupo_id = g.data[0]['id']
            st.session_state.vista = "seleccionar_usuario"; st.rerun()
        else:
            st.error("Código incorrecto o contraseña de admin inválida.")

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

    f_inicio_dt = date.fromisoformat(grupo['fecha_inicio'])
    
    with st.sidebar:
        st.write(f"### 🛡️ {grupo['nombre']}")
        st.info(f"Usuario: **{st.session_state.mi_nombre}**")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.update({"grupo_id": None, "mi_nombre": "", "vista": "inicio"})
            st.rerun()
        
        st.divider()
        st.write("📅 **Periodos del Loop**")
        for i, p in enumerate(participantes):
            f_p = calcular_fecha_periodo(f_inicio_dt, i, grupo['frecuencia'])
            label = f"P{i+1}: {p['nombre_usuario']} ({f_p.strftime('%d/%m')})"
            if st.button(label, key=f"per_{i}"):
                st.session_state.periodo_seleccionado = i
        
    # El periodo visualizado depende de la selección del sidebar
    idx_p = st.session_state.periodo_seleccionado
    beneficiario_p = participantes[idx_p] if idx_p < len(participantes) else participantes[0]
    fecha_p = calcular_fecha_periodo(f_inicio_dt, idx_p, grupo['frecuencia'])

    t1, t2, t3 = st.tabs(["🔄 El Loop", "💰 Reportar Pago", "⚙️ Admin" if es_admin else "ℹ️ Info"])

    with t1:
        st.subheader(f"Periodo {idx_p + 1}")
        st.markdown(f"""
        <div class="info-card">
            👤 <b>Recibe Pozo:</b> {beneficiario_p['nombre_usuario']}<br>
            🗓️ <b>Fecha Estimada:</b> {fecha_p.strftime('%d de %B de %Y')}<br>
            💰 <b>Monto Pozo:</b> ${grupo['monto_cuota'] * (len(participantes)-1)}
        </div>
        """, unsafe_allow_html=True)
        
        for p in participantes:
            col_u, col_p = st.columns([2, 1])
            with col_u: st.write(f"{'🎁 ' if p == beneficiario_p else '👤 '}{p['nombre_usuario']}")
            with col_p:
                if p == beneficiario_p: st.caption("Beneficiario")
                else:
                    status = "PAGADO" if p.get('pago_cuota') else "PENDIENTE"
                    clase = "pago-si" if p.get('pago_cuota') else "pago-no"
                    st.markdown(f"<span class='status-badge {clase}'>{status}</span>", unsafe_allow_html=True)

    with t2:
        st.subheader(f"Tu pago para el Periodo {idx_p + 1}")
        if yo:
            if yo['nombre_usuario'] == beneficiario_p['nombre_usuario']:
                st.success("En este periodo tú recibes el pozo. No debes reportar pago.")
            else:
                if yo.get('pago_cuota'):
                    st.success("✅ Tu cuota ya está marcada como pagada.")
                elif yo.get('aviso_pago'):
                    st.warning("🔔 Pago reportado. Esperando validación.")
                    if st.button("Cancelar Reporte"):
                        supabase.table("participantes").update({"aviso_pago": False}).eq("id", yo['id']).execute()
                        st.rerun()
                else:
                    st.info(f"Monto: **${grupo['monto_cuota']}**")
                    if st.button("📢 INFORMAR QUE YA PAGUÉ"):
                        supabase.table("participantes").update({"aviso_pago": True}).eq("id", yo['id']).execute()
                        st.rerun()

    with t3:
        if es_admin:
            st.subheader("Gestión de Miembros")
            st.write("---")
            st.write("📋 **Cambiar orden (solo quienes no han recibido pozo)**")
            pendientes = [p for p in participantes if not p.get('recibio_pozo')]
            if len(pendientes) > 1:
                m1 = st.selectbox("Mover a:", [p['nombre_usuario'] for p in pendientes], key="m1")
                pos_nueva = st.number_input("A la posición (0 es primero):", 0, len(participantes)-1, 0)
                if st.button("Cambiar Posición"):
                    p_obj = next(p for p in participantes if p['nombre_usuario'] == m1)
                    supabase.table("participantes").update({"posicion_orden": pos_nueva}).eq("id", p_obj['id']).execute()
                    st.rerun()

            st.write("---")
            st.write("❌ **Eliminar Miembro**")
            to_del = st.selectbox("Seleccionar para eliminar:", [p['nombre_usuario'] for p in participantes if p['nombre_usuario'] != st.session_state.mi_nombre])
            if st.button("Eliminar permanentemente"):
                p_del = next(p for p in participantes if p['nombre_usuario'] == to_del)
                supabase.table("participantes").delete().eq("id", p_del['id']).execute()
                st.rerun()

            st.write("---")
            st.subheader("✅ Validar Cuotas Reportadas")
            avisos = [p for p in participantes if p.get('aviso_pago')]
            if avisos:
                for a in avisos:
                    if st.button(f"Confirmar pago de {a['nombre_usuario']}"):
                        supabase.table("participantes").update({"aviso_pago": False, "pago_cuota": True}).eq("id", a['id']).execute()
                        st.rerun()
            else: st.caption("No hay pagos pendientes de validación.")

            st.markdown('<div class="danger-zone">', unsafe_allow_html=True)
            st.subheader("🗑️ Zona de Peligro")
            if st.button("ELIMINAR TODO EL LOOP"):
                supabase.table("participantes").delete().eq("grupo_id", st.session_state.grupo_id).execute()
                supabase.table("grupos").delete().eq("id", st.session_state.grupo_id).execute()
                st.session_state.update({"grupo_id": None, "vista": "inicio"})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.subheader("ℹ️ Información del Pacto")
            st.write(f"**Código:** {grupo['codigo']}")
            st.write(f"**Frecuencia:** {grupo['frecuencia'].capitalize()}")
            st.write(f"**Inicio:** {grupo['fecha_inicio']}")
