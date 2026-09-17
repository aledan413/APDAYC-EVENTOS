import streamlit as st
from datetime import date, datetime
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import streamlit.components.v1 as components
from io import BytesIO


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
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()


# =========================================================
# USUARIOS PILOTO
# =========================================================

USUARIOS_PILOTO = {
    "LN14": "1234"
}


# =========================================================
# FUNCIONES FIREBASE
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
        db.collection("locales").document(documento_id).set(
            datos,
            merge=True
        )
    else:
        datos["creado"] = datetime.now().isoformat()
        db.collection("locales").add(datos)


def documentos_del_local(local):

    documentos = []

    if local.get("ruc_dni"):
        documentos.append(str(local.get("ruc_dni")))

    if local.get("documento"):
        documentos.append(str(local.get("documento")))

    if not documentos:
        documentos.append("Sin documento")

    return list(dict.fromkeys(documentos))


def guardar_facturacion(datos):

    datos["fecha_registro"] = datetime.now().isoformat()

    db.collection("facturacion").add(datos)


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

    components.html(html, height=55)


# =========================================================
# EXPORTAR EXCEL
# =========================================================

def crear_excel():

    facturacion = []

    docs_facturacion = db.collection("facturacion").stream()

    for doc in docs_facturacion:

        datos = doc.to_dict()

        datos["id"] = doc.id

        facturacion.append(datos)


    visitas = []

    docs_visitas = db.collection("visitas").stream()

    for doc in docs_visitas:

        datos = doc.to_dict()

        datos["id"] = doc.id

        visitas.append(datos)


    df_facturacion = pd.DataFrame(facturacion)

    df_visitas = pd.DataFrame(visitas)


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

    st.subheader("Ingreso de gestor")

    codigo = st.text_input(
        "Código"
    )

    password = st.text_input(
        "Contraseña",
        type="password"
    )

    if st.button("Ingresar"):

        if (
            codigo in USUARIOS_PILOTO
            and USUARIOS_PILOTO[codigo] == password
        ):

            st.session_state.logueado = True
            st.session_state.codigo_gestor = codigo

            st.rerun()

        else:

            st.error("Código o contraseña incorrectos.")

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

    docs = db.collection("visitas").stream()

    for doc in docs:

        datos = doc.to_dict()

        if datos.get("fecha_visita") == hoy:

            visitas.append(datos)


    st.write(
        f"Fecha de visita: **{hoy}**"
    )


    total_visitas = len(visitas)

    pagos = sum(
        1
        for x in visitas
        if str(x.get("pago", "")).lower() in [
            "pagado",
            "sí",
            "si"
        ]
    )


    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Visitas de hoy",
        total_visitas
    )

    col2.metric(
        "Pagos registrados",
        pagos
    )

    col3.metric(
        "Pendientes",
        total_visitas - pagos
    )


    if visitas:

        df = pd.DataFrame(visitas)

        columnas = [
            "fecha_visita",
            "local",
            "direccion",
            "distrito",
            "resultado",
            "tipo_evento",
            "monto",
            "pago",
            "promotor",
            "telefono"
        ]

        columnas_existentes = [
            c for c in columnas
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

    st.title("📲 Mandar a facturar")

    locales = obtener_locales()

    nombres = [
        x.get("nombre", x.get("local", "Sin nombre"))
        for x in locales
    ]

    nombres = list(dict.fromkeys(nombres))

    local_seleccionado = st.selectbox(
        "Local",
        ["Nuevo local"] + nombres
    )


    local_data = None

    if local_seleccionado != "Nuevo local":

        for x in locales:

            nombre_x = x.get(
                "nombre",
                x.get("local", "")
            )

            if nombre_x == local_seleccionado:

                local_data = x
                break


    col1, col2 = st.columns(2)

    with col1:

        local = st.text_input(
            "Local",
            value=(
                local_data.get("local", "")
                if local_data else ""
            )
        )

        nombre = st.text_input(
            "Razón social / nombre",
            value=(
                local_data.get("nombre", "")
                if local_data else ""
            )
        )

        documento = st.text_input(
            "RUC / DNI",
            value=(
                local_data.get(
                    "ruc_dni",
                    local_data.get("documento", "")
                )
                if local_data else ""
            )
        )

        direccion = st.text_input(
            "Dirección",
            value=(
                local_data.get("direccion", "")
                if local_data else ""
            )
        )

        distrito = st.text_input(
            "Distrito",
            value=(
                local_data.get("distrito", "")
                if local_data else ""
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

            "fecha_evento": str(fecha_evento),

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

            "observaciones": observaciones
        }


        guardar_facturacion(datos)


        st.success(
            "Registro enviado correctamente a facturación."
        )


        mensaje = generar_whatsapp(datos)


        st.subheader(
            "📱 Mensaje para WhatsApp"
        )


        st.text_area(
            "Mensaje",
            mensaje,
            height=400
        )


        boton_copiar_whatsapp(mensaje)


# =========================================================
# VISITAS
# =========================================================

elif opcion == "🚗 Visitas":

    st.title("🚗 Registrar visita")

    locales = obtener_locales()

    nombres = [
        x.get("nombre", x.get("local", "Sin nombre"))
        for x in locales
    ]

    nombres = list(dict.fromkeys(nombres))


    local_seleccionado = st.selectbox(
        "Local visitado",
        ["Nuevo local"] + nombres
    )


    local_data = None

    if local_seleccionado != "Nuevo local":

        for x in locales:

            nombre_x = x.get(
                "nombre",
                x.get("local", "")
            )

            if nombre_x == local_seleccionado:

                local_data = x
                break


    col1, col2 = st.columns(2)


    with col1:

        local = st.text_input(
            "Local",
            value=(
                local_data.get("local", "")
                if local_data else ""
            )
        )

        nombre = st.text_input(
            "Razón social / nombre",
            value=(
                local_data.get("nombre", "")
                if local_data else ""
            )
        )

        documento = st.text_input(
            "RUC / DNI",
            value=(
                local_data.get(
                    "ruc_dni",
                    local_data.get("documento", "")
                )
                if local_data else ""
            )
        )

        direccion = st.text_input(
            "Dirección",
            value=(
                local_data.get("direccion", "")
                if local_data else ""
            )
        )

        distrito = st.text_input(
            "Distrito",
            value=(
                local_data.get("distrito", "")
                if local_data else ""
            )
        )


    with col2:

        fecha_evento = st.date_input(
            "Fecha del evento",
            value=date.today()
        )

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


    if st.button(
        "💾 Guardar visita",
        type="primary"
    ):

        datos = {

            "fecha_visita": str(date.today()),

            "fecha_evento": str(fecha_evento),

            "local": local,

            "nombre": nombre,

            "documento": documento,

            "direccion": direccion,

            "distrito": distrito,

            "resultado": resultado,

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


        guardar_visita(datos)


        st.success(
            "Visita registrada correctamente."
        )


# =========================================================
# LOCALES
# =========================================================

elif opcion == "🏪 Locales":

    st.title("🏪 Locales")

    locales = obtener_locales()


    st.subheader("Registrar / actualizar local")


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
            None if local_id == "Nuevo local"
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

    st.title("📥 Exportar Excel")

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
