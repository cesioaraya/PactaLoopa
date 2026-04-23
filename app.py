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
    .danger-zone { border: 1px solid #ff4b4b; padding: 15px; border-radius: 10px; margin-top: 20px; }
    .code-box { background-color: #f0f2f6; padding: 10px; border-radius: 10px; border: 1px dashed #4e4e4e; }
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
    fecha_inicio = st.date_input("¿Cuándo inicia el primer pago?", value=date.today())
    pass_pacto = st.text_input("Contraseña", type="password")
    tu_nombre = st.text_input("Tu nombre (Admin)").strip()
    
    if st.button("🚀 Crear Pacto"):
        if nombre_pacto and tu_nombre and pass_pacto:
            codigo = generar_codigo()
            res = supabase.table("grupos").insert({
                "nombre": nombre_pacto, 
                "monto_cuota": monto, 
                "frecuencia": frecuencia.lower(), 
                "fecha_inicio": fecha_inicio.isoformat(),
                "codigo": codigo, 
                "password": pass_pacto,
                "abierto": True
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
            supabase.table("participantes").insert({"grupo_id": st.session_state.grupo_id, "nombre_usuario": nuevo, "posicion_orden": max_pos + 1}).execute()
            st.session_state.mi_nombre = nuevo
            st.session_state.vista = "dashboard"; st.rerun()
    elif sel != "-- Seleccionar --":
        if st.button(f"Entrar como {sel}"):
            st.session_state.mi_nombre = sel
            st.session_state.vista = "dashboard"; st.rerun()

# --- DASHBOARD PRINCIPAL ---
elif st.session_state.vista == "dashboard":
    g_res = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
    if not g_res.data:
        st.warning("Este pacto ya no existe.")
        if st.button("Ir al Inicio"):
            st.session_state.update({"grupo_id": None, "mi_nombre": "", "vista": "inicio"})
            st.rerun()
        st.stop()
        
    grupo = g_res.data[0]
    p_res = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("posicion_orden").execute()
    participantes = p_res.data
    
    admin_nombre = supabase.table("participantes").select("nombre_usuario").eq("grupo_id", st.session_state.grupo_id).order("id").limit(1).execute().data[0]['nombre_usuario']
    es_admin = (st.session_state.mi_nombre == admin_nombre)

    f_inicio_pacto = date.fromisoformat(grupo['fecha_inicio'])
    salto = {"semanal": 7, "quincenal": 15, "mensual": 30}[grupo['frecuencia']]
    
    with st.sidebar:
        st.write(f"### 🛡️ {grupo['nombre']}")
        st.info(f"Código: **{grupo['codigo']}**")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.update({"grupo_id": None, "mi_nombre": "", "vista": "inicio"})
            st.rerun()

    t1, t2, t3 = st.tabs(["🔄 El Loop", "💰 Mi Pago", "⚙️ Admin" if es_admin else "ℹ️ Info"])

    with t1:
        st.subheader("Cronograma de Pagos")
        for i, p in enumerate(participantes):
            f_pago = f_inicio_pacto + timedelta(days=i * salto)
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
        st.subheader(f"Estado de {st.session_state.mi_nombre}")
        
        # Lógica de fecha dinámica
        proximo_en_cobrar = next((p for p in participantes if not p['completado']), None)
        if proximo_en_cobrar:
            idx_prox = participantes.index(proximo_en_cobrar)
            fecha_prox = f_inicio_pacto + timedelta(days=idx_prox * salto)
            dias_restantes = (fecha_prox - date.today()).days
            
            st.markdown(f"⏳ El grupo espera el pago en: <span class='days-badge'>{max(0, dias_restantes)} días</span>", unsafe_allow_html=True)
            st.caption(f"Fecha estimada: **{fecha_prox.strftime('%d de %B')}**")
            
        st.write("---")
        if not yo['completado']:
            if yo['aviso_pago']:
                st.warning("Pago reportado. Esperando validación.")
                if st.button("❌ Cancelar reporte"):
                    supabase.table("participantes").update({"aviso_pago": False}).eq("id", yo['id']).execute()
                    st.rerun()
            else:
                st.info(f"Monto a pagar: **${grupo['monto_cuota']}**")
                if st.button("📢 REPORTAR PAGO"):
                    supabase.table("participantes").update({"aviso_pago": True}).eq("id", yo['id']).execute()
                    st.rerun()
        else:
            st.success("✅ Ciclo completado. Ya recibiste tu pozo.")

    if es_admin:
        with t3:
            st.subheader("🔑 Acceso para Miembros")
            col_cod1, col_cod2 = st.columns(2)
            with col_cod1:
                st.code(grupo['codigo'], language=None)
                st.caption("Código de Grupo")
            with col_cod2:
                st.code(grupo['password'], language=None)
                st.caption("Contraseña")
            
            st.write("---")
            st.subheader("Control del Ciclo")
            if st.button("♻️ LIMPIAR TABLERO (Nuevo Ciclo)"):
                supabase.table("participantes").update({"completado": False, "aviso_pago": False}).eq("grupo_id", st.session_state.grupo_id).execute()
                supabase.table("grupos").update({"fecha_inicio": date.today().isoformat()}).eq("id", st.session_state.grupo_id).execute()
                st.rerun()

            st.write("---")
            estado_insc = "Abiertas" if grupo['abierto'] else "Cerradas"
            if st.button(f"🚪 {'Cerrar' if grupo['abierto'] else 'Abrir'} Inscripciones (Ahora: {estado_insc})"):
                supabase.table("grupos").update({"abierto": not grupo['abierto']}).eq("id", st.session_state.grupo_id).execute()
                st.rerun()

            st.write("---")
            st.subheader("Validar Pagos")
            avisos = [p for p in participantes if p['aviso_pago']]
            if not avisos: st.caption("Sin reportes pendientes.")
            for a in avisos:
                if st.button(f"Validar a {a['nombre_usuario']} ✅"):
                    supabase.table("participantes").update({"completado": True, "aviso_pago": False}).eq("id", a['id']).execute()
                    st.rerun()
            
            st.write("---")
            st.subheader("Organizar Loop")
            pendientes = [p for p in participantes if not p['completado']]
            if len(pendientes) > 1:
                nombres_p = [p['nombre_usuario'] for p in pendientes]
                nuevo_orden = st.multiselect("Reordenar los que faltan:", nombres_p, default=nombres_p)
                if st.button("💾 Guardar Orden"):
                    completados = [p for p in participantes if p['completado']]
                    final = completados + [next(p for p in pendientes if p['nombre_usuario'] == n) for n in nuevo_orden]
                    for idx, p in enumerate(final):
                        supabase.table("participantes").update({"posicion_orden": idx}).eq("id", p['id']).execute()
                    st.rerun()

            st.write("---")
            st.subheader("Eliminar Miembros")
            opciones_eliminar = [p['nombre_usuario'] for p in participantes if not p['completado'] and p['nombre_usuario'] != admin_nombre]
            if opciones_eliminar:
                u_elim = st.selectbox("Seleccionar miembro:", opciones_eliminar)
                if st.button("🗑️ Eliminar Miembro Seleccionado"):
                    supabase.table("participantes").delete().eq("grupo_id", st.session_state.grupo_id).eq("nombre_usuario", u_elim).execute()
                    st.rerun()

            st.write("---")
            st.markdown('<div class="danger-zone">', unsafe_allow_html=True)
            st.subheader("☢️ Zona Peligrosa")
            if st.button("🔥 ELIMINAR TODO ESTE PACTO"):
                supabase.table("participantes").delete().eq("grupo_id", st.session_state.grupo_id).execute()
                supabase.table("grupos").delete().eq("id", st.session_state.grupo_id).execute()
                st.session_state.update({"grupo_id": None, "mi_nombre": "", "vista": "inicio"})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    else:
        with t3:
            st.write(f"**Administrador:** {admin_nombre}")
            st.write(f"**Frecuencia:** {grupo['frecuencia'].capitalize()}")
            st.write(f"**Inicio actual:** {f_inicio_pacto.strftime('%d %b %Y')}")
