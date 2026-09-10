app.py
import streamlit as st
import csv
import os
from datetime import date
import firebase_admin
from firebase_admin import credentials, firestore

# =========================
# FIREBASE
# =========================

cred = credentials.Certificate("firebase_credentials.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# =========================
# CONFIGURACIÓN
# =========================

st.set_page_config(
    page_title="PRUEBA",
    page_icon="🎵",
    layout="centered"
)

ARCHIVO = "eventos.csv"

COLUMNAS = [
    "LOCAL",
    "NOMBRE",
    "RUC/DNI",
    "DIRECCION",
    "DISTRITO",
    "FECHA",
    "MONTO",
    "MEDIO",
    "TIPO EVENTO",
    "ARTISTA/BANDA",
    "TARIFA",
    "TARIFA CORRECTA",
    "PAGO",
    "BANCO",
    "# OPERACION",
    "PROMOTOR",
    "TELEFONO",
    "CODIGO",
    "OBSERVACIONES"
]

# Crear CSV si no existe
if not os.path.exists(ARCHIVO) or os.path.getsize(ARCHIVO) == 0:
    with open(ARCHIVO, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(COLUMNAS)

# =========================
# TÍTULO
# =========================

st.title("🎵 APDAYC - Control de Eventos")
st.caption("Control territorial de eventos, locales y pagos")

# =========================
# MENÚ
# =========================

opcion = st.radio(
    "Selecciona una opción",
    [
        "🏪 Registrar / actualizar local",
        "🎤 Registrar evento"
    ],
    horizontal=True
)

# ============================================================
# PARTE 1: REGISTRAR / ACTUALIZAR LOCAL
# ============================================================

if opcion == "🏪 Registrar / actualizar local":

    st.subheader("🏪 Ficha del local")

    st.info(
        "Registra aquí los datos que normalmente no cambian. "
        "Después podrás seleccionar este local al registrar un evento."
    )

    local = st.text_input("LOCAL")
    nombre = st.text_input("NOMBRE / RAZÓN SOCIAL")
    ruc_dni = st.text_input("RUC / DNI")
    direccion = st.text_input("DIRECCIÓN")
    distrito = st.text_input("DISTRITO")
    promotor = st.text_input("PROMOTOR")
    telefono = st.text_input("TELÉFONO")
    codigo = st.text_input("CÓDIGO")

    st.divider()

    if st.button("💾 GUARDAR LOCAL", use_container_width=True):

        if not local:
            st.error("Debes ingresar el LOCAL.")

        elif not nombre:
            st.error("Debes ingresar el NOMBRE / RAZÓN SOCIAL.")

        elif not distrito:
            st.error("Debes ingresar el DISTRITO.")

        else:

            datos_local = {
                "local": local,
                "nombre": nombre,
                "ruc_dni": ruc_dni,
                "direccion": direccion,
                "distrito": distrito,
                "promotor": promotor,
                "telefono": telefono,
                "codigo": codigo
            }

            # Guardar en Firebase
            db.collection("locales").add(datos_local)

            st.success("✅ LOCAL GUARDADO CORRECTAMENTE")

# ============================================================
# PARTE 2: REGISTRAR EVENTO
# ============================================================

else:

    st.subheader("🎤 Registrar evento")

    # =========================
    # OBTENER LOCALES DE FIREBASE
    # =========================

    locales_docs = db.collection("locales").stream()

    locales = []

    for documento in locales_docs:
        datos = documento.to_dict()

        locales.append({
            "id": documento.id,
            "local": datos.get("local", ""),
            "nombre": datos.get("nombre", ""),
            "ruc_dni": datos.get("ruc_dni", ""),
            "direccion": datos.get("direccion", ""),
            "distrito": datos.get("distrito", ""),
            "promotor": datos.get("promotor", ""),
            "telefono": datos.get("telefono", ""),
            "codigo": datos.get("codigo", "")
        })

    # =========================
    # SELECCIONAR LOCAL
    # =========================

    if not locales:

        st.warning(
            "⚠️ Todavía no tienes locales registrados. "
            "Primero entra a '🏪 Registrar / actualizar local'."
        )

    else:

        nombres_locales = [
            local["local"] for local in locales
        ]

        local_seleccionado = st.selectbox(
            "🏪 SELECCIONA EL LOCAL",
            ["Seleccionar"] + nombres_locales
        )

        datos_local = None

        if local_seleccionado != "Seleccionar":

            for local in locales:
                if local["local"] == local_seleccionado:
                    datos_local = local
                    break

        # =========================
        # MOSTRAR DATOS AUTOMÁTICOS
        # =========================

        if datos_local:

            st.success("✅ Datos del local cargados automáticamente")

            st.write(
                f"**Nombre / Razón Social:** "
                f"{datos_local['nombre']}"
            )

            st.write(
                f"**RUC / DNI:** "
                f"{datos_local['ruc_dni']}"
            )

            st.write(
                f"**Dirección:** "
                f"{datos_local['direccion']}"
            )

            st.write(
                f"**Distrito:** "
                f"{datos_local['distrito']}"
            )

            st.write(
                f"**Promotor:** "
                f"{datos_local['promotor']}"
            )

            st.write(
                f"**Teléfono:** "
                f"{datos_local['telefono']}"
            )

            st.write(
                f"**Código:** "
                f"{datos_local['codigo']}"
            )

            st.divider()

            # =========================
            # DATOS DEL EVENTO
            # =========================

            st.subheader("🎤 Datos del evento")

            fecha = st.date_input(
                "FECHA",
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

            st.subheader("💰 Tarifa y pago")

            monto = st.number_input(
                "MONTO",
                min_value=0.0,
                step=10.0
            )

            tarifa = st.number_input(
                "TARIFA",
                min_value=0.0,
                step=10.0
            )

            tarifa_correcta = st.selectbox(
                "¿LA TARIFA ES CORRECTA?",
                [
                    "Pendiente de revisión",
                    "Sí",
                    "No"
                ]
            )

            pago = st.selectbox(
                "PAGO",
                [
                    "Pagado",
                    "Pendiente",
                    "Pago parcial"
                ]
            )

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

            operacion = st.text_input("N.º DE OPERACIÓN")

            observacion = st.text_area(
                "OBSERVACIONES"
            )

            st.subheader("📷 Voucher")

            voucher = st.file_uploader(
                "Adjuntar voucher",
                type=[
                    "jpg",
                    "jpeg",
                    "png",
                    "pdf"
                ]
            )

            st.divider()

            # =========================
            # GUARDAR EVENTO
            # =========================

            if st.button(
                "💾 GUARDAR EVENTO",
                use_container_width=True
            ):

                if tipo_evento == "Seleccionar":
                    st.error(
                        "Debes seleccionar el TIPO DE EVENTO."
                    )

                elif medio == "Seleccionar":
                    st.error(
                        "Debes seleccionar el MEDIO."
                    )

                else:

                    datos = [
                        datos_local["local"],
                        datos_local["nombre"],
                        datos_local["ruc_dni"],
                        datos_local["direccion"],
                        datos_local["distrito"],
                        str(fecha),
                        monto,
                        medio,
                        tipo_evento,
                        artista,
                        tarifa,
                        tarifa_correcta,
                        pago,
                        banco,
                        operacion,
                        datos_local["promotor"],
                        datos_local["telefono"],
                        datos_local["codigo"],
                        observacion
                    ]

                    # Guardar en CSV
                    with open(
                        ARCHIVO,
                        "a",
                        newline="",
                        encoding="utf-8-sig"
                    ) as archivo:

                        escritor = csv.writer(archivo)
                        escritor.writerow(datos)

                    # Guardar en Firebase
                    datos_firebase = {
                        "local": datos_local["local"],
                        "nombre": datos_local["nombre"],
                        "ruc_dni": datos_local["ruc_dni"],
                        "direccion": datos_local["direccion"],
                        "distrito": datos_local["distrito"],
                        "fecha": str(fecha),
                        "monto": monto,
                        "medio": medio,
                        "tipo_evento": tipo_evento,
                        "artista": artista,
                        "tarifa": tarifa,
                        "tarifa_correcta": tarifa_correcta,
                        "pago": pago,
                        "banco": banco,
                        "operacion": operacion,
                        "promotor": datos_local["promotor"],
                        "telefono": datos_local["telefono"],
                        "codigo": datos_local["codigo"],
                        "observacion": observacion
                    }

                    db.collection("eventos").add(
                        datos_firebase
                    )

                    st.success(
                        "✅ EVENTO GUARDADO CORRECTAMENTE"
                    )

                    st.write("### Registro guardado")

                    st.write(
                        f"**Local:** "
                        f"{datos_local['local']}"
                    )

                    st.write(
                        f"**Fecha:** {fecha}"
                    )

                    st.write(
                        f"**Monto:** S/ {monto:,.2f}"
                    )

                    st.write(
                        f"**Medio:** {medio}"
                    )

                    st.write(
                        f"**Pago:** {pago}"
                    )

                    if voucher:
                        st.info(
                            f"📎 Voucher recibido: "
                            f"{voucher.name}"
                        )

