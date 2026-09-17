import streamlit as st
import csv
import os
from datetime import date, datetime
import firebase_admin
from firebase_admin import credentials, firestore

# ============================================================
# FIREBASE
# ============================================================

if not firebase_admin._apps:
    cred = credentials.Certificate(st.secrets["firebase"])
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

ARCHIVO = "eventos.csv"
CODIGO_GESTOR = "LN14"

# PILOTO: cambia esta contraseña antes de poner la aplicación
# en producción.
USUARIOS_PILOTO = {
    "LN14": "1234"
}

COLUMNAS = [
    "FECHA",
    "CODIGO GESTOR",
    "LOCAL",
    "NOMBRE / RAZON SOCIAL",
    "DOCUMENTO SELECCIONADO",
    "DIRECCION",
    "DISTRITO",
    "RESULTADO VISITA",
    "HUBO EVENTO",
    "QUIZO PAGAR",
    "SE DEJO CARTA",
    "TIPO CARTA",
    "CODIGO CARTA",
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

if not os.path.exists(ARCHIVO) or os.path.getsize(ARCHIVO) == 0:
    with open(ARCHIVO, "w", newline="", encoding="utf-8-sig") as archivo:
        csv.writer(archivo).writerow(COLUMNAS)

# ============================================================
# FUNCIONES
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
    locales.sort(key=lambda x: limpiar(x.get("local")).lower())
    return locales

def documentos_del_local(local):
    docs = local.get("documentos", [])

    # Compatibilidad con locales creados con la versión anterior:
    documento_anterior = limpiar(local.get("ruc_dni", "")).strip()
    if documento_anterior and not any(
        limpiar(d.get("numero")) == documento_anterior
        for d in docs if isinstance(d, dict)
    ):
        docs = list(docs)
        docs.insert(0, {
            "tipo": "RUC/DNI",
            "numero": documento_anterior,
            "descripcion": "Documento registrado anteriormente",
            "fecha": ""
        })

    resultado = []
    vistos = set()

    for d in docs:
        if not isinstance(d, dict):
            continue
        numero = limpiar(d.get("numero")).strip()
        if not numero or numero in vistos:
            continue
        vistos.add(numero)
        resultado.append({
            "tipo": limpiar(d.get("tipo", "RUC/DNI")),
            "numero": numero,
            "descripcion": limpiar(d.get("descripcion", "")),
            "fecha": limpiar(d.get("fecha", ""))
        })

    return resultado

def guardar_local(datos, local_id=None):
    if local_id:
        db.collection("locales").document(local_id).set(datos, merge=True)
    else:
        db.collection("locales").add(datos)

def guardar_evento(datos):
    db.collection("eventos").add(datos)

def contar_resumen():
    hoy = str(date.today())
    visitas_hoy = []

    for documento in db.collection("eventos").stream():
        datos = documento.to_dict()
        if limpiar(datos.get("fecha")) == hoy:
            visitas_hoy.append(datos)

    return visitas_hoy

def guardar_csv(fila):
    with open(ARCHIVO, "a", newline="", encoding="utf-8-sig") as archivo:
        csv.writer(archivo).writerow(fila)

# ============================================================
# ACCESO PILOTO
# ============================================================

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🎵 APDAYC - Control Territorial")
    st.subheader("🔐 Ingreso de gestor")

    codigo = st.text_input("Código de gestor", value=CODIGO_GESTOR)
    clave = st.text_input("Contraseña", type="password")

    if st.button("INGRESAR", use_container_width=True):
        if codigo in USUARIOS_PILOTO and clave == USUARIOS_PILOTO[codigo]:
            st.session_state.autenticado = True
            st.session_state.codigo_gestor = codigo
            st.rerun()
        else:
            st.error("Código o contraseña incorrectos.")

    st.caption("Piloto actual: código LN14. La contraseña inicial está definida en app.py.")
    st.stop()

# ============================================================
# CABECERA
# ============================================================

st.title("🎵 APDAYC - Control Territorial")
st.caption(f"Gestión territorial | Código de gestor: {st.session_state.codigo_gestor}")

if st.button("🔒 CERRAR SESIÓN"):
    st.session_state.autenticado = False
    st.rerun()

# ============================================================
# MENÚ
# ============================================================

opcion = st.radio(
    "Selecciona una opción",
    [
        "📊 Panel de ruta",
        "🏪 Locales",
        "🚗 Registrar visita"
    ],
    horizontal=True
)

# ============================================================
# PANEL DE RUTA
# ============================================================

if opcion == "📊 Panel de ruta":
    st.subheader("📊 Panel de ruta")

    visitas = contar_resumen()
    total = len(visitas)

    con_evento = sum(1 for x in visitas if x.get("hubo_evento") == "Sí")
    sin_evento = sum(1 for x in visitas if x.get("resultado") == "Sin evento")
    no_pago = sum(1 for x in visitas if x.get("quizo_pagar") == "No")
    cartas = sum(1 for x in visitas if x.get("se_dejo_carta") == "Sí")
    monto = sum(float(x.get("monto", 0) or 0) for x in visitas)

    locales_hoy = set(limpiar(x.get("local_id")) for x in visitas)
    locales_hoy.discard("")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Visitas hoy", total)
    c2.metric("Con evento", con_evento)
    c3.metric("Sin evento", sin_evento)
    c4.metric("Cartas", cartas)

    c5, c6, c7 = st.columns(3)
    c5.metric("No quisieron pagar", no_pago)
    c6.metric("Monto cobrado", f"S/ {monto:,.2f}")
    c7.metric("Locales visitados", len(locales_hoy))

    st.divider()
    st.info("El historial no se reemplaza: cada visita queda guardada como un registro independiente.")

    if visitas:
        filas = []
        for x in sorted(visitas, key=lambda z: limpiar(z.get("hora")), reverse=True):
            filas.append({
                "Hora": limpiar(x.get("hora")),
                "Local": limpiar(x.get("local")),
                "Resultado": limpiar(x.get("resultado")),
                "Evento": limpiar(x.get("hubo_evento")),
                "Pagó": limpiar(x.get("quizo_pagar")),
                "Carta": limpiar(x.get("se_dejo_carta")),
                "Monto": float(x.get("monto", 0) or 0)
            })
        st.dataframe(filas, use_container_width=True)
    else:
        st.warning("Todavía no hay visitas registradas hoy.")

# ============================================================
# LOCALES
# ============================================================

elif opcion == "🏪 Locales":
    st.subheader("🏪 Locales")

    locales = obtener_locales()

    modo = st.radio(
        "¿Qué deseas hacer?",
        ["➕ Nuevo local", "✏️ Actualizar local"],
        horizontal=True
    )

    local_editar = None

    if modo == "✏️ Actualizar local":
        if not locales:
            st.warning("No hay locales registrados todavía.")
            st.stop()

        opciones = {
            f"{x['local']} | {x['direccion']} | {x['distrito']}": x
            for x in locales
        }
        elegido = st.selectbox("Selecciona el local", list(opciones.keys()))
        local_editar = opciones[elegido]

    if local_editar:
        valor_local = local_editar.get("local", "")
        valor_nombre = local_editar.get("nombre", "")
        valor_direccion = local_editar.get("direccion", "")
        valor_distrito = local_editar.get("distrito", "")
        valor_promotor = local_editar.get("promotor", "")
        valor_telefono = local_editar.get("telefono", "")
        valor_codigo = local_editar.get("codigo", "")
        valor_obs = local_editar.get("observaciones", "")
        documentos = documentos_del_local(local_editar)
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

    st.markdown("### 🏪 Datos del local")

    col1, col2 = st.columns(2)
    with col1:
        local = st.text_input("LOCAL", value=valor_local)
        nombre = st.text_input("NOMBRE / RAZÓN SOCIAL", value=valor_nombre)
        direccion = st.text_input("DIRECCIÓN", value=valor_direccion)
        distrito = st.text_input("DISTRITO", value=valor_distrito)

    with col2:
        promotor = st.text_input("PROMOTOR", value=valor_promotor)
        telefono = st.text_input("TELÉFONO", value=valor_telefono)
        codigo = st.text_input("CÓDIGO DEL LOCAL", value=valor_codigo)
        observaciones_local = st.text_area("OBSERVACIONES DEL LOCAL", value=valor_obs)

    st.divider()
    st.markdown("### 🪪 Documentos guardados del local")

    if documentos:
        for d in documentos:
            etiqueta = f"{d['tipo']} — {d['numero']}"
            if d["descripcion"]:
                etiqueta += f" — {d['descripcion']}"
            st.write(f"• {etiqueta}")
    else:
        st.info("Este local todavía no tiene documentos guardados.")

    st.markdown("#### ➕ Agregar documento")
    c1, c2, c3 = st.columns([1, 2, 2])

    with c1:
        tipo_documento = st.selectbox("TIPO", ["RUC", "DNI", "Otro"])
    with c2:
        numero_documento = st.text_input("NÚMERO DEL DOCUMENTO")
    with c3:
        descripcion_documento = st.text_input(
            "DESCRIPCIÓN",
            placeholder="Ej.: RUC del local / DNI responsable"
        )

    guardar = st.button(
        "💾 GUARDAR LOCAL",
        use_container_width=True
    )

    if guardar:
        if not local.strip():
            st.error("Debes ingresar el LOCAL.")
        elif not nombre.strip():
            st.error("Debes ingresar el NOMBRE / RAZÓN SOCIAL.")
        elif not distrito.strip():
            st.error("Debes ingresar el DISTRITO.")
        else:
            documentos_actualizados = list(documentos)

            numero = numero_documento.strip()
            if numero:
                if any(d["numero"] == numero for d in documentos_actualizados):
                    st.warning("Ese documento ya está guardado para este local.")
                else:
                    documentos_actualizados.append({
                        "tipo": tipo_documento,
                        "numero": numero,
                        "descripcion": descripcion_documento.strip(),
                        "fecha": str(date.today())
                    })

            datos_local = {
                "local": local.strip(),
                "nombre": nombre.strip(),
                "direccion": direccion.strip(),
                "distrito": distrito.strip(),
                "promotor": promotor.strip(),
                "telefono": telefono.strip(),
                "codigo": codigo.strip(),
                "observaciones": observaciones_local.strip(),
                "documentos": documentos_actualizados,
                "actualizado": datetime.now().isoformat()
            }

            guardar_local(
                datos_local,
                local_editar["id"] if local_editar else None
            )

            st.success("✅ LOCAL GUARDADO CORRECTAMENTE")
            st.rerun()

# ============================================================
# REGISTRAR VISITA
# ============================================================

else:
    st.subheader("🚗 Registrar visita")

    locales = obtener_locales()

    if not locales:
        st.warning("Primero registra al menos un local en 🏪 Locales.")
        st.stop()

    # Usamos ID de Firestore para evitar problemas si existen
    # dos locales con nombres parecidos o iguales.
    opciones_locales = {
        f"{x['local']} | {x['distrito']} | {x['direccion']}": x
        for x in locales
    }

    seleccionado = st.selectbox(
        "🏪 SELECCIONA EL LOCAL",
        ["Seleccionar"] + list(opciones_locales.keys())
    )

    if seleccionado == "Seleccionar":
        st.info("Selecciona un local para cargar automáticamente sus datos.")
        st.stop()

    datos_local = opciones_locales[seleccionado]

    st.success("✅ Datos del local cargados automáticamente")

    c1, c2, c3 = st.columns(3)
    c1.write(f"**Local:** {datos_local['local']}")
    c2.write(f"**Dirección:** {datos_local['direccion']}")
    c3.write(f"**Distrito:** {datos_local['distrito']}")

    st.write(f"**Razón social:** {datos_local['nombre']}")
    st.write(f"**Promotor:** {datos_local['promotor']} | **Teléfono:** {datos_local['telefono']}")

    # ========================================================
    # DOCUMENTO DESPLEGABLE
    # ========================================================

    documentos = documentos_del_local(datos_local)

    st.markdown("### 🪪 Documento para esta visita")

    opciones_documentos = []

    for d in documentos:
        etiqueta = f"{d['tipo']} — {d['numero']}"
        if d["descripcion"]:
            etiqueta += f" — {d['descripcion']}"
        opciones_documentos.append(etiqueta)

    opciones_documentos.append("➕ Agregar nuevo documento")

    documento_elegido = st.selectbox(
        "Documento registrado",
        opciones_documentos if opciones_documentos else ["➕ Agregar nuevo documento"]
    )

    documento_tipo = ""
    documento_numero = ""
    documento_descripcion = ""

    if documento_elegido == "➕ Agregar nuevo documento":
        c1, c2, c3 = st.columns([1, 2, 2])
        with c1:
            documento_tipo = st.selectbox(
                "TIPO DEL NUEVO DOCUMENTO",
                ["RUC", "DNI", "Otro"]
            )
        with c2:
            documento_numero = st.text_input("NÚMERO")
        with c3:
            documento_descripcion = st.text_input(
                "DESCRIPCIÓN",
                placeholder="Ej.: DNI nuevo responsable"
            )
    else:
        indice = opciones_documentos.index(documento_elegido)
        d = documentos[indice]
        documento_tipo = d["tipo"]
        documento_numero = d["numero"]
        documento_descripcion = d["descripcion"]

    st.divider()

    # ========================================================
    # RESULTADO DE VISITA
    # ========================================================

    st.markdown("### 📍 Resultado de la visita")

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

    hubo_evento = "Sí" if resultado in [
        "Con evento",
        "Evento pero no quiso pagar"
    ] else "No"

    if hubo_evento == "Sí":
        quizo_pagar = st.selectbox(
            "¿QUIZO PAGAR?",
            ["Sí", "No", "Pendiente"]
        )
    else:
        quizo_pagar = "No corresponde"

    se_dejo_carta = st.checkbox("📄 ¿SE DEJÓ CARTA / NOTIFICACIÓN?")

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
        codigo_carta = st.text_input("CÓDIGO DE CARTA")

    observacion = st.text_area(
        "OBSERVACIONES DE LA VISITA",
        placeholder="Ej.: Realizó evento sin efectuar pago."
    )

    # ========================================================
    # DATOS DEL EVENTO
    # ========================================================

    if hubo_evento == "Sí":
        st.divider()
        st.markdown("### 🎤 Datos del evento")

        fecha = st.date_input("FECHA DEL EVENTO", value=date.today())

        tipo_evento = st.selectbox(
            "TIPO DE EVENTO",
            [
                "Seleccionar",
                "Evento musical",
                "Concierto",
                "Fiesta",
                "Aniversario",
                "Matrimonio",
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
                "ARTISTA / BANDA / GRUPO QUE SE PRESENTÓ"
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
                "¿LA TARIFA ES CORRECTA?",
                ["Pendiente de revisión", "Sí", "No"]
            )

        c1, c2, c3 = st.columns(3)

        with c1:
            pago = st.selectbox(
                "PAGO",
                ["Pagado", "Pendiente", "Pago parcial"]
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
            operacion = st.text_input("N.º DE OPERACIÓN")

        st.markdown("### 📷 Voucher")
        voucher = st.file_uploader(
            "Adjuntar voucher",
            type=["jpg", "jpeg", "png", "pdf"]
        )

        if voucher:
            st.info(f"📎 Voucher recibido: {voucher.name}")

    else:
        fecha = date.today()
        tipo_evento = ""
        medio = ""
        artista = ""
        monto = 0.0
        tarifa = 0.0
        tarifa_correcta = "Pendiente de revisión"
        pago = "Pendiente"
        banco = "No corresponde"
        operacion = ""
        voucher = None

    st.divider()

    # ========================================================
    # GUARDAR VISITA
    # ========================================================

    if st.button(
        "💾 GUARDAR VISITA",
        use_container_width=True
    ):
        if not documento_numero.strip():
            st.error("Selecciona un documento guardado o agrega uno nuevo.")
        elif hubo_evento == "Sí" and tipo_evento == "Seleccionar":
            st.error("Debes seleccionar el TIPO DE EVENTO.")
        elif hubo_evento == "Sí" and medio == "Seleccionar":
            st.error("Debes seleccionar el MEDIO.")
        elif se_dejo_carta and not codigo_carta.strip():
            st.error("Ingresa el CÓDIGO DE CARTA.")
        else:
            ahora = datetime.now()

            datos_visita = {
                "fecha": str(fecha),
                "hora": ahora.strftime("%H:%M:%S"),
                "codigo_gestor": st.session_state.codigo_gestor,

                "local_id": datos_local["id"],
                "local": datos_local["local"],
                "nombre": datos_local["nombre"],
                "documento_tipo": documento_tipo,
                "documento_numero": documento_numero.strip(),
                "documento_descripcion": documento_descripcion.strip(),
                "direccion": datos_local["direccion"],
                "distrito": datos_local["distrito"],

                "resultado": resultado,
                "hubo_evento": hubo_evento,
                "quizo_pagar": quizo_pagar,
                "se_dejo_carta": "Sí" if se_dejo_carta else "No",
                "tipo_carta": tipo_carta,
                "codigo_carta": codigo_carta.strip(),

                "tipo_evento": tipo_evento,
                "medio": medio,
                "artista": artista,
                "monto": monto,
                "tarifa": tarifa,
                "tarifa_correcta": tarifa_correcta,
                "pago": pago,
                "banco": banco,
                "operacion": operacion.strip(),

                "promotor": datos_local["promotor"],
                "telefono": datos_local["telefono"],
                "observacion": observacion.strip(),

                "voucher_nombre": voucher.name if voucher else ""
            }

            # Guardamos la visita sin modificar visitas anteriores.
            guardar_evento(datos_visita)

            # Si se agregó un documento nuevo, queda guardado
            # para futuras visitas del mismo local.
            if documento_elegido == "➕ Agregar nuevo documento":
                nuevos_documentos = list(documentos)
                nuevos_documentos.append({
                    "tipo": documento_tipo,
                    "numero": documento_numero.strip(),
                    "descripcion": documento_descripcion.strip(),
                    "fecha": str(date.today())
                })

                db.collection("locales").document(
                    datos_local["id"]
                ).set(
                    {"documentos": nuevos_documentos},
                    merge=True
                )

            fila = [
                str(fecha),
                st.session_state.codigo_gestor,
                datos_local["local"],
                datos_local["nombre"],
                f"{documento_tipo} - {documento_numero.strip()}",
                datos_local["direccion"],
                datos_local["distrito"],
                resultado,
                hubo_evento,
                quizo_pagar,
                "Sí" if se_dejo_carta else "No",
                tipo_carta,
                codigo_carta.strip(),
                tipo_evento,
                medio,
                artista,
                monto,
                tarifa,
                tarifa_correcta,
                pago,
                banco,
                operacion.strip(),
                datos_local["promotor"],
                datos_local["telefono"],
                observacion.strip()
            ]

            guardar_csv(fila)

            st.success("✅ VISITA GUARDADA CORRECTAMENTE")
            st.balloons()

            st.write("### Registro guardado")
            st.write(f"**Local:** {datos_local['local']}")
            st.write(f"**Resultado:** {resultado}")
            st.write(f"**Documento:** {documento_tipo} — {documento_numero}")
            st.write(f"**Carta:** {'Sí' if se_dejo_carta else 'No'}")
            st.write(f"**Código gestor:** {st.session_state.codigo_gestor}")
