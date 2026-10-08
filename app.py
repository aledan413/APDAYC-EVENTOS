import streamlit as st
import requests
from datetime import date, datetime
from zoneinfo import ZoneInfo
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import streamlit.components.v1 as components
from io import BytesIO
from PIL import Image

# NUEVO: ubicación GPS
from streamlit_geolocation import streamlit_geolocation


# =========================================================
# CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="APDAYC - Eventos",
    page_icon="🎵",
    layout="wide"
)


# =========================================================
# FIREBASE
# =========================================================

if not firebase_admin._apps:

    cred = credentials.Certificate(
        dict(st.secrets["firebase"])
    )

    firebase_admin.initialize_app(cred)


db = firestore.client()

# =========================================================
# AUTENTICACIÓN FIREBASE
# =========================================================

def autenticar_usuario(email, password):

    api_key = st.secrets["firebase_api_key"]

    url = (
        "https://identitytoolkit.googleapis.com/v1/"
        f"accounts:signInWithPassword?key={api_key}"
    )

    datos = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    try:

        respuesta = requests.post(
            url,
            json=datos,
            timeout=15
        )

        if respuesta.status_code == 200:

            return respuesta.json()

        error_data = respuesta.json()

        mensaje_error = (
            error_data
            .get("error", {})
            .get("message", "Error de autenticación")
        )

        return {
            "error": mensaje_error
        }

    except Exception as e:

        return {
            "error": str(e)
        }



# =========================================================
# BASE MAESTRA DE LOCALES
# =========================================================

ARCHIVO_BASE_LOCALES = "BASE2.xlsx"


@st.cache_data
def cargar_base_locales():

    try:

        df = pd.read_excel(
            ARCHIVO_BASE_LOCALES,
            dtype=str,
            engine="calamine"
        )

    except Exception as e:

        st.error("❌ No se pudo leer BASE2.xlsx")
        st.code(str(e))
        st.stop()

    df.columns = df.columns.str.strip()

    for columna in df.columns:

        df[columna] = (
            df[columna]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    return df


# =========================================================
# BUSCAR LOCALES
# =========================================================

def buscar_locales_excel(termino):

    df = cargar_base_locales()

    termino = termino.strip().lower()

    if not termino:

        return df.iloc[0:0]

    columnas_busqueda = [
        "Establecimiento",
        "Ruc",
        "Nombre ó Razón Social"
    ]

    filtros = []

    for columna in columnas_busqueda:

        if columna in df.columns:

            filtros.append(
                df[columna]
                .str.lower()
                .str.contains(
                    termino,
                    na=False,
                    regex=False
                )
            )

    if not filtros:

        return df.iloc[0:0]

    filtro_final = filtros[0]

    for filtro in filtros[1:]:

        filtro_final = filtro_final | filtro

    return df[filtro_final]


# =========================================================
# FIREBASE - LOCALES
# =========================================================

def obtener_locales():

    locales = []

    docs = db.collection("locales").stream()

    for doc in docs:

        datos = doc.to_dict()

        datos["_id"] = doc.id

        locales.append(datos)

    return locales


def guardar_local(datos, documento_id=None):

    datos["actualizado"] = datetime.now(
        ZoneInfo("America/Lima")
    ).isoformat()
    if documento_id:

        db.collection("locales").document(
            documento_id
        ).set(
            datos,
            merge=True
        )

    else:

        datos["creado"] = datetime.now().isoformat()

        db.collection("locales").add(datos)


# =========================================================
# FIREBASE - FACTURACIÓN
# =========================================================

def guardar_facturacion(datos):

    datos["fecha_registro"] = datetime.now(
        ZoneInfo("America/Lima")
    ).isoformat()

    db.collection("facturacion").add(datos)


# =========================================================
# PREPARAR FOTO CON DATOS DE VISITA
# =========================================================

def preparar_foto(
    foto,
    local="",
    fecha="",
    hora="",
    latitud="",
    longitud="",
    gestor=""
):

    """
    Prepara la fotografía y coloca una franja inferior
    con los datos de la visita.
    """

    try:

        imagen = Image.open(foto)

        # Convertir a RGB
        if imagen.mode != "RGB":
            imagen = imagen.convert("RGB")

        # Reducir tamaño
        max_lado = 1200

        if max(imagen.size) > max_lado:
            imagen.thumbnail(
                (max_lado, max_lado)
            )

        # =================================================
        # CREAR FRANJA INFERIOR
        # =================================================

        from PIL import ImageDraw, ImageFont

        ancho, alto = imagen.size

        alto_franja = 125

        nueva_imagen = Image.new(
            "RGB",
            (
                ancho,
                alto + alto_franja
            ),
            "white"
        )

        nueva_imagen.paste(
            imagen,
            (0, 0)
        )

        draw = ImageDraw.Draw(
            nueva_imagen
        )

        # =================================================
        # FUENTE
        # =================================================

        try:

            fuente = ImageFont.truetype(
                "DejaVuSans.ttf",
                20
            )

            fuente_pequena = ImageFont.truetype(
                "DejaVuSans.ttf",
                17
            )

        except:

            fuente = ImageFont.load_default()

            fuente_pequena = fuente

        # =================================================
        # DATOS
        # =================================================

        texto_local = (
            f"{local}"
        )

        texto_gps = (
            f"GPS: {latitud}, {longitud}"
            if latitud and longitud
            else "GPS: No disponible"
        )

        texto_fecha = (
            f"{fecha} · {hora}"
        )

        texto_gestor = (
            f"Gestor: {gestor}"
            if gestor
            else "Gestor"
        )

        # =================================================
        # ESCRIBIR INFORMACIÓN
        # =================================================

        x = 20

        draw.text(
            (x, alto + 10),
            texto_local,
            fill="black",
            font=fuente
        )

        draw.text(
            (x, alto + 38),
            texto_gps,
            fill="black",
            font=fuente_pequena
        )

        draw.text(
            (x, alto + 64),
            texto_fecha,
            fill="black",
            font=fuente_pequena
        )

        draw.text(
            (x, alto + 90),
            texto_gestor,
            fill="black",
            font=fuente_pequena
        )

        # =================================================
        # COMPRIMIR
        # =================================================

        for calidad in [
            70,
            55,
            45,
            35
        ]:

            salida = BytesIO()

            nueva_imagen.save(
                salida,
                format="JPEG",
                quality=calidad,
                optimize=True
            )

            foto_bytes = (
                salida.getvalue()
            )

            if len(foto_bytes) <= 500000:

                return foto_bytes

        return None

    except Exception as e:

        st.error(
            f"❌ No se pudo preparar la fotografía: {e}"
        )

        return None
# =========================================================
# VERIFICAR DUPLICADO DE VISITA
# =========================================================

def visita_ya_registrada_hoy(documento="", local="", gestor="", fecha_visita=""):

    try:
        docs = (
            db.collection("visitas")
            .where("fecha_visita", "==", fecha_visita)
            .where("gestor", "==", gestor)
            .stream()
        )

        local_busqueda = local.strip().lower()

        for doc in docs:
            datos = doc.to_dict()

            local_guardado = str(
                datos.get("local", "")
            ).strip().lower()

            if local_guardado == local_busqueda:
                return True

        return False

    except Exception as e:

        st.error(
            "❌ Error al verificar si la visita ya existe."
        )

        st.code(
            f"{type(e).__name__}: {e}"
        )

        return False


# =========================================================
# GUARDAR VISITA
# =========================================================

def guardar_visita(datos):

    try:

        datos["fecha_registro"] = datetime.now(
            ZoneInfo("America/Lima")
        ).isoformat()

        resultado = (
            db.collection("visitas")
            .add(datos)
        )

        # Firebase devuelve:
        # (update_time, DocumentReference)

        referencia = resultado[1]

        if hasattr(referencia, "id"):

            return referencia.id

        st.error(
            "❌ Firebase guardó la visita, "
            "pero no se pudo obtener el ID."
        )

        st.code(
            f"Tipo recibido: {type(referencia)}"
        )

        return None

    except Exception as e:

        st.error(
            "❌ No se pudo guardar la visita en Firebase."
        )

        st.code(
            f"{type(e).__name__}: {e}"
        )

        return None
# =========================================================
# WHATSAPP
# =========================================================

def generar_whatsapp(datos):

    mensaje = f"""APDAYC - DATOS PARA FACTURACIÓN

LOCAL: {datos.get('local', '')}
RAZÓN SOCIAL: {datos.get('nombre', '')}
DOCUMENTO: {datos.get('documento', '')}
DIRECCIÓN: {datos.get('direccion', '')}
DISTRITO: {datos.get('distrito', '')}

FECHA DEL EVENTO: {datos.get('fecha_evento', '')}
TIPO DE EVENTO: {datos.get('tipo_evento', '')}
MEDIO: {datos.get('medio', '')}
ARTISTA/BANDA: {datos.get('artista', '')}

MONTO: S/ {datos.get('monto', '')}
TARIFA: S/ {datos.get('tarifa', '')}
PAGO: {datos.get('pago', '')}
BANCO: {datos.get('banco', '')}
N.º OPERACIÓN: {datos.get('operacion', '')}

PROMOTOR: {datos.get('promotor', '')}
TELÉFONO: {datos.get('telefono', '')}

OBSERVACIONES:
{datos.get('observaciones', '')}
"""

    return mensaje

def boton_compartir_foto_whatsapp(
    foto_bytes,
    local,
    fecha,
    hora
):

    import base64

    imagen_base64 = base64.b64encode(
        foto_bytes
    ).decode("utf-8")

    mensaje = (
        f"Visita - {local}\n"
        f"Fecha: {fecha}\n"
        f"Hora: {hora}"
    )

    mensaje_js = (
        mensaje
        .replace("\\", "\\\\")
        .replace("`", "\\`")
    )

    html = f"""
    <button
        id="compartir"
        style="
            width:100%;
            padding:12px;
            border:none;
            border-radius:8px;
            cursor:pointer;
            font-size:17px;
            font-weight:bold;
        "
    >
        📲 Compartir foto por WhatsApp
    </button>

    <script>

    document
        .getElementById("compartir")
        .onclick = async function() {{

            try {{

                const base64 =
                    "{imagen_base64}";

                const byteCharacters =
                    atob(base64);

                const byteNumbers =
                    new Array(
                        byteCharacters.length
                    );

                for (
                    let i = 0;
                    i < byteCharacters.length;
                    i++
                ) {{

                    byteNumbers[i] =
                        byteCharacters.charCodeAt(i);
                }}

                const byteArray =
                    new Uint8Array(
                        byteNumbers
                    );

                const blob =
                    new Blob(
                        [byteArray],
                        {{
                            type: "image/jpeg"
                        }}
                    );

                const archivo =
                    new File(
                        [blob],
                        "APDAYC_{local}.jpg",
                        {{
                            type: "image/jpeg"
                        }}
                    );

                const texto =
                    `{mensaje_js}`;

                if (
                    navigator.share &&
                    navigator.canShare &&
                    navigator.canShare({{
                        files: [archivo]
                    }})
                ) {{

                    await navigator.share({{
                        title: "APDAYC",
                        text: texto,
                        files: [archivo]
                    }});

                }} else {{

                    alert(
                        "Tu navegador no permite compartir "
                        + "la fotografía directamente. "
                        + "Puedes descargarla y enviarla "
                        + "por WhatsApp."
                    );

                }}

            }} catch(error) {{

                console.log(error);

            }}

        }};

    </script>
    """

    components.html(
        html,
        height=65
    )


# =========================================================
# EXPORTAR EXCEL
# =========================================================

def crear_excel():

    # -----------------------------------------------------
    # FACTURACIÓN
    # -----------------------------------------------------

    facturacion = []

    docs_facturacion = (
        db.collection("facturacion")
        .stream()
    )

    for doc in docs_facturacion:

        datos = doc.to_dict()

        datos["id"] = doc.id

        facturacion.append(datos)

    # -----------------------------------------------------
    # VISITAS
    # -----------------------------------------------------

    visitas = []

    docs_visitas = (
        db.collection("visitas")
        .stream()
    )

    for doc in docs_visitas:

        datos = doc.to_dict()

        datos["id"] = doc.id

        # No colocar la foto binaria dentro del Excel
        if "foto_evidencia" in datos:

            if datos["foto_evidencia"]:

                datos["foto_evidencia"] = (
                    "Sí - evidencia guardada"
                )

            else:

                datos["foto_evidencia"] = "No"

        visitas.append(datos)

    df_facturacion = pd.DataFrame(
        facturacion
    )

    df_visitas = pd.DataFrame(
        visitas
    )

    salida = BytesIO()

    with pd.ExcelWriter(
        salida,
        engine="openpyxl"
    ) as writer:

        df_facturacion.to_excel(
            writer,
            index=False,
            sheet_name="Facturacion"
        )

        df_visitas.to_excel(
            writer,
            index=False,
            sheet_name="Visitas"
        )

    salida.seek(0)

    return salida


# =========================================================
# EXPORTAR SOLO VISITAS
# =========================================================

def crear_excel_visitas():

    visitas = []

    docs_visitas = (
        db.collection("visitas")
        .stream()
    )

    for doc in docs_visitas:

        datos = doc.to_dict()

        datos["id"] = doc.id

        # La foto no se mete como archivo binario
        # dentro del Excel. Se registra si existe.
        if "foto_evidencia" in datos:

            if datos["foto_evidencia"]:
                datos["evidencia_foto"] = "Sí - foto guardada"
            else:
                datos["evidencia_foto"] = "No"

            del datos["foto_evidencia"]

        visitas.append(datos)

    df_visitas = pd.DataFrame(visitas)

    # Orden recomendado para el trabajo de ruta.
    columnas_preferidas = [
        "id",
        "fecha_visita",
        "hora_visita",
        "fecha_hora_visita",
        "gestor",
        "local",
        "tiene_evento",
        "estado_evento",
        "accion_realizada",
        "codigo_carta",
        "evidencia_foto",
        "latitud",
        "longitud",
        "precision_gps",
        "fecha_registro"
    ]

    columnas_finales = [
        c for c in columnas_preferidas
        if c in df_visitas.columns
    ]

    otras_columnas = [
        c for c in df_visitas.columns
        if c not in columnas_finales
    ]

    if not df_visitas.empty:
        df_visitas = df_visitas[
            columnas_finales + otras_columnas
        ]

        if "fecha_hora_visita" in df_visitas.columns:
            df_visitas = df_visitas.sort_values(
                by="fecha_hora_visita",
                ascending=False
            )

    salida = BytesIO()

    with pd.ExcelWriter(
        salida,
        engine="openpyxl"
    ) as writer:

        df_visitas.to_excel(
            writer,
            index=False,
            sheet_name="Visitas"
        )

    salida.seek(0)

    return salida


# =========================================================
# LOGIN CON FIREBASE AUTHENTICATION
# =========================================================

if "logueado" not in st.session_state:
    st.session_state.logueado = False


if not st.session_state.logueado:

    st.title("🎵 APDAYC - Eventos")

    st.subheader("Ingreso de gestor")

    email = st.text_input(
        "Correo electrónico",
        placeholder="ejemplo@correo.com"
    )

    password = st.text_input(
        "Contraseña",
        type="password"
    )

    if st.button(
        "Ingresar",
        type="primary",
        use_container_width=True
    ):

        if not email.strip():

            st.error(
                "⚠️ Ingresa tu correo electrónico."
            )

        elif not password:

            st.error(
                "⚠️ Ingresa tu contraseña."
            )

        else:

            resultado = autenticar_usuario(
                email.strip(),
                password
            )

            if "idToken" in resultado:

                st.session_state.logueado = True

                st.session_state.email_usuario = (
                    resultado.get("email", email)
                )

                st.session_state.uid_usuario = (
                    resultado.get("localId", "")
                )

                # =====================================================
                # IDENTIFICAR GESTOR SEGÚN SU CORREO
                # =====================================================

                correo_usuario = (
                    resultado.get("email", email)
                    .strip()
                    .lower()
                )

                if correo_usuario == "aldedan413@gmail.com":

                    st.session_state.codigo_gestor = "LN14"

                elif correo_usuario == "agecoferln19@gmail.com":

                    st.session_state.codigo_gestor = "LN19"

                else:

                    st.session_state.codigo_gestor = ""

                st.rerun()
           
            else:

                error = resultado.get(
                    "error",
                    "Error desconocido"
                )

                if error == "EMAIL_NOT_FOUND":

                    st.error(
                        "❌ El correo no está registrado."
                    )

                elif error == "INVALID_PASSWORD":

                    st.error(
                        "❌ La contraseña es incorrecta."
                    )

                elif error == "INVALID_LOGIN_CREDENTIALS":

                    st.error(
                        "❌ Correo o contraseña incorrectos."
                    )

                elif error == "USER_DISABLED":

                    st.error(
                        "❌ Este usuario está deshabilitado."
                    )

                else:

                    st.error(
                        f"❌ No se pudo iniciar sesión: {error}"
                    )

    st.stop()


# =========================================================
# MENÚ
# =========================================================

st.sidebar.title("🎵 APDAYC")

opcion = st.sidebar.radio(
    "Menú",
    [
        "📊 Panel de ruta",
        "📲 Mandar a facturar",
        "🚗 Visitas",
        "🏪 Locales",
        "📥 Exportar Excel"
    ]
)


# =========================================================
# PANEL DE RUTA
# =========================================================

if opcion == "📊 Panel de ruta":

    ahora_peru = datetime.now(
        ZoneInfo("America/Lima")
    )

    hoy = str(ahora_peru.date())

    st.title("📊 Panel de ruta")

    st.caption(
        f"📅 Fecha: {ahora_peru.strftime('%d/%m/%Y')}  |  "
        f"🕐 Hora Perú: {ahora_peru.strftime('%H:%M:%S')}"
    )

    # =====================================================
    # CONFIGURAR META
    # =====================================================

    st.subheader("🎯 Meta de ruta")

    col_meta, col_actualizar = st.columns(
        [3, 1]
    )

    with col_meta:

        meta_locales = st.number_input(
            "¿Cuántos locales debes visitar hoy?",
            min_value=1,
            max_value=200,
            value=30,
            step=1
        )

    with col_actualizar:

        st.write("")
        st.write("")

        if st.button(
            "🔄 Actualizar ruta",
            use_container_width=True
        ):

            st.rerun()

    # =====================================================
    # OBTENER VISITAS DEL DÍA
    # =====================================================

    visitas = []

    docs = db.collection(
        "visitas"
    ).stream()

    for doc in docs:

        datos = doc.to_dict()

        if (
            datos.get("fecha_visita")
            == hoy
        ):

            visitas.append(datos)

    # =====================================================
    # INDICADORES
    # =====================================================

    total_visitas = len(visitas)

    avance = (
        total_visitas / meta_locales
        if meta_locales > 0
        else 0
    )

    porcentaje = min(
        avance * 100,
        100
    )

    faltan = max(
        meta_locales - total_visitas,
        0
    )

    # =====================================================
    # CONTADORES
    # =====================================================

    con_evento = sum(
        1
        for x in visitas
        if x.get("tiene_evento")
        == "Con evento"
    )

    sin_evento = sum(
        1
        for x in visitas
        if x.get("tiene_evento")
        == "Sin evento"
    )

    sin_licenciar = sum(
        1
        for x in visitas
        if x.get("estado_evento")
        == "Detectado sin licenciar"
    )

    cartas = sum(
        1
        for x in visitas
        if x.get("accion_realizada")
        == "Se dejó carta de notificación"
    )

    licenciado_ruta = sum(
        1
        for x in visitas
        if x.get("accion_realizada")
        == "Licenciado en ruta"
    )

    fotos = sum(
        1
        for x in visitas
        if x.get("tiene_foto")
        is True
    )

    gps = sum(
        1
        for x in visitas
        if (
            x.get("latitud") not in [
                "",
                None
            ]
            and
            x.get("longitud") not in [
                "",
                None
            ]
        )
    )

    # =====================================================
    # TARJETAS PRINCIPALES
    # =====================================================

    st.subheader("📈 Avance de ruta")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "🎯 Meta",
        meta_locales
    )

    col2.metric(
        "🚗 Visitados",
        total_visitas
    )

    col3.metric(
        "⏳ Faltan",
        faltan
    )

    col4.metric(
        "📈 Avance",
        f"{porcentaje:.0f}%"
    )

    # =====================================================
    # BARRA DE PROGRESO
    # =====================================================

    st.progress(
        int(porcentaje)
    )

    st.markdown(
        f"""
        <div style="
            text-align:center;
            font-size:22px;
            font-weight:bold;
            margin-top:-8px;
            margin-bottom:20px;
        ">
            🚗 {total_visitas} de {meta_locales} locales visitados
        </div>
        """,
        unsafe_allow_html=True
    )

    # =====================================================
    # SEGUNDO GRUPO DE INDICADORES
    # =====================================================

    st.subheader("📋 Resultado de la ruta")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "🎵 Con evento",
        con_evento
    )

    col2.metric(
        "🏪 Sin evento",
        sin_evento
    )

    col3.metric(
        "⚠️ Sin licenciar",
        sin_licenciar
    )

    col4.metric(
        "📝 Cartas",
        cartas
    )

    # =====================================================
    # TERCER GRUPO
    # =====================================================

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "✅ Licenciados en ruta",
        licenciado_ruta
    )

    col2.metric(
        "📷 Con foto",
        fotos
    )

    col3.metric(
        "📍 Con GPS",
        gps
    )

    col4.metric(
        "🕐 Última hora",
        visitas[-1].get(
            "hora_visita",
            "-"
        )
        if visitas
        else "-"
    )

    # =====================================================
    # MENSAJE DE AVANCE
    # =====================================================

    if total_visitas == 0:

        st.info(
            "🚗 Todavía no tienes visitas registradas hoy. "
            "¡Vamos con la ruta!"
        )

    elif total_visitas < meta_locales:

        st.info(
            f"🚗 Vas avanzando. "
            f"Te faltan **{faltan} locales** "
            f"para completar tu meta de hoy."
        )

    else:

        st.success(
            f"🎯 ¡Meta cumplida! "
            f"Has registrado **{total_visitas} visitas** "
            f"de una meta de {meta_locales}."
        )

    # =====================================================
    # DETALLE DE VISITAS
    # =====================================================

    st.subheader("📍 Detalle de visitas de hoy")

    if visitas:

        df = pd.DataFrame(
            visitas
        )

        # -------------------------------------------------
        # Crear columnas de visualización
        # -------------------------------------------------

        if "tiene_foto" in df.columns:

            df["📷 Evidencia"] = df[
                "tiene_foto"
            ].apply(
                lambda x:
                "✅ Sí"
                if x
                else "❌ No"
            )

        else:

            df["📷 Evidencia"] = "❌ No"

        if (
            "latitud" in df.columns
            and
            "longitud" in df.columns
        ):

            df["📍 GPS"] = df.apply(
                lambda fila:
                "✅ Sí"
                if (
                    fila.get("latitud")
                    not in ["", None]
                    and
                    fila.get("longitud")
                    not in ["", None]
                )
                else
                "❌ No",
                axis=1
            )

        else:

            df["📍 GPS"] = "❌ No"

        columnas = [

            "hora_visita",

            "local",

            "tiene_evento",

            "estado_evento",

            "accion_realizada",

            "codigo_carta",

            "📷 Evidencia",

            "📍 GPS",

            "precision_gps",

            "gestor"
        ]

        columnas_existentes = [

            c
            for c in columnas
            if c in df.columns

        ]

        # -------------------------------------------------
        # Ordenar por hora
        # -------------------------------------------------

        if "hora_visita" in df.columns:

            df = df.sort_values(
                by="hora_visita",
                ascending=False
            )

        st.dataframe(
            df[
                columnas_existentes
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "📭 Todavía no hay visitas registradas hoy."
        )

# =========================================================
# MANDAR A FACTURAR
# =========================================================

elif opcion == "📲 Mandar a facturar":

    st.title(
        "📲 Mandar a facturar"
    )

    locales = obtener_locales()

    nombres = [
        x.get(
            "nombre",
            x.get(
                "local",
                "Sin nombre"
            )
        )
        for x in locales
    ]

    nombres = list(
        dict.fromkeys(nombres)
    )

    local_seleccionado = st.selectbox(
        "Local",
        ["Nuevo local"] + nombres
    )

    local_data = None

    if (
        local_seleccionado
        != "Nuevo local"
    ):

        for x in locales:

            nombre_x = x.get(
                "nombre",
                x.get("local", "")
            )

            if (
                nombre_x
                == local_seleccionado
            ):

                local_data = x

                break

    col1, col2 = st.columns(2)

    with col1:

        local = st.text_input(
            "Local",
            value=(
                local_data.get(
                    "local",
                    ""
                )
                if local_data
                else ""
            )
        )

        nombre = st.text_input(
            "Razón social / nombre",
            value=(
                local_data.get(
                    "nombre",
                    ""
                )
                if local_data
                else ""
            )
        )

        documento = st.text_input(
            "RUC / DNI",
            value=(
                local_data.get(
                    "ruc_dni",
                    local_data.get(
                        "documento",
                        ""
                    )
                )
                if local_data
                else ""
            )
        )

        direccion = st.text_input(
            "Dirección",
            value=(
                local_data.get(
                    "direccion",
                    ""
                )
                if local_data
                else ""
            )
        )

        distrito = st.text_input(
            "Distrito",
            value=(
                local_data.get(
                    "distrito",
                    ""
                )
                if local_data
                else ""
            )
        )

    with col2:

        fecha_evento = st.date_input(
            "Fecha del evento",
            value=date.today()
        )

        tipo_evento = st.selectbox(
            "Tipo de evento",
            [
                "Medios mecánicos",
                "Medios humanos",
                "Concierto",
                "Costumbrista",
                "Quinceañero",
                "Matrimonio",
                "Cumpleaños",
                "Evangelístico",
                "Circus",
                "Otro"
            ]
        )

        medio = st.selectbox(
            "Medio",
            [
                "Medios mecánicos",
                "Medios humanos"
            ]
        )

        artista = st.text_input(
            "Artista / Banda / Grupo"
        )

        monto = st.number_input(
            "Monto",
            min_value=0.0,
            step=10.0
        )

        tarifa = st.number_input(
            "Tarifa",
            min_value=0.0,
            step=10.0
        )

        pago = st.selectbox(
            "Pago",
            [
                "Pendiente",
                "Pagado"
            ]
        )

        banco = st.text_input(
            "Banco"
        )

        operacion = st.text_input(
            "N.º operación"
        )

        promotor = st.text_input(
            "Promotor"
        )

        telefono = st.text_input(
            "Teléfono"
        )

    observaciones = st.text_area(
        "Observaciones"
    )

    if st.button(
        "💾 Guardar y preparar facturación",
        type="primary"
    ):

        datos = {

            "local": local,

            "nombre": nombre,

            "documento": documento,

            "direccion": direccion,

            "distrito": distrito,

            "fecha_evento": str(
                fecha_evento
            ),

            "tipo_evento": tipo_evento,

            "medio": medio,

            "artista": artista,

            "monto": monto,

            "tarifa": tarifa,

            "pago": pago,

            "banco": banco,

            "operacion": operacion,

            "promotor": promotor,

            "telefono": telefono,

            "observaciones": observaciones,

            "gestor": st.session_state.get(
                "codigo_gestor",
                ""
            )
        }

        guardar_facturacion(
            datos
        )

        st.success(
            "Registro enviado correctamente a facturación."
        )

        mensaje = generar_whatsapp(
            datos
        )

        st.subheader(
            "📱 Mensaje para WhatsApp"
        )

        st.text_area(
            "Mensaje",
            mensaje,
            height=400
        )

        boton_copiar_whatsapp(
            mensaje
        )


# =========================================================
# VISITAS
# =========================================================

elif opcion == "🚗 Visitas":

    st.title("🚗 Registrar visita")

    # =====================================================
    # FECHA Y HORA AUTOMÁTICAS
    # =====================================================

    ahora = datetime.now(
        ZoneInfo("America/Lima")
    )

    fecha_visita = str(ahora.date())
    hora_visita = ahora.strftime("%H:%M:%S")

    st.info(
        f"🕐 Fecha: **{fecha_visita}** | "
        f"Hora: **{hora_visita}**"
    )

 

    # =====================================================
    # GPS
    # =====================================================

    ubicacion = streamlit_geolocation()

    latitud = ""
    longitud = ""
    precision_gps = ""

    if ubicacion:

        if (
            ubicacion.get("latitude") is not None
            and ubicacion.get("longitude") is not None
        ):

            latitud = ubicacion.get("latitude")
            longitud = ubicacion.get("longitude")
            precision_gps = ubicacion.get(
                "accuracy",
                ""
            )

            st.success(
                f"📍 GPS obtenido | "
                f"Precisión aproximada: {precision_gps} m"
            )

        elif ubicacion.get("error"):

            st.warning(
                "⚠️ No se pudo obtener la ubicación. "
                "Verifica el permiso de ubicación."
            )

    # =====================================================
    # LOCAL
    # =====================================================

    st.subheader("🏪 Local")

    local = st.text_input(
        "Nombre del local",
        placeholder="Ejemplo: Dventuri"
    )

    # =====================================================
    # ¿TIENE EVENTO?
    # =====================================================

    st.subheader("🎵 Evento")

    tiene_evento = st.radio(
        "¿Tiene evento?",
        [
            "Sin evento",
            "Con evento"
        ],
        horizontal=True
    )

    # Valores iniciales
    estado_evento = ""
    accion_realizada = ""
    codigo_carta = ""

    # =====================================================
    # SI TIENE EVENTO
    # =====================================================

    if tiene_evento == "Con evento":

        st.subheader("📋 Estado del evento")

        estado_evento = st.radio(
            "Estado",
            [
                "Ya licenciado",
                "Detectado sin licenciar"
            ],
            horizontal=True
        )

        # =================================================
        # DETECTADO SIN LICENCIAR
        # =================================================

        if estado_evento == "Detectado sin licenciar":

            st.subheader("⚠️ Acción realizada")

            accion_realizada = st.radio(
                "¿Qué se realizó en ruta?",
                [
                    "Licenciado en ruta",
                    "Se dejó carta de notificación"
                ],
                horizontal=True
            )

            # =============================================
            # CARTA DE NOTIFICACIÓN
            # =============================================

            if accion_realizada == "Se dejó carta de notificación":

                codigo_carta = st.text_input(
                    "Código de carta",
                    placeholder="Ejemplo: NT-004582"
                )

                st.info(
                    "📷 Toma una fotografía de la carta "
                    "como evidencia."
                )

    # =====================================================
    # FOTO DEL LOCAL
    # =====================================================

    st.subheader("📷 Foto del local")

    foto = st.camera_input(
        "📸 Tomar foto"
    )

    foto_bytes = None

    if foto is not None:

        gestor_actual = st.session_state.get(
            "codigo_gestor",
            ""
        )

        foto_bytes = preparar_foto(
            foto=foto,
            local=local.strip(),
            fecha=fecha_visita,
            hora=hora_visita,
            latitud=latitud,
            longitud=longitud,
            gestor=gestor_actual
        )

        if foto_bytes is not None:

            st.success(
                "📸 Foto preparada correctamente."
            )

            st.image(
                foto_bytes,
                caption="Foto del local",
                use_container_width=True
            )

            st.subheader(
                "📲 Foto lista para enviar"
            )

            st.download_button(
                label="⬇️ Descargar foto",
                data=foto_bytes,
                file_name=f"APDAYC_{local.strip()}.jpg",
                mime="image/jpeg",
                use_container_width=True,
                key="descargar_foto_preview"
            )

            boton_compartir_foto_whatsapp(
                foto_bytes=foto_bytes,
                local=local.strip(),
                fecha=fecha_visita,
                hora=hora_visita
            )

        else:

            st.error(
                "❌ No se pudo preparar la fotografía."
            )   
    # =====================================================
    # RESUMEN
    # =====================================================

    st.subheader("📋 Resumen")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Local",
        local if local else "-"
    )

    col2.metric(
        "Evento",
        tiene_evento
    )

    col3.metric(
        "Estado",
        estado_evento if estado_evento else "-"
    )

    col4.metric(
        "Foto",
        "Sí" if foto_bytes else "No"
    )

    # =====================================================
    # GUARDAR
    # =====================================================

    if st.button(
        "💾 GUARDAR VISITA",
        type="primary",
        use_container_width=True
    ):

        # -----------------------------------------------
        # VALIDAR LOCAL
        # -----------------------------------------------

        if not local.strip():

            st.error(
                "⚠️ Debes ingresar el nombre del local."
            )

            st.stop()

        # -----------------------------------------------
        # VALIDAR CARTA
        # -----------------------------------------------

        if (
            tiene_evento == "Con evento"
            and estado_evento == "Detectado sin licenciar"
            and accion_realizada == "Se dejó carta de notificación"
        ):

            if not codigo_carta.strip():

                st.error(
                    "⚠️ Debes ingresar el código de la carta."
                )

                st.stop()

            if not foto_bytes:

                st.error(
                    "⚠️ Debes tomar una foto de la carta "
                    "como evidencia."
                )

                st.stop()

        # -----------------------------------------------
        # GESTOR
        # -----------------------------------------------

        gestor = st.session_state.get(
            "codigo_gestor",
            ""
        )

        # -----------------------------------------------
        # DUPLICADO
        # -----------------------------------------------

        duplicado = visita_ya_registrada_hoy(
            documento="",
            local=local,
            gestor=gestor,
            fecha_visita=fecha_visita
        )

        if duplicado:

            st.warning(
                "⚠️ Este local ya tiene una visita "
                "registrada hoy."
            )

            confirmar = st.checkbox(
                "Deseo registrar otra visita para este local."
            )

            if not confirmar:

                st.stop()

        # -----------------------------------------------
        # DATOS A FIREBASE
        # -----------------------------------------------

        datos = {

            # VISITA
            "fecha_visita": fecha_visita,

            "hora_visita": hora_visita,

            "fecha_hora_visita":
                f"{fecha_visita} {hora_visita}",

            # LOCAL
            "local": local.strip(),

            # EVENTO
            "tiene_evento": tiene_evento,

            "estado_evento": estado_evento,

            "accion_realizada": accion_realizada,

            # CARTA
            "codigo_carta": codigo_carta.strip(),

            # GESTOR
            "gestor": gestor,

            # GPS
            "latitud": latitud,

            "longitud": longitud,

            "precision_gps": precision_gps,

            # FOTO
            "foto_evidencia": foto_bytes,

            "tiene_foto":
                True if foto_bytes else False
        }

        id_visita = guardar_visita(datos)

        # -----------------------------------------------
        # CONFIRMACIÓN
        # -----------------------------------------------

        if id_visita:

            st.success(
                "✅ VISITA REGISTRADA CORRECTAMENTE"
            )

            st.info(
            f"🏪 Local: {local}\n\n"
            f"🎵 Evento: {tiene_evento}\n\n"
            f"📋 Estado: "
            f"{estado_evento if estado_evento else 'No aplica'}\n\n"
            f"📝 Acción: "
            f"{accion_realizada if accion_realizada else 'No aplica'}\n\n"
            f"🔖 Código de carta: "
            f"{codigo_carta if codigo_carta else 'No aplica'}\n\n"
            f"🕐 Hora: {hora_visita}\n\n"
            f"📷 Evidencia: "
            f"{'Sí' if foto_bytes else 'No'}\n\n"
            f"📍 GPS: "
                f"{'Sí' if latitud else 'No'}"
            )

            # Excel actualizado inmediatamente después de guardar.
            st.download_button(
                label="📊 Descargar Excel de visitas",
                data=crear_excel_visitas(),
                file_name=(
                    f"APDAYC_Visitas_"
                    f"{date.today()}.xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True
            )

            # =================================================
            # COMPARTIR FOTO
            # =================================================

            if foto_bytes:

                st.subheader("📲 Compartir foto")

                st.download_button(
                    label="⬇️ Descargar foto",
                    data=foto_bytes,
                    file_name=f"APDAYC_{local.strip()}.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )

                boton_compartir_foto_whatsapp(
                    foto_bytes=foto_bytes,
                    local=local.strip(),
                    fecha=fecha_visita,
                    hora=hora_visita
                )

        else:

            st.error(
                "❌ La visita NO quedó registrada. "
                "Revisa el error de Firebase mostrado arriba."
            )



# =========================================================
# LOCALES
# =========================================================

elif opcion == "🏪 Locales":

    st.title(
        "🏪 Locales"
    )

    locales = obtener_locales()

    st.subheader(
        "Registrar / actualizar local"
    )

    local_id = st.selectbox(
        "Seleccionar local existente",
        ["Nuevo local"] + [
            x["_id"]
            for x in locales
        ]
    )

    datos_existentes = {}

    if local_id != "Nuevo local":

        for x in locales:

            if x["_id"] == local_id:

                datos_existentes = x

                break

    local = st.text_input(
        "Local",
        value=datos_existentes.get(
            "local",
            ""
        )
    )

    nombre = st.text_input(
        "Razón social / nombre",
        value=datos_existentes.get(
            "nombre",
            ""
        )
    )

    ruc_dni = st.text_input(
        "RUC / DNI",
        value=datos_existentes.get(
            "ruc_dni",
            ""
        )
    )

    direccion = st.text_input(
        "Dirección",
        value=datos_existentes.get(
            "direccion",
            ""
        )
    )

    distrito = st.text_input(
        "Distrito",
        value=datos_existentes.get(
            "distrito",
            ""
        )
    )

    telefono = st.text_input(
        "Teléfono",
        value=datos_existentes.get(
            "telefono",
            ""
        )
    )

    if st.button(
        "💾 Guardar local"
    ):

        datos = {

            "local": local,

            "nombre": nombre,

            "ruc_dni": ruc_dni,

            "direccion": direccion,

            "distrito": distrito,

            "telefono": telefono
        }

        guardar_local(
            datos,
            None
            if local_id == "Nuevo local"
            else local_id
        )

        st.success(
            "Local guardado correctamente."
        )

        st.rerun()


# =========================================================
# EXPORTAR EXCEL
# =========================================================

elif opcion == "📥 Exportar Excel":

    st.title(
        "📥 Exportar Excel"
    )

    st.write(
        "Puedes descargar el Excel general o solamente el "
        "registro de visitas."
    )

    st.subheader("📊 Excel general")

    st.write(
        "Incluye las pestañas Facturacion y Visitas."
    )

    if st.button(
        "📊 Generar Excel general"
    ):

        archivo = crear_excel()

        st.download_button(
            label="⬇️ Descargar Excel general",
            data=archivo,
            file_name=(
                f"APDAYC_Eventos_"
                f"{date.today()}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            )
        )

    st.subheader("🚗 Excel de visitas")

    st.write(
        "Este archivo contiene únicamente las visitas "
        "registradas y marca si cada visita tiene foto."
    )

    if st.button(
        "🚗 Generar Excel de visitas"
    ):

        archivo_visitas = crear_excel_visitas()

        st.download_button(
            label="⬇️ Descargar Excel de visitas",
            data=archivo_visitas,
            file_name=(
                f"APDAYC_Visitas_"
                f"{date.today()}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            )
        )
