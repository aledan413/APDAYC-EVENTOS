import streamlit as st
from datetime import date, datetime
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
# USUARIOS PILOTO
# =========================================================

USUARIOS_PILOTO = {
    "LN14": "1234"
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

    datos["actualizado"] = datetime.now().isoformat()

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

    datos["fecha_registro"] = datetime.now().isoformat()

    db.collection("facturacion").add(datos)


# =========================================================
# PREPARAR FOTO
# =========================================================

def preparar_foto(foto):

    """
    Convierte la foto a JPG comprimido para que
    pueda guardarse dentro del documento de Firebase.
    """

    try:

        imagen = Image.open(foto)

        # Convertir a RGB
        if imagen.mode != "RGB":

            imagen = imagen.convert("RGB")

        # Reducir tamaño máximo
        max_lado = 1280

        if max(imagen.size) > max_lado:

            imagen.thumbnail(
                (max_lado, max_lado)
            )

        salida = BytesIO()

        calidad = 75

        imagen.save(
            salida,
            format="JPEG",
            quality=calidad,
            optimize=True
        )

        foto_bytes = salida.getvalue()

        # Firebase Firestore tiene límite de tamaño por documento.
        # Dejamos margen de seguridad.
        if len(foto_bytes) > 850000:

            salida = BytesIO()

            imagen.save(
                salida,
                format="JPEG",
                quality=55,
                optimize=True
            )

            foto_bytes = salida.getvalue()

        if len(foto_bytes) > 950000:

            return None

        return foto_bytes

    except Exception:

        return None


# =========================================================
# VERIFICAR DUPLICADO DE VISITA
# =========================================================

def visita_ya_registrada_hoy(
    documento,
    local,
    gestor,
    fecha_visita
):

    docs = db.collection("visitas").stream()

    for doc in docs:

        datos = doc.to_dict()

        mismo_dia = (
            datos.get("fecha_visita")
            == fecha_visita
        )

        mismo_gestor = (
            datos.get("gestor")
            == gestor
        )

        mismo_documento = (
            str(datos.get("documento", "")).strip()
            == str(documento).strip()
        )

        mismo_local = (
            str(datos.get("local", "")).strip().lower()
            == str(local).strip().lower()
        )

        if (
            mismo_dia
            and mismo_gestor
            and (
                mismo_documento
                or mismo_local
            )
        ):

            return True

    return False


# =========================================================
# GUARDAR VISITA
# =========================================================

def guardar_visita(datos):

    datos["fecha_registro"] = datetime.now().isoformat()

    db.collection("visitas").add(datos)


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


def boton_copiar_whatsapp(texto):

    texto_js = (
        texto
        .replace("\\", "\\\\")
        .replace("`", "\\`")
    )

    html = f"""
    <button
        onclick="navigator.clipboard.writeText(`{texto_js}`)"
        style="
            padding:10px 18px;
            border:none;
            border-radius:8px;
            cursor:pointer;
            font-size:16px;
        "
    >
        📋 Copiar mensaje para WhatsApp
    </button>
    """

    components.html(
        html,
        height=55
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
# LOGIN
# =========================================================

if "logueado" not in st.session_state:

    st.session_state.logueado = False


if not st.session_state.logueado:

    st.title("🎵 APDAYC - Eventos")

    st.subheader(
        "Ingreso de gestor"
    )

    codigo = st.text_input(
        "Código"
    )

    password = st.text_input(
        "Contraseña",
        type="password"
    )

    if st.button(
        "Ingresar"
    ):

        if (
            codigo in USUARIOS_PILOTO
            and USUARIOS_PILOTO[codigo]
            == password
        ):

            st.session_state.logueado = True

            st.session_state.codigo_gestor = (
                codigo
            )

            st.rerun()

        else:

            st.error(
                "Código o contraseña incorrectos."
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

    st.title("📊 Panel de ruta")

    hoy = str(date.today())

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

    st.write(
        f"Fecha de visita: **{hoy}**"
    )

    total_visitas = len(visitas)

    pagos = sum(
        1
        for x in visitas
        if str(
            x.get("pago", "")
        ).lower()
        in [
            "pagado",
            "sí",
            "si"
        ]
    )

    encontrados = sum(
        1
        for x in visitas
        if x.get("resultado")
        == "Encontrado"
    )

    no_encontrados = sum(
        1
        for x in visitas
        if x.get("resultado")
        == "No encontrado"
    )

    col1, col2, col3, col4, col5 = (
        st.columns(5)
    )

    col1.metric(
        "Visitas de hoy",
        total_visitas
    )

    col2.metric(
        "Encontrados",
        encontrados
    )

    col3.metric(
        "No encontrados",
        no_encontrados
    )

    col4.metric(
        "Pagos",
        pagos
    )

    col5.metric(
        "Pendientes",
        total_visitas - pagos
    )

    if visitas:

        df = pd.DataFrame(
            visitas
        )

        columnas = [
            "fecha_visita",
            "hora_visita",
            "local",
            "documento",
            "direccion",
            "distrito",
            "resultado",
            "monto",
            "pago",
            "gestor",
            "tiene_foto",
            "latitud",
            "longitud",
            "precision_gps"
        ]

        columnas_existentes = [
            c
            for c in columnas
            if c in df.columns
        ]

        st.dataframe(
            df[columnas_existentes],
            use_container_width=True
        )

    else:

        st.info(
            "Todavía no hay visitas registradas hoy."
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

    st.title(
        "🚗 Registrar visita"
    )

    st.subheader(
        "📍 Ubicación de la visita"
    )

    # -----------------------------------------------------
    # GPS
    # -----------------------------------------------------

    ubicacion = streamlit_geolocation()

    latitud = ""
    longitud = ""
    precision_gps = ""

    if ubicacion:

        if (
            "latitude"
            in ubicacion
            and "longitude"
            in ubicacion
        ):

            latitud = ubicacion.get(
                "latitude"
            )

            longitud = ubicacion.get(
                "longitude"
            )

            precision_gps = ubicacion.get(
                "accuracy",
                ""
            )

            st.success(
                f"📍 Ubicación obtenida "
                f"| Precisión aproximada: "
                f"{precision_gps} m"
            )

        elif "error" in ubicacion:

            st.warning(
                "⚠️ No se pudo obtener la ubicación. "
                "Verifica que el navegador tenga "
                "permiso para acceder al GPS."
            )

    # -----------------------------------------------------
    # FECHA Y HORA
    # -----------------------------------------------------

    ahora = datetime.now()

    fecha_visita = str(
        ahora.date()
    )

    hora_visita = ahora.strftime(
        "%H:%M:%S"
    )

    st.info(
        f"🕐 Fecha de visita: **{fecha_visita}**  "
        f"| Hora registrada: **{hora_visita}**"
    )

    # =====================================================
    # BUSCAR ESTABLECIMIENTO
    # =====================================================

    termino_busqueda = st.text_input(
        "🔎 Buscar por RUC, razón social o establecimiento",
        placeholder="Ejemplo: 20123456789, Huanca o nombre de empresa",
        key="buscar_visita"
    )

    fila_local = None

    if len(
        termino_busqueda.strip()
    ) >= 2:

        resultados = buscar_locales_excel(
            termino_busqueda
        )

        if resultados.empty:

            st.warning(
                "No se encontraron establecimientos."
            )

        else:

            opciones = []

            indices = []

            for indice, fila in resultados.iterrows():

                opciones.append(
                    f"{fila.get('Establecimiento', '')} | "
                    f"RUC: {fila.get('Ruc', '')} | "
                    f"{fila.get('Nombre ó Razón Social', '')} | "
                    f"{fila.get('Direccion', '')}"
                )

                indices.append(
                    indice
                )

            seleccion = st.selectbox(
                "🏪 Selecciona el establecimiento",
                opciones,
                key="seleccionar_visita"
            )

            posicion = opciones.index(
                seleccion
            )

            indice_seleccionado = (
                indices[posicion]
            )

            fila_local = resultados.loc[
                indice_seleccionado
            ]

    else:

        st.info(
            "Escribe al menos 2 caracteres para buscar."
        )


    # =====================================================
    # DATOS DEL LOCAL
    # =====================================================

    if fila_local is not None:

        local = fila_local.get(
            "Establecimiento",
            ""
        )

        nombre = fila_local.get(
            "Nombre ó Razón Social",
            ""
        )

        documento = fila_local.get(
            "Ruc",
            ""
        )

        direccion = fila_local.get(
            "Direccion",
            ""
        )

        distrito = fila_local.get(
            "Distrito",
            ""
        )

        departamento = fila_local.get(
            "Departamento",
            ""
        )

        provincia = fila_local.get(
            "Provincia",
            ""
        )

        tipo_establecimiento = fila_local.get(
            "Tipo Est.",
            ""
        )

        tipo_facturacion = fila_local.get(
            "Tipo Fac.",
            ""
        )

        st.success(
            "✅ Datos encontrados en la Base Maestra"
        )

    else:

        local = ""
        nombre = ""
        documento = ""
        direccion = ""
        distrito = ""
        departamento = ""
        provincia = ""
        tipo_establecimiento = ""
        tipo_facturacion = ""


    # =====================================================
    # MOSTRAR DATOS
    # =====================================================

    if fila_local is not None:

        with st.expander(
            "🏪 Ver datos completos del establecimiento",
            expanded=True
        ):

            col_a, col_b = st.columns(2)

            with col_a:

                st.text_input(
                    "Local / Establecimiento",
                    value=local,
                    disabled=True,
                    key=f"local_{fila_local.name}"
                )

                st.text_input(
                    "Razón social",
                    value=nombre,
                    disabled=True,
                    key=f"nombre_{fila_local.name}"
                )

                st.text_input(
                    "RUC",
                    value=documento,
                    disabled=True,
                    key=f"ruc_{fila_local.name}"
                )

                st.text_input(
                    "Dirección",
                    value=direccion,
                    disabled=True,
                    key=f"direccion_{fila_local.name}"
                )

            with col_b:

                st.text_input(
                    "Distrito",
                    value=distrito,
                    disabled=True,
                    key=f"distrito_{fila_local.name}"
                )

                st.text_input(
                    "Provincia",
                    value=provincia,
                    disabled=True,
                    key=f"provincia_{fila_local.name}"
                )

                st.text_input(
                    "Departamento",
                    value=departamento,
                    disabled=True,
                    key=f"departamento_{fila_local.name}"
                )

                st.text_input(
                    "Tipo de establecimiento",
                    value=tipo_establecimiento,
                    disabled=True,
                    key=f"tipo_est_{fila_local.name}"
                )


    # =====================================================
    # FOTO
    # =====================================================

    st.subheader(
        "📷 Evidencia fotográfica"
    )

    st.write(
        "Toma la foto directamente desde el celular. "
        "Esta foto quedará asociada a la visita."
    )

    foto = st.camera_input(
        "📸 Tomar foto de evidencia",
        key=(
            f"camera_{fila_local.name}"
            if fila_local is not None
            else "camera_vacia"
        )
    )

    foto_bytes = None

    if foto is not None:

        st.image(
            foto,
            caption="Vista previa de la evidencia",
            use_container_width=True
        )

        foto_bytes = preparar_foto(
            foto
        )

        if foto_bytes is None:

            st.error(
                "❌ La foto es demasiado grande. "
                "Toma otra foto con menor resolución."
            )

        else:

            st.success(
                "📸 Foto preparada para guardar."
            )


    # =====================================================
    # FORMULARIO DE VISITA
    # =====================================================

    st.subheader(
        "📝 Resultado de la visita"
    )

    col1, col2 = st.columns(2)

    with col1:

        resultado = st.selectbox(
            "Resultado de la visita",
            [
                "Encontrado",
                "No encontrado",
                "Cerrado",
                "No corresponde",
                "Reprogramar"
            ]
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

    with col2:

        pago = st.selectbox(
            "Pago",
            [
                "Pendiente",
                "Pagado",
                "No aplica"
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


    # =====================================================
    # RESUMEN ANTES DE GUARDAR
    # =====================================================

    if fila_local is not None:

        st.subheader(
            "📋 Resumen de la visita"
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Local",
            local[:25]
            if local
            else "-"
        )

        col2.metric(
            "Resultado",
            resultado
        )

        col3.metric(
            "Foto",
            "Sí"
            if foto_bytes
            else "No"
        )

        col4.metric(
            "GPS",
            "Sí"
            if latitud
            else "No"
        )


    # =====================================================
    # GUARDAR
    # =====================================================

    if st.button(
        "💾 GUARDAR VISITA",
        type="primary",
        use_container_width=True
    ):

        if not local:

            st.error(
                "⚠️ Primero debes buscar y seleccionar un local."
            )

        elif foto is None:

            st.error(
                "⚠️ Toma una foto de evidencia antes de guardar."
            )

        elif foto_bytes is None:

            st.error(
                "⚠️ No se pudo preparar la foto."
            )

        else:

            gestor = st.session_state.get(
                "codigo_gestor",
                ""
            )

            # ---------------------------------------------
            # EVITAR DUPLICADOS
            # ---------------------------------------------

            duplicado = visita_ya_registrada_hoy(
                documento=documento,
                local=local,
                gestor=gestor,
                fecha_visita=fecha_visita
            )

            if duplicado:

                st.warning(
                    "⚠️ Este local ya tiene una visita "
                    "registrada hoy para este gestor."
                )

                confirmar = st.checkbox(
                    "Quiero registrar nuevamente esta visita de todas formas."
                )

                if not confirmar:

                    st.stop()


            # ---------------------------------------------
            # DATOS
            # ---------------------------------------------

            datos = {

                "fecha_visita": fecha_visita,

                "hora_visita": hora_visita,

                "fecha_hora_visita": (
                    f"{fecha_visita} "
                    f"{hora_visita}"
                ),

                "local": local,

                "nombre": nombre,

                "documento": documento,

                "direccion": direccion,

                "distrito": distrito,

                "departamento": departamento,

                "provincia": provincia,

                "tipo_establecimiento": (
                    tipo_establecimiento
                ),

                "tipo_facturacion": (
                    tipo_facturacion
                ),

                "resultado": resultado,

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

                "gestor": gestor,

                # GPS
                "latitud": latitud,

                "longitud": longitud,

                "precision_gps": precision_gps,

                # Evidencia
                "foto_evidencia": foto_bytes,

                "tiene_foto": True
            }

            guardar_visita(
                datos
            )

            st.success(
                "✅ VISITA REGISTRADA CORRECTAMENTE"
            )

            st.balloons()


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
        "El archivo contiene dos pestañas:"
    )

    st.write(
        "1. Facturacion"
    )

    st.write(
        "2. Visitas"
    )

    if st.button(
        "📊 Generar Excel"
    ):

        archivo = crear_excel()

        st.download_button(
            label="⬇️ Descargar Excel",
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
