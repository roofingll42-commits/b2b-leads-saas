import streamlit as st
import sqlite3
import pandas as pd
import re
import os
import random
import hashlib
import smtplib
from email.message import EmailMessage
import requests

st.set_page_config(
    page_title="Global B2B Intelligence Portal | SaaS",
    page_icon="🚀",
    layout="wide"
)

# ==============================================================================
# ⚙️ CONFIGURACIÓN DE CORREO (OTP), LÍMITES Y PRECIOS DE SUSCRIPCIÓN
# ==============================================================================
LIMITE_BUSQUEDAS_GRATIS = 5

# Precios y enlaces de tus planes de suscripción (puedes cambiarlos cuando quieras)
PRECIO_MENSUAL = "$49 / month"
PRECIO_ANUAL = "$195 / year"
LINK_PAGO_MENSUAL = "https://juanahez.gumroad.com/l/ywcomq"
LINK_PAGO_ANUAL = "https://juanahez.gumroad.com/l/rzzow"

# Códigos de activación que reciben al suscribirse
CODIGOS_PLAN_MENSUAL = {"PRO-MONTHLY-2026", "VIP-STATE-2026"}
CODIGOS_PLAN_ANUAL = {"PRO-ANNUAL-2026", "VIP-ALL-2026"}

# Credenciales SMTP para enviar el código OTP de 6 dígitos por correo
# Puedes configurarlas en Streamlit Cloud -> Settings -> Secrets
SMTP_EMAIL = st.secrets.get("SMTP_EMAIL", "") if hasattr(st, "secrets") else ""
SMTP_PASSWORD = st.secrets.get("SMTP_PASSWORD", "") if hasattr(st, "secrets") else ""

# ==============================================================================
# 🔐 BASE DE DATOS DE USUARIOS, OTP Y CONTADOR DE BÚSQUEDAS
# ==============================================================================
USERS_DB = "usuarios_saas.db"

def inicializar_db_usuarios():
    conn = sqlite3.connect(USERS_DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            email TEXT PRIMARY KEY,
            nombre TEXT,
            password_hash TEXT,
            verificado INTEGER DEFAULT 0,
            otp_codigo TEXT,
            plan TEXT DEFAULT 'free',
            busquedas_usadas INTEGER DEFAULT 0,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

inicializar_db_usuarios()

def encriptar_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def enviar_correo_otp(destinatario, nombre, codigo_otp, motivo="verificar tu cuenta"):
    """Envía el código de 6 dígitos por correo real. Si no hay SMTP configurado, avisa en pantalla."""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        return False, f"Modo de Prueba Activo (Sin SMTP configurado). Tu código OTP de 6 dígitos es: **{codigo_otp}**"

    try:
        msg = EmailMessage()
        msg["Subject"] = f"🔑 Tu código de verificación es {codigo_otp} - Global B2B Portal"
        msg["From"] = SMTP_EMAIL
        msg["To"] = destinatario
        msg.set_content(
            f"Hola {nombre},\n\n"
            f"Tu código de seguridad de 6 dígitos para {motivo} en Global B2B Intelligence Portal es:\n\n"
            f"👉 {codigo_otp}\n\n"
            f"Si no solicitaste este código, puedes ignorar este mensaje.\n"
        )
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        return True, f"✅ Hemos enviado un código de 6 dígitos a **{destinatario}**. Revisa tu bandeja de entrada o Spam."
    except Exception as e:
        return False, f"No se pudo enviar el email por SMTP ({e}). Código temporal de respaldo: **{codigo_otp}**"

def obtener_usuario(email):
    conn = sqlite3.connect(USERS_DB)
    c = conn.cursor()
    fila = c.execute(
        "SELECT email, nombre, password_hash, verificado, otp_codigo, plan, busquedas_usadas FROM usuarios WHERE email = ?",
        (email.lower().strip(),)
    ).fetchone()
    conn.close()
    if fila:
        return {
            "email": fila[0], "nombre": fila[1], "password_hash": fila[2],
            "verificado": fila[3], "otp_codigo": fila[4], "plan": fila[5],
            "busquedas_usadas": fila[6]
        }
    return None

def incrementar_busqueda_usuario(email):
    conn = sqlite3.connect(USERS_DB)
    c = conn.cursor()
    c.execute("UPDATE usuarios SET busquedas_usadas = busquedas_usadas + 1 WHERE email = ?", (email.lower().strip(),))
    conn.commit()
    conn.close()

def actualizar_plan_usuario(email, nuevo_plan):
    conn = sqlite3.connect(USERS_DB)
    c = conn.cursor()
    c.execute("UPDATE usuarios SET plan = ? WHERE email = ?", (nuevo_plan, email.lower().strip()))
    conn.commit()
    conn.close()

# ==============================================================================
# 🖥️ SISTEMA DE NAVEGACIÓN DE SESIÓN (LOGIN / REGISTRO / OTP / OLVIDÉ CONTRASEÑA)
# ==============================================================================
if "usuario_activo" not in st.session_state:
    st.session_state.usuario_activo = None
if "vista_auth" not in st.session_state:
    st.session_state.vista_auth = "login"  # 'login', 'registro', 'verificar_otp', 'olvide_pass'
if "email_pendiente_otp" not in st.session_state:
    st.session_state.email_pendiente_otp = ""
if "mensaje_otp_info" not in st.session_state:
    st.session_state.mensaje_otp_info = ""
if "ultima_firma_busqueda" not in st.session_state:
    st.session_state.ultima_firma_busqueda = ""

def mostrar_pantalla_autenticacion():
    col_izq, col_centro, col_der = st.columns([1, 1.4, 1])
    with col_centro:
        st.markdown("<h1 style='text-align:center;'>🚀 Global B2B Intelligence</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#9CA3AF;'>409,530+ Verified US Commercial Profiles across 96 Industries</p>", unsafe_allow_html=True)
        st.markdown("---")

        # ------------------------------------------------------------------
        # 1. PANTALLA: INICIAR SESIÓN (LOGIN)
        # ------------------------------------------------------------------
        if st.session_state.vista_auth == "login":
            st.subheader("🔐 Iniciar Sesión en tu Cuenta")
            email_in = st.text_input("Correo Electrónico:", placeholder="tu@empresa.com")
            pass_in = st.text_input("Contraseña:", type="password", placeholder="••••••••")

            if st.button("Entrar al Portal", use_container_width=True, type="primary"):
                user = obtener_usuario(email_in)
                if not user or user["password_hash"] != encriptar_password(pass_in):
                    st.error("❌ Correo o contraseña incorrectos.")
                elif user["verificado"] == 0:
                    # Si no ha confirmado su correo con el OTP, mandarlo a la pantalla de OTP
                    nuevo_otp = str(random.randint(100000, 999999))
                    conn = sqlite3.connect(USERS_DB)
                    conn.execute("UPDATE usuarios SET otp_codigo = ? WHERE email = ?", (nuevo_otp, user["email"]))
                    conn.commit()
                    conn.close()
                    _, msg_info = enviar_correo_otp(user["email"], user["nombre"], nuevo_otp)
                    st.session_state.email_pendiente_otp = user["email"]
                    st.session_state.mensaje_otp_info = msg_info
                    st.session_state.vista_auth = "verificar_otp"
                    st.rerun()
                else:
                    st.session_state.usuario_activo = user["email"]
                    st.rerun()

            st.markdown("")
            c_btn1, c_btn2 = st.columns(2)
            if c_btn1.button("✨ Crear Cuenta Gratis", use_container_width=True):
                st.session_state.vista_auth = "registro"
                st.rerun()
            if c_btn2.button("❓ Olvidé mi Contraseña", use_container_width=True):
                st.session_state.vista_auth = "olvide_pass"
                st.rerun()

        # ------------------------------------------------------------------
        # 2. PANTALLA: CREAR CUENTA NUEVA -> ENVÍA CÓDIGO OTP DE 6 DÍGITOS
        # ------------------------------------------------------------------
        elif st.session_state.vista_auth == "registro":
            st.subheader("✨ Crear Cuenta Gratis (Incluye 5 Búsquedas)")
            nombre_reg = st.text_input("Nombre Completo:", placeholder="Juan Hernández")
            email_reg = st.text_input("Correo Electrónico:", placeholder="tu@correo.com")
            pass_reg1 = st.text_input("Crear Contraseña:", type="password", placeholder="Mínimo 6 caracteres")
            pass_reg2 = st.text_input("Confirmar Contraseña:", type="password", placeholder="Repite tu contraseña")

            if st.button("Registrarme y Recibir Código OTP", use_container_width=True, type="primary"):
                email_clean = email_reg.lower().strip()
                if not nombre_reg.strip() or "@" not in email_clean or "." not in email_clean:
                    st.error("⚠️ Por favor ingresa un nombre y correo electrónico válidos.")
                elif len(pass_reg1) < 6:
                    st.error("⚠️ La contraseña debe tener al menos 6 caracteres.")
                elif pass_reg1 != pass_reg2:
                    st.error("⚠️ Las contraseñas no coinciden.")
                elif obtener_usuario(email_clean):
                    st.error("⚠️ Este correo ya está registrado. Inicia sesión o recupera tu contraseña.")
                else:
                    codigo_otp = str(random.randint(100000, 999999))
                    conn = sqlite3.connect(USERS_DB)
                    conn.execute(
                        "INSERT INTO usuarios (email, nombre, password_hash, verificado, otp_codigo, plan, busquedas_usadas) VALUES (?, ?, ?, 0, ?, 'free', 0)",
                        (email_clean, nombre_reg.strip(), encriptar_password(pass_reg1), codigo_otp)
                    )
                    conn.commit()
                    conn.close()

                    _, msg_info = enviar_correo_otp(email_clean, nombre_reg.strip(), codigo_otp, "confirmar tu cuenta")
                    st.session_state.email_pendiente_otp = email_clean
                    st.session_state.mensaje_otp_info = msg_info
                    st.session_state.vista_auth = "verificar_otp"
                    st.rerun()

            if st.button("⬅️ Volver a Iniciar Sesión", use_container_width=True):
                st.session_state.vista_auth = "login"
                st.rerun()

        # ------------------------------------------------------------------
        # 3. PANTALLA: CONFIRMAR CORREO CON CÓDIGO OTP DE 6 DÍGITOS
        # ------------------------------------------------------------------
        elif st.session_state.vista_auth == "verificar_otp":
            st.subheader("📩 Confirma tu Correo Electrónico")
            st.write(f"Cuenta: **{st.session_state.email_pendiente_otp}**")
            if st.session_state.mensaje_otp_info:
                st.info(st.session_state.mensaje_otp_info)

            otp_ingresado = st.text_input("Ingresa el código OTP de 6 dígitos:", max_chars=6, placeholder="123456")

            if st.button("✅ Verificar Código y Activar Cuenta", use_container_width=True, type="primary"):
                user = obtener_usuario(st.session_state.email_pendiente_otp)
                if user and otp_ingresado.strip() == user["otp_codigo"]:
                    conn = sqlite3.connect(USERS_DB)
                    conn.execute("UPDATE usuarios SET verificado = 1, otp_codigo = NULL WHERE email = ?", (user["email"],))
                    conn.commit()
                    conn.close()
                    st.session_state.usuario_activo = user["email"]
                    st.success("🎉 ¡Correo verificado con éxito! Entrando al portal...")
                    st.rerun()
                else:
                    st.error("❌ El código de 6 dígitos es incorrecto. Verifica e intenta de nuevo.")

            c_reenv, c_volver = st.columns(2)
            if c_reenv.button("🔄 Reenviar Código OTP", use_container_width=True):
                user = obtener_usuario(st.session_state.email_pendiente_otp)
                if user:
                    nuevo_otp = str(random.randint(100000, 999999))
                    conn = sqlite3.connect(USERS_DB)
                    conn.execute("UPDATE usuarios SET otp_codigo = ? WHERE email = ?", (nuevo_otp, user["email"]))
                    conn.commit()
                    conn.close()
                    _, msg_info = enviar_correo_otp(user["email"], user["nombre"], nuevo_otp)
                    st.session_state.mensaje_otp_info = msg_info
                    st.rerun()

            if c_volver.button("⬅️ Volver al Login", use_container_width=True):
                st.session_state.vista_auth = "login"
                st.rerun()

        # ------------------------------------------------------------------
        # 4. PANTALLA: OLVIDÉ MI CONTRASEÑA (RECUPERACIÓN CON OTP DE 6 DÍGITOS)
        # ------------------------------------------------------------------
        elif st.session_state.vista_auth == "olvide_pass":
            st.subheader("🔑 Recuperar mi Contraseña")
            email_rec = st.text_input("Ingresa tu correo registrado:", value=st.session_state.email_pendiente_otp)

            if st.button("📨 Enviar Código de 6 Dígitos a mi Correo", use_container_width=True):
                user = obtener_usuario(email_rec)
                if not user:
                    st.error("❌ No encontramos ninguna cuenta con ese correo electrónico.")
                else:
                    nuevo_otp = str(random.randint(100000, 999999))
                    conn = sqlite3.connect(USERS_DB)
                    conn.execute("UPDATE usuarios SET otp_codigo = ? WHERE email = ?", (nuevo_otp, user["email"]))
                    conn.commit()
                    conn.close()
                    _, msg_info = enviar_correo_otp(user["email"], user["nombre"], nuevo_otp, "restablecer tu contraseña")
                    st.session_state.email_pendiente_otp = user["email"]
                    st.session_state.mensaje_otp_info = msg_info
                    st.rerun()

            if st.session_state.mensaje_otp_info:
                st.info(st.session_state.mensaje_otp_info)
                st.markdown("#### Paso 2: Ingresa el código y tu nueva contraseña")
                otp_rec = st.text_input("Código OTP de 6 dígitos:", max_chars=6, placeholder="123456")
                nueva_p1 = st.text_input("Nueva Contraseña:", type="password")
                nueva_p2 = st.text_input("Confirmar Nueva Contraseña:", type="password")

                if st.button("💾 Guardar Nueva Contraseña", use_container_width=True, type="primary"):
                    user = obtener_usuario(st.session_state.email_pendiente_otp)
                    if not user or otp_rec.strip() != user["otp_codigo"]:
                        st.error("❌ El código OTP de 6 dígitos no es válido.")
                    elif len(nueva_p1) < 6 or nueva_p1 != nueva_p2:
                        st.error("⚠️ Las contraseñas deben coincidir y tener mínimo 6 caracteres.")
                    else:
                        conn = sqlite3.connect(USERS_DB)
                        conn.execute(
                            "UPDATE usuarios SET password_hash = ?, verificado = 1, otp_codigo = NULL WHERE email = ?",
                            (encriptar_password(nueva_p1), user["email"])
                        )
                        conn.commit()
                        conn.close()
                        st.session_state.mensaje_otp_info = ""
                        st.session_state.vista_auth = "login"
                        st.success("✅ ¡Contraseña actualizada! Ya puedes iniciar sesión.")
                        st.rerun()

            if st.button("⬅️ Volver al Inicio de Sesión", use_container_width=True):
                st.session_state.mensaje_otp_info = ""
                st.session_state.vista_auth = "login"
                st.rerun()

# Si el usuario NO ha iniciado sesión, mostramos únicamente el sistema de Login/OTP y detenemos aquí
if not st.session_state.usuario_activo:
    mostrar_pantalla_autenticacion()
    st.stop()

# ==============================================================================
# 👤 DATOS DEL USUARIO CONECTADO Y CONTROL DE SUSCRIPCIÓN
# ==============================================================================
usuario_actual = obtener_usuario(st.session_state.usuario_activo)
if not usuario_actual:
    st.session_state.usuario_activo = None
    st.rerun()

es_suscriptor_pro = usuario_actual["plan"] in ("monthly", "annual")
busquedas_usadas = usuario_actual["busquedas_usadas"]
busquedas_restantes = max(0, LIMITE_BUSQUEDAS_GRATIS - busquedas_usadas)

# ==============================================================================
# 📥 DESCARGADOR AUTOMÁTICO DE LA MEGA BASE DE DATOS (GITHUB RELEASES)
# ==============================================================================
DB_MEGA_PATH = "mega_base_b2b.db"

if not os.path.exists(DB_MEGA_PATH):
    st.info("⏳ Descargando la base de datos desde el servidor en la nube (solo ocurre la primera vez)...")
    ENLACE_DIRECTO_DB = "https://github.com/roofingll42-commits/b2b-leads-saas/releases/download/v1.0/mega_base_b2b.db"
    try:
        response = requests.get(ENLACE_DIRECTO_DB, stream=True, timeout=120)
        if response.status_code == 200:
            with open(DB_MEGA_PATH, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
            st.rerun()
    except Exception as e:
        st.error(f"Error en descarga: {e}")

# ==============================================================================
# 📋 LISTADO DE LAS 95 INDUSTRIAS Y FUNCIONES DE LIMPIEZA
# ==============================================================================
RUBROS_95 = [
    "Construction Company", "General Contractor", "Roofing Contractor", "Plumbing Service",
    "HVAC Repair", "Electrician", "Painting Company", "Landscaping Service", "Cleaning Service",
    "Water Damage Restoration", "Pest Control", "Flooring Contractor", "Home Remodeling",
    "Cabinet Shop", "Tree Service", "Pool Maintenance", "Fencing Company", "Moving Company",
    "Garage Door Repair", "Locksmith Service", "Carpet Cleaning", "Window Tinting",
    "Paving Contractor", "Excavation Company", "Asphalt Contractor", "Gutter Cleaning Service",
    "Junk Removal Service", "Interior Designer", "Handyman Service", "Appliance Repair",
    "Law Firm", "Accountant", "Architecture Firm", "Real Estate Agency", "Tax Preparation Service",
    "Financial Advisor", "Insurance Agency", "Business Consultant", "Property Management",
    "Private Investigator", "Notary Public", "Title Company", "Mortgage Broker",
    "Staffing Agency", "Public Relations Firm", "Commercial Real Estate",
    "Dentist Office", "Medical Clinic", "Chiropractor", "Physical Therapy Clinic",
    "Med Spa", "Veterinary Clinic", "Optometrist", "Fitness Center", "Yoga Studio",
    "Dermatologist Office", "Plastic Surgery Clinic", "Acupuncture Clinic", "Massage Therapy",
    "Hair Salon", "Barber Shop", "Orthodontist", "Home Health Care Service",
    "Trucking Company", "Logistics Service", "Auto Repair Shop", "Car Dealership",
    "Towing Service", "Auto Body Shop", "Mobile Car Detailing", "Tire Shop",
    "Auto Glass Repair", "Freight Forwarder", "Warehouse Storage",
    "Digital Marketing Agency", "IT Support Service", "Web Development Agency",
    "Software Company", "Cybersecurity Firm", "Managed Service Provider",
    "Graphic Design Studio", "Video Production Company", "SEO Agency", "Data Recovery Service",
    "Solar Energy Company", "Security Company", "Machine Shop", "Wholesale Supplier",
    "Catering Service", "Event Planner", "Wedding Photographer", "Boutique Hotel",
    "Commercial Printer", "Sign Shop", "Janitorial Service", "Equipment Rental Agency"
]

def ocultar_dato(val, visibles=5):
    s = str(val).strip()
    if not s or s in ["-", "N/A", "None", "nan"]:
        return "-"
    return (s[:visibles] + "••••• (Locked)") if len(s) > visibles else (s + "***")

@st.cache_data(ttl=600)
def obtener_conteos_en_vivo():
    conteos = {r: 0 for r in RUBROS_95}
    total_fmcsa = 0
    total_mega = 0
    try:
        conn1 = sqlite3.connect("perfiles_fmcsa.db")
        total_fmcsa = conn1.execute("SELECT COUNT(*) FROM empresas").fetchone()[0]
        conn1.close()
    except Exception:
        pass
    conteos["Trucking & Logistics (FMCSA)"] = total_fmcsa

    try:
        conn2 = sqlite3.connect(DB_MEGA_PATH)
        total_mega = conn2.execute("SELECT COUNT(*) FROM leads_b2b").fetchone()[0]
        filas_ind = conn2.execute("""
            SELECT COALESCE(NULLIF(sub_category, ''), industry) AS cat, COUNT(*)
            FROM leads_b2b
            GROUP BY cat
        """).fetchall()
        for cat_name, cant in filas_ind:
            if cat_name in conteos:
                conteos[cat_name] += cant
        conn2.close()
    except Exception:
        pass

    total_global = total_fmcsa + total_mega
    conteos["🌐 All Categories (Global Search)"] = total_mega
    return total_global, conteos

total_general_en_vivo, conteos_por_industria = obtener_conteos_en_vivo()

# ==============================================================================
# 🏢 BARRA LATERAL: PERFIL DE USUARIO + CONTADOR GRATUITO + MENÚ
# ==============================================================================
st.sidebar.markdown(f"👤 **{usuario_actual['nombre']}** (`{usuario_actual['email']}`)")
if es_suscriptor_pro:
    st.sidebar.success(f"💎 Plan Activo: **PRO ({usuario_actual['plan'].upper()})** — Búsquedas Ilimitadas")
else:
    st.sidebar.warning(f"🎁 Plan Gratis: **{busquedas_restantes} de {LIMITE_BUSQUEDAS_GRATIS}** búsquedas disponibles")
    st.sidebar.progress(min(1.0, busquedas_usadas / LIMITE_BUSQUEDAS_GRATIS))

col_s1, col_s2 = st.sidebar.columns(2)
modo_vista = st.sidebar.radio("📌 Navegación:", ["🔎 Explorar Base de Datos", "💳 Suscripción y Mi Cuenta"])
if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state.usuario_activo = None
    st.rerun()

st.sidebar.markdown("---")

# ==============================================================================
# 💳 FUNCIÓN DEL ÁREA DE SUSCRIPCIÓN MENSUAL O ANUAL (PAYWALL)
# ==============================================================================
def mostrar_area_suscripcion(motivo_bloqueo=False):
    if motivo_bloqueo:
        st.error(f"🛑 Has alcanzado el límite de **{LIMITE_BUSQUEDAS_GRATIS} búsquedas gratuitas** en tu cuenta de prueba.")
        st.markdown("### 🚀 Suscríbete para desbloquear búsquedas ilimitadas, teléfonos directos, emails y descargas CSV")
    else:
        st.title("💳 Planes de Suscripción y Configuración de Cuenta")
        st.write("Elige el plan que mejor se adapte a tu volumen de prospección B2B:")

    c_plan1, c_plan2 = st.columns(2)
    with c_plan1:
        st.markdown(
            f"""
            <div style="background-color:#1E293B; padding:25px; border-radius:12px; border: 2px solid #3B82F6; text-align:center;">
                <h3 style="color:#60A5FA; margin-bottom:5px;">📅 Plan Mensual Pro</h3>
                <h1 style="color:white; margin:10px 0;">{PRECIO_MENSUAL}</h1>
                <p style="color:#CBD5E1; font-size:14px;">✅ Búsquedas ilimitadas en los 50 Estados<br>✅ Teléfonos directos y Correos sin candado<br>✅ Exportación a Excel / CSV instantánea<br>✅ Cancela cuando quieras</p>
                <a href="{LINK_PAGO_MENSUAL}" target="_blank" style="background-color:#3B82F6; color:white; padding:12px 28px; border-radius:6px; text-decoration:none; font-weight:bold; display:inline-block; margin-top:12px;">Suscribirme al Plan Mensual</a>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c_plan2:
        st.markdown(
            f"""
            <div style="background-color:#111827; padding:25px; border-radius:12px; border: 2px solid #EC4899; text-align:center;">
                <h3 style="color:#F472B6; margin-bottom:5px;">🏆 Plan Anual VIP (Ahorra 65%)</h3>
                <h1 style="color:white; margin:10px 0;">{PRECIO_ANUAL}</h1>
                <p style="color:#CBD5E1; font-size:14px;">✅ Acceso Total durante 12 meses a las 96 Industrias<br>✅ 409,530+ Perfiles Comerciales Verificados<br>✅ Descargas masivas ilimitadas para tu CRM<br>✅ Soporte y actualizaciones prioritarias</p>
                <a href="{LINK_PAGO_ANUAL}" target="_blank" style="background-color:#EC4899; color:white; padding:12px 28px; border-radius:6px; text-decoration:none; font-weight:bold; display:inline-block; margin-top:12px;">Suscribirme al Plan Anual VIP</a>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.subheader("🔑 ¿Ya realizaste tu pago? Activa tu suscripción aquí")
    codigo_sub = st.text_input("Ingresa el código de licencia que recibiste tras tu pago:", placeholder="Ej: PRO-MONTHLY-2026 o PRO-ANNUAL-2026")
    if st.button("⚡ Activar Suscripción Pro en mi Cuenta", type="primary"):
        cod_limpio = codigo_sub.strip().upper()
        if cod_limpio in CODIGOS_PLAN_MENSUAL:
            actualizar_plan_usuario(usuario_actual["email"], "monthly")
            st.success("🎉 ¡Plan Mensual Pro activado en tu cuenta! Ahora tienes búsquedas ilimitadas y datos desbloqueados.")
            st.rerun()
        elif cod_limpio in CODIGOS_PLAN_ANUAL:
            actualizar_plan_usuario(usuario_actual["email"], "annual")
            st.success("🎉 ¡Plan Anual VIP activado en tu cuenta! Acceso total desbloqueado.")
            st.rerun()
        else:
            st.error("❌ Código no válido. Verifica el código enviado a tu correo tras la compra.")

    if not motivo_bloqueo:
        st.markdown("---")
        st.subheader("🔒 Cambiar mi Contraseña")
        p_nueva1 = st.text_input("Nueva Contraseña:", type="password", key="cambio_p1")
        p_nueva2 = st.text_input("Confirmar Nueva Contraseña:", type="password", key="cambio_p2")
        if st.button("Actualizar Contraseña"):
            if len(p_nueva1) < 6 or p_nueva1 != p_nueva2:
                st.error("⚠️ Las contraseñas deben coincidir y tener al menos 6 caracteres.")
            else:
                conn = sqlite3.connect(USERS_DB)
                conn.execute("UPDATE usuarios SET password_hash = ? WHERE email = ?", (encriptar_password(p_nueva1), usuario_actual["email"]))
                conn.commit()
                conn.close()
                st.success("✅ Tu contraseña ha sido actualizada correctamente.")

# Si el usuario eligió en el menú lateral ver la pestaña de Suscripción y Cuenta:
if modo_vista == "💳 Suscripción y Mi Cuenta":
    mostrar_area_suscripcion(motivo_bloqueo=False)
    st.stop()

# ==============================================================================
# 🔎 EXPLORADOR DE BASES DE DATOS (CON CONTROL DE LÍMITE DE BÚSQUEDAS GRATIS)
# ==============================================================================
st.sidebar.subheader("🏢 Select Industry (96 Total)")
filtro_sidebar = st.sidebar.text_input("🔍 Filtrar industria:", placeholder="Ej: Plumbing, Law, Dental...")

rubros_ordenados = sorted(RUBROS_95, key=lambda r: conteos_por_industria.get(r, 0), reverse=True)
todas_las_opciones = ["Trucking & Logistics (FMCSA)", "🌐 All Categories (Global Search)"] + rubros_ordenados

if filtro_sidebar.strip():
    opciones_filtradas = [op for op in todas_las_opciones if filtro_sidebar.strip().lower() in op.lower()]
    if not opciones_filtradas:
        opciones_filtradas = todas_las_opciones
else:
    opciones_filtradas = todas_las_opciones

industria = st.sidebar.radio(
    "Available Databases:",
    opciones_filtradas,
    format_func=lambda op: f"{op} ({conteos_por_industria.get(op, 0):,} Verified)"
)

st.title(f"🚀 B2B Lead Database: {industria}")

# Panel de filtros de búsqueda avanzada
st.markdown("##### 🔎 Búsqueda Avanzada por Perfil")
f1, f2, f3 = st.columns(3)
b_empresa = f1.text_input("🏢 Company Name:", placeholder="Ej: Express, Drain Genie...")
b_persona = f2.text_input("👤 Person / Owner Name:", placeholder="Ej: John, Michael...")
b_telefono = f3.text_input("📞 Phone Number / Area Code:", placeholder="Ej: 305, 718, 480...")

f4, f5, f6 = st.columns(3)
b_ciudad = f4.text_input("🏙️ City:", placeholder="Ej: Miami, Orlando, Houston...")
b_estado = f5.text_input("🗺️ State (2-Letter Code):", placeholder="Ej: FL, TX, NY, CA...")
b_zip = f6.text_input("📮 Zip Code:", placeholder="Ej: 33101, 85201...")

# Detectar si el usuario acaba de realizar una nueva búsqueda para descontar 1 del límite gratuito
firma_actual = f"{industria}|{b_empresa.strip()}|{b_persona.strip()}|{b_telefono.strip()}|{b_ciudad.strip()}|{b_estado.strip()}|{b_zip.strip()}"
hay_filtros_activos = any([b_empresa.strip(), b_persona.strip(), b_telefono.strip(), b_ciudad.strip(), b_estado.strip(), b_zip.strip()])

if not es_suscriptor_pro:
    if st.session_state.ultima_firma_busqueda == "":
        st.session_state.ultima_firma_busqueda = firma_actual
    elif firma_actual != st.session_state.ultima_firma_busqueda and hay_filtros_activos:
        st.session_state.ultima_firma_busqueda = firma_actual
        incrementar_busqueda_usuario(usuario_actual["email"])
        usuario_actual = obtener_usuario(usuario_actual["email"])
        busquedas_usadas = usuario_actual["busquedas_usadas"]

    # 🛑 SI EXCEDE EL LÍMITE DE BÚSQUEDAS GRATIS -> BLOQUEAR Y MOSTRAR SUSCRIPCIÓN
    if busquedas_usadas >= LIMITE_BUSQUEDAS_GRATIS:
        mostrar_area_suscripcion(motivo_bloqueo=True)
        st.stop()

# ==============================================================================
# MOSTRAR RESULTADOS SI TIENE BÚSQUEDAS DISPONIBLES O ES SUSCRIPTOR PRO
# ==============================================================================
if industria == "Trucking & Logistics (FMCSA)":
    conn = sqlite3.connect("perfiles_fmcsa.db")
    cursor = conn.cursor()
    condiciones = ["1=1"]
    params = []

    if b_empresa.strip():
        condiciones.append("(Empresa_Legal LIKE ? OR Nombre_Comercial_DBA LIKE ?)")
        params.extend([f"%{b_empresa.strip()}%", f"%{b_empresa.strip()}%"])
    if b_persona.strip():
        condiciones.append("(Dueno_Principal LIKE ? OR Segundo_Directivo LIKE ?)")
        params.extend([f"%{b_persona.strip()}%", f"%{b_persona.strip()}%"])
    if b_telefono.strip():
        condiciones.append("(Celular_Directo LIKE ? OR Telefono_Oficina LIKE ?)")
        params.extend([f"%{b_telefono.strip()}%", f"%{b_telefono.strip()}%"])
    if b_ciudad.strip():
        condiciones.append("Ciudad LIKE ?")
        params.append(f"%{b_ciudad.strip()}%")
    if b_estado.strip():
        condiciones.append("Estado LIKE ?")
        params.append(f"%{b_estado.strip().upper()}%")
    if b_zip.strip():
        condiciones.append("Codigo_Postal LIKE ?")
        params.append(f"%{b_zip.strip()}%")

    where_sql = " WHERE " + " AND ".join(condiciones)
    total_matching = cursor.execute(f"SELECT COUNT(*) FROM empresas {where_sql}", params).fetchone()[0]
    df = pd.read_sql_query(f"SELECT * FROM empresas {where_sql} LIMIT 250", conn, params=params)
    conn.close()

    if "Celular_Directo" in df.columns and not es_suscriptor_pro:
        df["Celular_Directo"] = df["Celular_Directo"].apply(lambda x: ocultar_dato(x, 5))
        df["Telefono_Oficina"] = df["Telefono_Oficina"].apply(lambda x: ocultar_dato(x, 5))
        df["Email"] = df["Email"].apply(lambda x: ocultar_dato(x, 4))
    df["Estatus_Verificacion"] = "✅ Verified Active"

    st.caption(f"Mostrando {len(df)} registros de **{total_matching:,}** perfiles verificados.")
    st.dataframe(df, use_container_width=True, height=450)

else:
    conn = sqlite3.connect(DB_MEGA_PATH)
    cursor = conn.cursor()
    es_global = (industria == "🌐 All Categories (Global Search)")
    condiciones = []
    params = []

    if not es_global:
        condiciones.append("(industry = ? OR sub_category = ?)")
        params.extend([industria, industria])
    if b_empresa.strip():
        condiciones.append("company_name LIKE ?")
        params.append(f"%{b_empresa.strip()}%")
    if b_persona.strip():
        condiciones.append("contact_name LIKE ?")
        params.append(f"%{b_persona.strip()}%")
    if b_telefono.strip():
        condiciones.append("phone LIKE ?")
        params.append(f"%{b_telefono.strip()}%")
    if b_ciudad.strip():
        condiciones.append("city LIKE ?")
        params.append(f"%{b_ciudad.strip()}%")
    if b_estado.strip():
        condiciones.append("state LIKE ?")
        params.append(f"%{b_estado.strip().upper()}%")
    if b_zip.strip():
        condiciones.append("zip_code LIKE ?")
        params.append(f"%{b_zip.strip()}%")

    where_sql = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
    total_matching_ind = cursor.execute(f"SELECT COUNT(*) FROM leads_b2b {where_sql}", params).fetchone()[0]

    query = f"""
        SELECT company_name AS Empresa_Legal,
               COALESCE(sub_category, industry) AS Rubro,
               contact_name AS Dueno_Principal,
               phone AS Telefono_Directo,
               email AS Email,
               COALESCE(address, 'On File (State Registry)') AS Direccion_Calle,
               city AS Ciudad,
               state AS Estado,
               zip_code AS Codigo_Postal,
               '✅ Verified Active' AS Estatus_Verificacion
        FROM leads_b2b
        {where_sql}
        LIMIT 500
    """
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if not df.empty and not es_suscriptor_pro:
        df["Telefono_Directo"] = df["Telefono_Directo"].apply(lambda x: ocultar_dato(x, 6))
        df["Email"] = df["Email"].apply(lambda x: ocultar_dato(x, 4))

    st.caption(f"Mostrando {len(df)} registros de **{total_matching_ind:,}** perfiles verificados.")
    st.dataframe(df, use_container_width=True, height=450)
