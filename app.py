import streamlit as st
import csv
import os
import pandas as pd
from datetime import date
from io import BytesIO

# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="APDAYC - Eventos",
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
    "OBSERVACIONES",
    "VOUCHER"
]

# ============================================================
# FUNCIONES
# ============================================================

def asegurar_csv():
    if not os.path.exists(ARCHIVO) or os.path.getsize(ARCHIVO) == 0:
        with open(ARCHIVO, "w", newline="", encoding="utf-8-sig") as archivo:
            csv.writer(archivo).writerow(COLUMNAS)

def leer_registros():
    asegurar_csv()
    try:
        return pd.read_csv(ARCHIVO, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame(columns=COLUMNAS)

def guardar_fila(datos):
    asegurar_csv()
    with open(ARCHIVO, "a", newline="", encoding="utf-8-sig") as archivo:
        csv.writer(archivo).writerow(datos)

def crear_excel(df):
    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Eventos")
        hoja = writer.book["Eventos"]
        for columna in hoja.columns:
            max_len = 0
            letra = columna[0].column_letter
            for celda in columna:
                valor = "" if celda.value is None else str(celda.value)
                max_len = max(max_len, len(valor))
            hoja.column_dimensions[letra].width = min(max(max_len + 2, 10), 35)
        hoja.freeze_panes = "A2"
        hoja.auto_filter.ref = hoja.dimensions
    salida.seek(0)
    return salida

asegurar_csv()

# ============================================================
# TÍTULO
# ============================================================

st.title("🎵 APDAYC - Control de Eventos")
st.caption("Piloto móvil para control territorial de eventos, locales y pagos")

# ============================================================
# MENÚ
# ============================================================

opcion = st.radio(
    "Selecciona una opción",
    [
        "🏪 Registrar / actualizar local",
        "🎤 Registrar evento",
        "📊 Ver registros / Exportar Excel"
    ],
    horizontal=True
)

# ============================================================
# PARTE 1: LOCAL
# ============================================================

if opcion == "🏪 Registrar / actualizar local":

    st.subheader("🏪 Ficha del local")
    st.info(
        "Registra aquí los datos que normalmente no cambian. "
        "Luego podrás seleccionar este local al registrar un evento."
    )

    local = st.text_input("LOCAL")
    nombre = st.text_input("NOMBRE / RAZÓN SOCIAL")
    ruc_dni = st.text_input("RUC / DNI")
    direccion = st.text_input("DIRECCIÓN")
    distrito = st.text_input("DISTRITO")
    promotor = st.text_input("PROMOTOR")
    telefono = st.text_input("TELÉFONO")
    codigo = st.text_input("CÓDIGO")

    if st.button("💾 GUARDAR LOCAL", use_container_width=True):
        if not local:
            st.error("Debes ingresar el LOCAL.")
        elif not nombre:
            st.error("Debes ingresar el NOMBRE / RAZÓN SOCIAL.")
        elif not distrito:
            st.error("Debes ingresar el DISTRITO.")
        else:
            st.success(
                "✅ Local registrado para el piloto. "
                "Para esta versión, vuelve a ingresar los locales si reinicias la aplicación."
            )

            # Guardamos locales en un archivo independiente.
            locales = []
            if os.path.exists("locales.csv"):
                try:
                    locales = pd.read_csv("locales.csv", encoding="utf-8-sig").to_dict("records")
                except Exception:
                    locales = []

            nuevo = {
                "LOCAL": local,
                "NOMBRE": nombre,
                "RUC/DNI": ruc_dni,
                "DIRECCION": direccion,
                "DISTRITO": distrito,
                "PROMOTOR": promotor,
                "TELEFONO": telefono,
                "CODIGO": codigo
            }

            # Evitar duplicado exacto por LOCAL.
            locales = [x for x in locales if str(x.get("LOCAL", "")).strip().lower() != local.strip().lower()]
            locales.append(nuevo)

            pd.DataFrame(locales).to_csv(
                "locales.csv", index=False, encoding="utf-8-sig"
            )

# ============================================================
# PARTE 2: EVENTO
# ============================================================

elif opcion == "🎤 Registrar evento":

    st.subheader("🎤 Registrar evento")

    locales = []
    if os.path.exists("locales.csv"):
        try:
            locales = pd.read_csv("locales.csv", encoding="utf-8-sig").fillna("").to_dict("records")
        except Exception:
            locales = []

    if not locales:
        st.warning(
            "⚠️ Todavía no tienes locales registrados. "
            "Primero entra a '🏪 Registrar / actualizar local'."
        )
    else:
        nombres_locales = [str(local["LOCAL"]) for local in locales]

        local_seleccionado = st.selectbox(
            "🏪 SELECCIONA EL LOCAL",
            ["Seleccionar"] + nombres_locales
        )

        datos_local = None
        if local_seleccionado != "Seleccionar":
            for local in locales:
                if str(local["LOCAL"]) == local_seleccionado:
                    datos_local = local
                    break

        if datos_local:
            st.success("✅ Datos del local cargados automáticamente")

            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Razón social:** {datos_local['NOMBRE']}")
                st.write(f"**RUC/DNI:** {datos_local['RUC/DNI']}")
                st.write(f"**Distrito:** {datos_local['DISTRITO']}")
                st.write(f"**Promotor:** {datos_local['PROMOTOR']}")
            with col2:
                st.write(f"**Dirección:** {datos_local['DIRECCION']}")
                st.write(f"**Teléfono:** {datos_local['TELEFONO']}")
                st.write(f"**Código:** {datos_local['CODIGO']}")

            st.divider()
            st.subheader("🎤 Datos del evento")

            fecha = st.date_input("FECHA", value=date.today())

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
                artista = st.text_input("ARTISTA / BANDA / GRUPO QUE SE PRESENTÓ")

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

            observacion = st.text_area("OBSERVACIONES")

            st.subheader("📷 Voucher")

            voucher = st.file_uploader(
                "Adjuntar voucher",
                type=["jpg", "jpeg", "png", "pdf"]
            )

            if st.button("💾 GUARDAR EVENTO", use_container_width=True):

                if tipo_evento == "Seleccionar":
                    st.error("Debes seleccionar el TIPO DE EVENTO.")
                elif medio == "Seleccionar":
                    st.error("Debes seleccionar el MEDIO.")
                else:
                    voucher_nombre = voucher.name if voucher else ""

                    datos = [
                        datos_local["LOCAL"],
                        datos_local["NOMBRE"],
                        datos_local["RUC/DNI"],
                        datos_local["DIRECCION"],
                        datos_local["DISTRITO"],
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
                        datos_local["PROMOTOR"],
                        datos_local["TELEFONO"],
                        datos_local["CODIGO"],
                        observacion,
                        voucher_nombre
                    ]

                    guardar_fila(datos)

                    st.success("✅ EVENTO GUARDADO CORRECTAMENTE")
                    st.write("### Registro guardado")
                    st.write(f"**Local:** {datos_local['LOCAL']}")
                    st.write(f"**Fecha:** {fecha}")
                    st.write(f"**Monto:** S/ {monto:,.2f}")
                    st.write(f"**Medio:** {medio}")
                    st.write(f"**Pago:** {pago}")

                    if voucher:
                        st.info(f"📎 Voucher registrado: {voucher.name}")

# ============================================================
# PARTE 3: CONSULTA Y EXPORTACIÓN
# ============================================================

else:

    st.subheader("📊 Registros y exportación")

    df = leer_registros()

    if df.empty:
        st.info("Todavía no hay eventos registrados.")
    else:
        st.metric("Total de eventos", len(df))
        st.dataframe(df, use_container_width=True, hide_index=True)

        excel = crear_excel(df)

        st.download_button(
            label="📥 DESCARGAR EXCEL",
            data=excel,
            file_name=f"APDAYC_eventos_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        st.caption(
            "El Excel contiene todos los registros guardados en esta versión del piloto."
        )

# ============================================================
# NOTA DEL PILOTO
# ============================================================

st.divider()
st.caption(
    "Versión piloto: almacenamiento local temporal. "
    "La conexión en línea con Firebase/Firestore puede incorporarse en la siguiente etapa."
)
