```python
import streamlit as st
from datetime import date, datetime
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from io import BytesIO
import streamlit.components.v1 as components

# ============================================================
# FIREBASE
# ============================================================

if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="APDAYC - Control Territorial",
    page_icon="🎵",
    layout="wide"
)

CODIGO_GESTOR = "LN14"

USUARIOS_PILOTO = {
    "LN14": "1234"
}

# ============================================================
# COLUMNAS EXCEL
# ============================================================

COLUMNAS_FACTURACION = [
    "FECHA REGISTRO",
    "CODIGO GESTOR",
    "LOCAL",
    "NOMBRE / RAZON SOCIAL",
    "TIPO DOCUMENTO",
    "NUMERO DOCUMENTO",
    "DIRECCION",
    "DISTRITO",
    "FECHA EVENTO",
    "TIPO EVENTO",
    "MEDIO",
    "ARTISTA/BANDA",
    "MONTO",
    "TARIFA",
    "PAGO",
    "BANCO",
    "# OPERACION",
    "PROMOTOR",
    "TELEFONO",
    "OBSERVACIONES"
]

COLUMNAS_VISITAS = [
    "FECHA VISITA",
    "HORA",
    "CODIGO GESTOR",
    "LOCAL",
    "NOMBRE / RAZON SOCIAL",
    "TIPO DOCUMENTO",
    "NUMERO DOCUMENTO",
    "DIRECCION",
    "DISTRITO",
    "RESULTADO VISITA",
    "HUBO EVENTO",
    "QUIZO PAGAR",
    "SE DEJO CARTA",
    "TIPO CARTA",
    "CODIGO CARTA",
    "FECHA EVENTO",
    "TIPO EVENTO",
    "MEDIO",
    "ARTISTA/BANDA",
    "MONTO",
    "TARIFA",
    "TARIFA CORRECTA",
    "PAGO",
    "BANCO",
    "# OPERACION",
    "PROMOTOR",
    "TELEFONO",
    "OBSERVACIONES"
]

# ============================================================
# FUNCIONES GENERALES
# ============================================================

def limpiar(valor):
    return "" if valor is None else str(valor)


def obtener_locales():
    locales = []

    for documento in db.collection("locales").stream():
        datos = documento.to_dict()

        datos["id"] = documento.id

        datos.setdefault("local", "")
        datos.setdefault("nombre", "")
        datos.setdefault("direccion", "")
        datos.setdefault("distrito", "")
        datos.setdefault("promotor", "")
        datos.setdefault("telefono", "")
        datos.setdefault("codigo", "")
        datos.setdefault("documentos", [])
        datos.setdefault("observaciones", "")

        locales.append(datos)

    locales.sort(
        key=lambda x: limpiar(x.get("local")).lower()
    )

    return locales


def documentos_del_local(local):

    docs = local.get("documentos", [])

    documento_anterior = limpiar(
        local.get("ruc_dni", "")
    ).strip()

    if documento_anterior and not any(
        limpiar(d.get("numero")) == documento_anterior
        for d in docs
        if isinstance(d, dict)
    ):

        docs = list(docs)

        docs.insert(
            0,
            {
                "tipo": "RUC/DNI",
                "numero": documento_anterior,
                "descripcion": "Documento registrado anteriormente",
                "fecha": ""
            }
        )

    resultado = []
    vistos = set()

    for d in docs:

        if not isinstance(d, dict):
            continue

        numero = limpiar(
            d.get("numero")
        ).strip()

        if not numero or numero in vistos:
            continue

        vistos.add(numero)

        resultado.append(
            {
                "tipo": limpiar(
                    d.get("tipo", "RUC/DNI")
                ),
                "numero": numero,
                "descripcion": limpiar(
                    d.get("descripcion", "")
                ),
                "fecha": limpiar(
                    d.get("fecha", "")
                )
            }
        )

    return resultado


def guardar_local(datos, local_id=None):

    if local_id:

        db.collection("locales").document(
            local_id
        ).set(
            datos,
            merge=True
        )

    else:

        db.collection("locales").add(
            datos
        )


def guardar_facturacion(datos):

    db.collection("facturacion").add(
        datos
    )


def guardar_visita(datos):

    db.collection("visitas").add(
        datos
    )


# ============================================================
# GENERAR EXCEL
# ============================================================

def crear_excel():

    facturacion = []

    for documento in db.collection(
        "facturacion"
    ).stream():

        x = documento.to_dict()

        facturacion.append(
            {
                "FECHA REGISTRO": limpiar(x.get("fecha_registro")),
                "CODIGO GESTOR": limpiar(x.get("codigo_gestor")),
                "LOCAL": limpiar(x.get("local")),
                "NOMBRE / RAZON SOCIAL": limpiar(x.get("nombre")),
                "TIPO DOCUMENTO": limpiar(x.get("documento_tipo")),
                "NUMERO DOCUMENTO": limpiar(x.get("documento_numero")),
                "DIRECCION": limpiar(x.get("direccion")),
                "DISTRITO": limpiar(x.get("distrito")),
                "FECHA EVENTO": limpiar(x.get("fecha_evento")),
                "TIPO EVENTO": limpiar(x.get("tipo_evento")),
                "MEDIO": limpiar(x.get("medio")),
                "ARTISTA/BANDA": limpiar(x.get("artista")),
                "MONTO": x.get("monto", 0),
                "TARIFA": x.get("tarifa", 0),
                "PAGO": limpiar(x.get("pago")),
                "BANCO": limpiar(x.get("banco")),
                "# OPERACION": limpiar(x.get("operacion")),
                "PROMOTOR": limpiar(x.get("promotor")),
                "TELEFONO": limpiar(x.get("telefono")),
                "OBSERVACIONES": limpiar(x.get("observaciones"))
            }
        )

    visitas = []

    for documento in db.collection(
        "visitas"
    ).stream():

        x = documento.to_dict()

        visitas.append(
            {
                "FECHA VISITA": limpiar(x.get("fecha_visita")),
                "HORA": limpiar(x.get("hora")),
                "CODIGO GESTOR": limpiar(x.get("codigo_gestor")),
                "LOCAL": limpiar(x.get("local")),
                "NOMBRE / RAZON SOCIAL": limpiar(x.get("nombre")),
                "TIPO DOCUMENTO": limpiar(x.get("documento_tipo")),
                "NUMERO DOCUMENTO": limpiar(x.get("documento_numero")),
                "DIRECCION": limpiar(x.get("direccion")),
                "DISTRITO": limpiar(x.get("distrito")),
                "RESULTADO VISITA": limpiar(x.get("resultado")),
                "HUBO EVENTO": limpiar(x.get("hubo_evento")),
                "QUIZO PAGAR": limpiar(x.get("quizo_pagar")),
                "SE DEJO CARTA": limpiar(x.get("se_dejo_carta")),
                "TIPO CARTA": limpiar(x.get("tipo_carta")),
                "CODIGO CARTA": limpiar(x.get("codigo_carta")),
                "FECHA EVENTO": limpiar(x.get("fecha_evento")),
                "TIPO EVENTO": limpiar(x.get("tipo_evento")),
                "MEDIO": limpiar(x.get("medio")),
                "ARTISTA/BANDA": limpiar(x.get("artista")),
                "MONTO": x.get("monto", 0),
                "TARIFA": x.get("tarifa", 0),
                "TARIFA CORRECTA": limpiar(x.get("tarifa_correcta")),
                "PAGO": limpiar(x.get("pago")),
                "BANCO": limpiar(x.get("banco")),
                "# OPERACION": limpiar(x.get("operacion")),
                "PROMOTOR": limpiar(x.get("promotor")),
                "TELEFONO": limpiar(x.get("telefono")),
                "OBSERVACIONES": limpiar(x.get("observacion"))
            }
        )

    df_facturacion = pd.DataFrame(
        facturacion,
        columns=COLUMNAS_FACTURACION
    )

    df_visitas = pd.DataFrame(
        visitas,
        columns=COLUMNAS_VISITAS
    )

    salida = BytesIO()

    with pd.ExcelWriter(
        salida,
        engine="openpyxl"
    ) as writer:

        df_facturacion.to_excel(
            writer,
            sheet_name="Facturacion",
            index=False
        )

        df_visitas.to_excel(
            writer,
            sheet_name="Visitas",
            index=False
        )

    salida.seek(0)

    return salida


# ============================================================
# TEXTO WHATSAPP
# ============================================================

def generar_whatsapp(
    datos
):

    texto = f"""APDAYC - DATOS PARA FACTURACIÓN

LOCAL: {datos["local"]}
RAZÓN SOCIAL: {datos["nombre"]}
DOCUMENTO: {datos["documento_tipo"]} - {datos["documento_numero"]}
DIRECCIÓN: {datos["direccion"]}
DISTRITO: {datos["distrito"]}

FECHA DEL EVENTO: {datos["fecha_evento"]}
TIPO DE EVENTO: {datos["tipo_evento"]}
MEDIO: {datos["medio"]}
ARTISTA/BANDA: {datos["artista"]}

MONTO: S/ {datos["monto"]:.2f}
TARIFA: S/ {datos["tarifa"]:.2f}
PAGO: {datos["pago"]}
BANCO: {datos["banco"]}
N.º OPERACIÓN: {datos["operacion"]}

PROMOTOR: {datos["promotor"]}
TELÉFONO: {datos["telefono"]}

OBSERVACIONES:
{datos["observaciones"]}
"""

    return texto


def boton_copiar_whatsapp(texto):

    texto_seguro = (
        texto
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("${", "\\${")
    )

    html = f"""
    <script>
    function copiarTexto() {{
        const texto = `{texto_seguro}`;

        navigator.clipboard.writeText(texto).then(
            function() {{
                document.getElementById("estado").innerText =
                "✅ COPIADO. Ahora abre WhatsApp y pega el mensaje.";
            }},
            function() {{
                document.getElementById("estado").innerText =
                "⚠️ No se pudo copiar automáticamente. Usa el botón de copiar del cuadro.";
            }}
        );
    }}
    </script>

    <button
        onclick="copiarTexto()"
        style="
            width:100%;
            padding:12px;
            font-size:18px;
            font-weight:bold;
            border-radius:8px;
            border:1px solid #999;
            cursor:pointer;
        "
    >
        📋 COPIAR PARA WHATSAPP
    </button>

    <p id="estado"></p>
    """

    components.html(
        html,
        height=100
    )


# ============================================================
# ACCESO
# ============================================================

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False


if not st.session_state.autenticado:

    st.title(
        "🎵 APDAYC - Control Territorial"
    )

    st.subheader(
        "🔐 Ingreso de gestor"
    )

    codigo = st.text_input(
        "Código de gestor",
        value=CODIGO_GESTOR
    )

    clave = st.text_input(
        "Contraseña",
        type="password"
    )

    if st.button(
        "INGRESAR",
        use_container_width=True
    ):

        if (
            codigo in USUARIOS_PILOTO
            and clave == USUARIOS_PILOTO[codigo]
        ):

            st.session_state.autenticado = True
            st.session_state.codigo_gestor = codigo

            st.rerun()

        else:

            st.error(
                "Código o contraseña incorrectos."
            )

    st.stop()


# ============================================================
# CABECERA
# ============================================================

st.title(
    "🎵 APDAYC - Control Territorial"
)

st.caption(
    f"Gestión territorial | Código de gestor: "
    f"{st.session_state.codigo_gestor}"
)

if st.button(
    "🔒 CERRAR SESIÓN"
):

    st.session_state.autenticado = False
    st.rerun()


# ============================================================
# MENÚ PRINCIPAL
# ============================================================

opcion = st.radio(
    "MENÚ",
    [
        "📊 Panel de ruta",
        "📲 Mandar a facturar",
        "🚗 Visitas",
        "🏪 Locales",
        "📥 Exportar Excel"
    ],
    horizontal=True
)


# ============================================================
# PANEL DE RUTA
# ============================================================

if opcion == "📊 Panel de ruta":

    st.subheader(
        "📊 Panel de ruta"
    )

    hoy = str(date.today())

    visitas = []

    for documento in db.collection(
        "visitas"
    ).stream():

        x = documento.to_dict()

        if limpiar(
            x.get("fecha_visita")
        ) == hoy:

            visitas.append(x)

    total = len(visitas)

    con_evento = sum(
        1
        for x in visitas
        if x.get("hubo_evento") == "Sí"
    )

    sin_evento = sum(
        1
        for x in visitas
        if x.get("resultado") == "Sin evento"
    )

    no_pago = sum(
        1
        for x in visitas
        if x.get("quizo_pagar") == "No"
    )

    cartas = sum(
        1
        for x in visitas
        if x.get("se_dejo_carta") == "Sí"
    )

    monto = sum(
        float(x.get("monto", 0) or 0)
        for x in visitas
    )

    locales_hoy = set(
        limpiar(x.get("local_id"))
        for x in visitas
    )

    locales_hoy.discard("")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Visitas hoy",
        total
    )

    c2.metric(
        "Con evento",
        con_evento
    )

    c3.metric(
        "Sin evento",
        sin_evento
    )

    c4.metric(
        "Cartas",
        cartas
    )

    c5, c6, c7 = st.columns(3)

    c5.metric(
        "No quisieron pagar",
        no_pago
    )

    c6.metric(
        "Monto registrado",
        f"S/ {monto:,.2f}"
    )

    c7.metric(
        "Locales visitados",
        len(locales_hoy)
    )

    st.divider()

    if visitas:

        filas = []

        for x in sorted(
            visitas,
            key=lambda z: limpiar(
                z.get("hora")
            ),
            reverse=True
        ):

            filas.append(
                {
                    "Hora": limpiar(
                        x.get("hora")
                    ),
                    "Local": limpiar(
                        x.get("local")
                    ),
                    "Resultado": limpiar(
                        x.get("resultado")
                    ),
                    "Evento": limpiar(
                        x.get("hubo_evento")
                    ),
                    "Pagó": limpiar(
                        x.get("quizo_pagar")
                    ),
                    "Carta": limpiar(
                        x.get("se_dejo_carta")
                    ),
                    "Monto": float(
                        x.get("monto", 0) or 0
                    )
                }
            )

        st.dataframe(
            filas,
            use_container_width=True
        )

    else:

        st.info(
            "Todavía no hay visitas registradas hoy."
        )


# ============================================================
# MANDAR A FACTURAR
# ============================================================

elif opcion == "📲 Mandar a facturar":

    st.subheader(
        "📲 Mandar a facturar"
    )

    st.info(
        "Usa esta pestaña cuando el evento ya fue informado "
        "y el pago llegó antes de realizar la visita."
    )

    locales = obtener_locales()

    if not locales:

        st.warning(
            "Primero registra un local."
        )

        st.stop()

    opciones_locales = {
        f"{x['local']} | {x['distrito']} | {x['direccion']}": x
        for x in locales
    }

    seleccionado = st.selectbox(
        "🏪 LOCAL",
        ["Seleccionar"] + list(
            opciones_locales.keys()
        )
    )

    if seleccionado == "Seleccionar":

        st.info(
            "Selecciona el local."
        )

        st.stop()

    datos_local = opciones_locales[
        seleccionado
    ]

    st.success(
        "✅ Datos del local cargados"
    )

    st.write(
        f"**Local:** {datos_local['local']}"
    )

    st.write(
        f"**Dirección:** {datos_local['direccion']} | "
        f"**Distrito:** {datos_local['distrito']}"
    )

    st.write(
        f"**Promotor:** {datos_local['promotor']} | "
        f"**Teléfono:** {datos_local['telefono']}"
    )

    documentos = documentos_del_local(
        datos_local
    )

    opciones_documentos = []

    for d in documentos:

        etiqueta = (
            f"{d['tipo']} — {d['numero']}"
        )

        if d["descripcion"]:

            etiqueta += (
                f" — {d['descripcion']}"
            )

        opciones_documentos.append(
            etiqueta
        )

    opciones_documentos.append(
        "➕ Agregar nuevo documento"
    )

    documento_elegido = st.selectbox(
        "🪪 DOCUMENTO",
        opciones_documentos
    )

    documento_tipo = ""
    documento_numero = ""
    documento_descripcion = ""

    if documento_elegido == "➕ Agregar nuevo documento":

        c1, c2, c3 = st.columns(
            [1, 2, 2]
        )

        with c1:

            documento_tipo = st.selectbox(
                "TIPO",
                ["RUC", "DNI", "Otro"]
            )

        with c2:

            documento_numero = st.text_input(
                "NÚMERO"
            )

        with c3:

            documento_descripcion = st.text_input(
                "DESCRIPCIÓN"
            )

    else:

        indice = opciones_documentos.index(
            documento_elegido
        )

        d = documentos[indice]

        documento_tipo = d["tipo"]
        documento_numero = d["numero"]
        documento_descripcion = d["descripcion"]

    st.divider()

    fecha_evento = st.date_input(
        "📅 FECHA DEL EVENTO",
        value=date.today()
    )

    tipo_evento = st.selectbox(
        "🎤 TIPO DE EVENTO",
        [
            "Seleccionar",
            "Evento musical",
            "Concierto",
            "Fiesta",
            "Aniversario",
            "Matrimonio",
            "Quinceañero",
            "Evento costumbrista",
            "Evento religioso",
            "Otro"
        ]
    )

    medio = st.selectbox(
        "🎵 MEDIO",
        [
            "Seleccionar",
            "Medios mecánicos",
            "Medios humanos"
        ]
    )

    artista = ""

    if medio == "Medios humanos":

        artista = st.text_input(
            "ARTISTA / BANDA / GRUPO"
        )

    c1, c2 = st.columns(2)

    with c1:

        monto = st.number_input(
            "💰 MONTO PAGADO",
            min_value=0.0,
            step=10.0
        )

    with c2:

        tarifa = st.number_input(
            "💵 TARIFA",
            min_value=0.0,
            step=10.0
        )

    c1, c2, c3 = st.columns(3)

    with c1:

        pago = st.selectbox(
            "PAGO",
            [
                "Pagado",
                "Pendiente",
                "Pago parcial"
            ]
        )

    with c2:

        banco = st.selectbox(
            "BANCO",
            [
                "No corresponde",
                "BCP",
                "BBVA",
                "Interbank",
                "Scotiabank",
                "Otro"
            ]
        )

    with c3:

        operacion = st.text_input(
            "N.º DE OPERACIÓN"
        )

    observaciones = st.text_area(
        "OBSERVACIONES"
    )

    if st.button(
        "📲 GUARDAR Y GENERAR WHATSAPP",
        use_container_width=True
    ):

        if not documento_numero.strip():

            st.error(
                "Debes seleccionar o ingresar un documento."
            )

        elif tipo_evento == "Seleccionar":

            st.error(
                "Selecciona el tipo de evento."
            )

        elif medio == "Seleccionar":

            st.error(
                "Selecciona el medio."
            )

        else:

            datos_facturacion = {

                "fecha_registro": str(
                    date.today()
                ),

                "codigo_gestor":
                    st.session_state.codigo_gestor,

                "local":
                    datos_local["local"],

                "nombre":
                    datos_local["nombre"],

                "documento_tipo":
                    documento_tipo,

                "documento_numero":
                    documento_numero.strip(),

                "direccion":
                    datos_local["direccion"],

                "distrito":
                    datos_local["distrito"],

                "fecha_evento":
                    str(fecha_evento),

                "tipo_evento":
                    tipo_evento,

                "medio":
                    medio,

                "artista":
                    artista,

                "monto":
                    monto,

                "tarifa":
                    tarifa,

                "pago":
                    pago,

                "banco":
                    banco,

                "operacion":
                    operacion.strip(),

                "promotor":
                    datos_local["promotor"],

                "telefono":
                    datos_local["telefono"],

                "observaciones":
                    observaciones.strip()
            }

            guardar_facturacion(
                datos_facturacion
            )

            # Guardar documento nuevo
            if documento_elegido == "➕ Agregar nuevo documento":

                nuevos_documentos = list(
                    documentos
                )

                nuevos_documentos.append(
                    {
                        "tipo":
                            documento_tipo,

                        "numero":
                            documento_numero.strip(),

                        "descripcion":
                            documento_descripcion.strip(),

                        "fecha":
                            str(date.today())
                    }
                )

                db.collection(
                    "locales"
                ).document(
                    datos_local["id"]
                ).set(
                    {
                        "documentos":
                            nuevos_documentos
                    },
                    merge=True
                )

            st.success(
                "✅ FACTURACIÓN GUARDADA CORRECTAMENTE"
            )

            texto_whatsapp = generar_whatsapp(
                datos_facturacion
            )

            st.markdown(
                "### 📲 Mensaje para WhatsApp"
            )

            st.text_area(
                "Puedes copiar este mensaje:",
                value=texto_whatsapp,
                height=350
            )

            boton_copiar_whatsapp(
                texto_whatsapp
            )


# ============================================================
# VISITAS
# ============================================================

elif opcion == "🚗 Visitas":

    st.subheader(
        "🚗 Registrar visita"
    )

    st.info(
        "Esta pestaña sirve para registrar lo que realmente "
        "encontraste en campo y corroborar los pagos/eventos."
    )

    locales = obtener_locales()

    if not locales:

        st.warning(
            "Primero registra al menos un local."
        )

        st.stop()

    opciones_locales = {
        f"{x['local']} | {x['distrito']} | {x['direccion']}": x
        for x in locales
    }

    seleccionado = st.selectbox(
        "🏪 SELECCIONA EL LOCAL",
        ["Seleccionar"] + list(
            opciones_locales.keys()
        )
    )

    if seleccionado == "Seleccionar":

        st.info(
            "Selecciona un local."
        )

        st.stop()

    datos_local = opciones_locales[
        seleccionado
    ]

    st.success(
        "✅ Datos del local cargados automáticamente"
    )

    c1, c2, c3 = st.columns(3)

    c1.write(
        f"**Local:** {datos_local['local']}"
    )

    c2.write(
        f"**Dirección:** {datos_local['direccion']}"
    )

    c3.write(
        f"**Distrito:** {datos_local['distrito']}"
    )

    st.write(
        f"**Razón social:** {datos_local['nombre']}"
    )

    st.write(
        f"**Promotor:** {datos_local['promotor']} | "
        f"**Teléfono:** {datos_local['telefono']}"
    )

    documentos = documentos_del_local(
        datos_local
    )

    st.markdown(
        "### 🪪 Documento"
    )

    opciones_documentos = []

    for d in documentos:

        etiqueta = (
            f"{d['tipo']} — {d['numero']}"
        )

        if d["descripcion"]:

            etiqueta += (
                f" — {d['descripcion']}"
            )

        opciones_documentos.append(
            etiqueta
        )

    opciones_documentos.append(
        "➕ Agregar nuevo documento"
    )

    documento_elegido = st.selectbox(
        "Documento",
        opciones_documentos
    )

    documento_tipo = ""
    documento_numero = ""
    documento_descripcion = ""

    if documento_elegido == "➕ Agregar nuevo documento":

        c1, c2, c3 = st.columns(
            [1, 2, 2]
        )

        with c1:

            documento_tipo = st.selectbox(
                "TIPO",
                ["RUC", "DNI", "Otro"]
            )

        with c2:

            documento_numero = st.text_input(
                "NÚMERO"
            )

        with c3:

            documento_descripcion = st.text_input(
                "DESCRIPCIÓN"
            )

    else:

        indice = opciones_documentos.index(
            documento_elegido
        )

        d = documentos[indice]

        documento_tipo = d["tipo"]
        documento_numero = d["numero"]
        documento_descripcion = d["descripcion"]

    st.divider()

    st.markdown(
        "### 📍 Resultado de la visita"
    )

    resultado = st.selectbox(
        "RESULTADO DE VISITA",
        [
            "Con evento",
            "Sin evento",
            "Evento pero no quiso pagar",
            "No atendió",
            "Otro"
        ]
    )

    hubo_evento = (
        "Sí"
        if resultado in [
            "Con evento",
            "Evento pero no quiso pagar"
        ]
        else "No"
    )

    if hubo_evento == "Sí":

        quizo_pagar = st.selectbox(
            "¿QUIZO PAGAR?",
            [
                "Sí",
                "No",
                "Pendiente"
            ]
        )

    else:

        quizo_pagar = "No corresponde"

    se_dejo_carta = st.checkbox(
        "📄 ¿SE DEJÓ CARTA / NOTIFICACIÓN?"
    )

    tipo_carta = ""
    codigo_carta = ""

    if se_dejo_carta:

        tipo_carta = st.selectbox(
            "TIPO DE CARTA",
            [
                "Uso no autorizado",
                "Notificación",
                "Requerimiento",
                "Otro"
            ]
        )

        codigo_carta = st.text_input(
            "CÓDIGO DE CARTA"
        )

    observacion = st.text_area(
        "OBSERVACIONES DE LA VISITA"
    )

    # ========================================================
    # DATOS EVENTO
    # ========================================================

    if hubo_evento == "Sí":

        st.divider()

        st.markdown(
            "### 🎤 Datos del evento"
        )

        fecha_evento = st.date_input(
            "FECHA DEL EVENTO",
            value=date.today()
        )

        tipo_evento = st.selectbox(
            "TIPO DE EVENTO",
            [
                "Seleccionar",
                "Evento musical",
                "Concierto",
                "Fiesta",
                "Aniversario",
                "Matrimonio",
                "Quinceañero",
                "Evento costumbrista",
                "Evento religioso",
                "Otro"
            ]
        )

        medio = st.selectbox(
            "MEDIO",
            [
                "Seleccionar",
                "Medios mecánicos",
                "Medios humanos"
            ]
        )

        artista = ""

        if medio == "Medios humanos":

            artista = st.text_input(
                "ARTISTA / BANDA / GRUPO"
            )

        c1, c2, c3 = st.columns(3)

        with c1:

            monto = st.number_input(
                "MONTO",
                min_value=0.0,
                step=10.0
            )

        with c2:

            tarifa = st.number_input(
                "TARIFA",
                min_value=0.0,
                step=10.0
            )

        with c3:

            tarifa_correcta = st.selectbox(
                "¿TARIFA CORRECTA?",
                [
                    "Pendiente de revisión",
                    "Sí",
                    "No"
                ]
            )

        c1, c2, c3 = st.columns(3)

        with c1:

            pago = st.selectbox(
                "PAGO",
                [
                    "Pagado",
                    "Pendiente",
                    "Pago parcial"
                ]
            )

        with c2:

            banco = st.selectbox(
                "BANCO",
                [
                    "No corresponde",
                    "BCP",
                    "BBVA",
                    "Interbank",
                    "Scotiabank",
                    "Otro"
                ]
            )

        with c3:

            operacion = st.text_input(
                "N.º DE OPERACIÓN"
            )

    else:

        fecha_evento = date.today()
        tipo_evento = ""
        medio = ""
        artista = ""
        monto = 0.0
        tarifa = 0.0
        tarifa_correcta = "Pendiente de revisión"
        pago = "Pendiente"
        banco = "No corresponde"
        operacion = ""

    st.divider()

    if st.button(
        "💾 GUARDAR VISITA",
        use_container_width=True
    ):

        if not documento_numero.strip():

            st.error(
                "Selecciona un documento o agrega uno nuevo."
            )

        elif hubo_evento == "Sí" and tipo_evento == "Seleccionar":

            st.error(
                "Debes seleccionar el tipo de evento."
            )

        elif hubo_evento == "Sí" and medio == "Seleccionar":

            st.error(
                "Debes seleccionar el medio."
            )

        elif se_dejo_carta and not codigo_carta.strip():

            st.error(
                "Ingresa el código de carta."
            )

        else:

            ahora = datetime.now()

            datos_visita = {

                # FECHA REAL DE LA VISITA
                "fecha_visita":
                    str(date.today()),

                "hora":
                    ahora.strftime("%H:%M:%S"),

                "codigo_gestor":
                    st.session_state.codigo_gestor,

                "local_id":
                    datos_local["id"],

                "local":
                    datos_local["local"],

                "nombre":
                    datos_local["nombre"],

                "documento_tipo":
                    documento_tipo,

                "documento_numero":
                    documento_numero.strip(),

                "documento_descripcion":
                    documento_descripcion.strip(),

                "direccion":
                    datos_local["direccion"],

                "distrito":
                    datos_local["distrito"],

                "resultado":
                    resultado,

                "hubo_evento":
                    hubo_evento,

                "quizo_pagar":
                    quizo_pagar,

                "se_dejo_carta":
                    "Sí"
                    if se_dejo_carta
                    else "No",

                "tipo_carta":
                    tipo_carta,

                "codigo_carta":
                    codigo_carta.strip(),

                "fecha_evento":
                    str(fecha_evento),

                "tipo_evento":
                    tipo_evento,

                "medio":
                    medio,

                "artista":
                    artista,

                "monto":
                    monto,

                "tarifa":
                    tarifa,

                "tarifa_correcta":
                    tarifa_correcta,

                "pago":
                    pago,

                "banco":
                    banco,

                "operacion":
                    operacion.strip(),

                "promotor":
                    datos_local["promotor"],

                "telefono":
                    datos_local["telefono"],

                "observacion":
                    observacion.strip()
            }

            guardar_visita(
                datos_visita
            )

            # Guardar documento nuevo
            if documento_elegido == "➕ Agregar nuevo documento":

                nuevos_documentos = list(
                    documentos
                )

                nuevos_documentos.append(
                    {
                        "tipo":
                            documento_tipo,

                        "numero":
                            documento_numero.strip(),

                        "descripcion":
                            documento_descripcion.strip(),

                        "fecha":
                            str(date.today())
                    }
                )

                db.collection(
                    "locales"
                ).document(
                    datos_local["id"]
                ).set(
                    {
                        "documentos":
                            nuevos_documentos
                    },
                    merge=True
                )

            st.success(
                "✅ VISITA GUARDADA CORRECTAMENTE"
            )

            st.info(
                "La visita ya quedó registrada y aparecerá "
                "en el Panel de ruta."
            )


# ============================================================
# LOCALES
# ============================================================

elif opcion == "🏪 Locales":

    st.subheader(
        "🏪 Locales"
    )

    locales = obtener_locales()

    modo = st.radio(
        "¿Qué deseas hacer?",
        [
            "➕ Nuevo local",
            "✏️ Actualizar local"
        ],
        horizontal=True
    )

    local_editar = None

    if modo == "✏️ Actualizar local":

        if not locales:

            st.warning(
                "No hay locales registrados."
            )

            st.stop()

        opciones = {
            f"{x['local']} | {x['direccion']} | {x['distrito']}": x
            for x in locales
        }

        elegido = st.selectbox(
            "Selecciona el local",
            list(opciones.keys())
        )

        local_editar = opciones[
            elegido
        ]

    if local_editar:

        valor_local = local_editar.get(
            "local",
            ""
        )

        valor_nombre = local_editar.get(
            "nombre",
            ""
        )

        valor_direccion = local_editar.get(
            "direccion",
            ""
        )

        valor_distrito = local_editar.get(
            "distrito",
            ""
        )

        valor_promotor = local_editar.get(
            "promotor",
            ""
        )

        valor_telefono = local_editar.get(
            "telefono",
            ""
        )

        valor_codigo = local_editar.get(
            "codigo",
            ""
        )

        valor_obs = local_editar.get(
            "observaciones",
            ""
        )

        documentos = documentos_del_local(
            local_editar
        )

    else:

        valor_local = ""
        valor_nombre = ""
        valor_direccion = ""
        valor_distrito = ""
        valor_promotor = ""
        valor_telefono = ""
        valor_codigo = ""
        valor_obs = ""
        documentos = []

    st.markdown(
        "### 🏪 Datos del local"
    )

    col1, col2 = st.columns(2)

    with col1:

        local = st.text_input(
            "LOCAL",
            value=valor_local
        )

        nombre = st.text_input(
            "NOMBRE / RAZÓN SOCIAL",
            value=valor_nombre
        )

        direccion = st.text_input(
            "DIRECCIÓN",
            value=valor_direccion
        )

        distrito = st.text_input(
            "DISTRITO",
            value=valor_distrito
        )

    with col2:

        promotor = st.text_input(
            "PROMOTOR",
            value=valor_promotor
        )

        telefono = st.text_input(
            "TELÉFONO",
            value=valor_telefono
        )

        codigo = st.text_input(
            "CÓDIGO DEL LOCAL",
            value=valor_codigo
        )

        observaciones_local = st.text_area(
            "OBSERVACIONES DEL LOCAL",
            value=valor_obs
        )

    st.divider()

    st.markdown(
        "### 🪪 Documentos guardados"
    )

    if documentos:

        for d in documentos:

            etiqueta = (
                f"{d['tipo']} — {d['numero']}"
            )

            if d["descripcion"]:

                etiqueta += (
                    f" — {d['descripcion']}"
                )

            st.write(
                f"• {etiqueta}"
            )

    else:

        st.info(
            "Este local todavía no tiene documentos."
        )

    st.markdown(
        "#### ➕ Agregar documento"
    )

    c1, c2, c3 = st.columns(
        [1, 2, 2]
    )

    with c1:

        tipo_documento = st.selectbox(
            "TIPO",
            [
                "RUC",
                "DNI",
                "Otro"
            ]
        )

    with c2:

        numero_documento = st.text_input(
            "NÚMERO DEL DOCUMENTO"
        )

    with c3:

        descripcion_documento = st.text_input(
            "DESCRIPCIÓN"
        )

    if st.button(
        "💾 GUARDAR LOCAL",
        use_container_width=True
    ):

        if not local.strip():

            st.error(
                "Debes ingresar el LOCAL."
            )

        elif not nombre.strip():

            st.error(
                "Debes ingresar el NOMBRE / RAZÓN SOCIAL."
            )

        elif not distrito.strip():

            st.error(
                "Debes ingresar el DISTRITO."
            )

        else:

            documentos_actualizados = list(
                documentos
            )

            numero = numero_documento.strip()

            if numero:

                if any(
                    d["numero"] == numero
                    for d in documentos_actualizados
                ):

                    st.warning(
                        "Ese documento ya está guardado."
                    )

                else:

                    documentos_actualizados.append(
                        {
                            "tipo":
                                tipo_documento,

                            "numero":
                                numero,

                            "descripcion":
                                descripcion_documento.strip(),

                            "fecha":
                                str(date.today())
                        }
                    )

            datos_local = {

                "local":
                    local.strip(),

                "nombre":
                    nombre.strip(),

                "direccion":
                    direccion.strip(),

                "distrito":
                    distrito.strip(),

                "promotor":
                    promotor.strip(),

                "telefono":
                    telefono.strip(),

                "codigo":
                    codigo.strip(),

                "observaciones":
                    observaciones_local.strip(),

                "documentos":
                    documentos_actualizados,

                "actualizado":
                    datetime.now().isoformat()
            }

            guardar_local(
                datos_local,
                local_editar["id"]
                if local_editar
                else None
            )

            st.success(
                "✅ LOCAL GUARDADO CORRECTAMENTE"
            )

            st.rerun()


# ============================================================
# EXPORTAR EXCEL
# ============================================================

elif opcion == "📥 Exportar Excel":

    st.subheader(
        "📥 Exportar información"
    )

    st.info(
        "El archivo contiene dos hojas: "
        "Facturacion y Visitas."
    )

    excel = crear_excel()

    st.download_button(
        label="📥 DESCARGAR EXCEL",
        data=excel,
        file_name=f"APDAYC_Control_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
```
