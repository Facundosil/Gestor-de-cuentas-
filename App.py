import streamlit as st 
import pandas as pd
import os
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import matplotlib.pyplot as plt

# ---------- CONFIGURACIÓN DE PÁGINA ----------
st.set_page_config(page_title="Gestor de Cuentas Personales - Bolso Company", layout="wide")
st_autorefresh(interval=9 * 60 * 1000, key="refresh")  # Refresca cada 9 minutos

# ---------- FUNCIONES AUXILIARES ----------
def cargar_datos_csv(nombre_archivo):
    if os.path.exists(nombre_archivo):
        return pd.read_csv(nombre_archivo)
    return pd.DataFrame(columns=["tipo", "subtipo", "fecha", "monto", "referencia", "cuotas", "dolares"])

def guardar_datos_csv(df, nombre_archivo):
    df.to_csv(nombre_archivo, index=False)

def obtener_cotizacion_dolar():
    try:
        url = "https://api.bluelytics.com.ar/v2/latest"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            dolar_blue = data.get("blue", {}).get("value_sell", None)
            if dolar_blue:
                return dolar_blue * 1.3  # Simulando Dólar Tarjeta
    except Exception as e:
        print(f"Error al obtener cotización: {e}")
    return None

def cargar_credenciales_guardadas():
    archivo = "credenciales_guardadas.csv"
    if os.path.exists(archivo):
        return pd.read_csv(archivo)
    return pd.DataFrame(columns=["usuario", "contraseña"])

def guardar_credenciales_guardadas(usuario, contraseña):
    df = pd.DataFrame({"usuario": [usuario], "contraseña": [contraseña]})
    df.to_csv("credenciales_guardadas.csv", index=False)

# ---------- VARIABLES INICIALES ----------
if not os.path.exists("usuarios.csv"):
    guardar_datos_csv(pd.DataFrame(columns=["usuario", "contraseña"]), "usuarios.csv")

if not os.path.exists("data"):
    os.makedirs("data")

usuarios = cargar_datos_csv("usuarios.csv")
credenciales_guardadas = cargar_credenciales_guardadas()

# ---------- PANTALLA DE INICIO ----------
def login():
    st.image("Logo.png", width=200)
    st.title("Gestor de Cuentas Personales")
    opcion = st.radio("¿Qué querés hacer?", ["Iniciar Sesión", "Registrarte"])

    if opcion == "Registrarte":
        nuevo_usuario = st.text_input("Nuevo nombre de usuario")
        nueva_contraseña = st.text_input("Nueva contraseña", type="password")
        if st.button("Registrarse"):
            if not nuevo_usuario or not nueva_contraseña:
                st.error("Debes completar todos los campos.")
            elif nuevo_usuario in usuarios["usuario"].values:
                st.error("El usuario ya existe.")
            else:
                usuarios.loc[len(usuarios)] = [nuevo_usuario, nueva_contraseña]
                guardar_datos_csv(usuarios, "usuarios.csv")
                st.success("Usuario creado exitosamente. Ahora podés iniciar sesión.")

    if opcion == "Iniciar Sesión":
        usuario_default = credenciales_guardadas["usuario"].iloc[0] if not credenciales_guardadas.empty else ""
        contraseña_default = credenciales_guardadas["contraseña"].iloc[0] if not credenciales_guardadas.empty else ""

        usuario = st.text_input("Usuario", value=usuario_default)
        contraseña = st.text_input("Contraseña", type="password", value=contraseña_default)
        recordar = st.checkbox("Recordarme", value=True)

        if st.button("Iniciar sesión"):
            if ((usuarios["usuario"] == usuario) & (usuarios["contraseña"] == contraseña)).any():
                st.success("Inicio de sesión exitoso.")
                st.session_state["sesion_iniciada"] = True
                st.session_state["usuario_actual"] = usuario

                if recordar:
                    guardar_credenciales_guardadas(usuario, contraseña)

                return True
            else:
                st.error("Usuario o contraseña incorrectos.")
    return False

# ---------- MENÚ PRINCIPAL ----------
def menu():
    usuario = st.session_state["usuario_actual"]
    nombre_archivo_usuario = f"data/{usuario}.csv"
    datos = cargar_datos_csv(nombre_archivo_usuario)

    st.sidebar.image("Logo.png", use_container_width=True)
    st.sidebar.title(f"Hola, {usuario}")

    opciones = st.sidebar.radio("Menú", ["Registrar Ingreso", "Registrar Gasto", "Resumen Mensual", "Resumen Anual", "Editar o Eliminar", "Cerrar Sesión", "Gráficos"])

    if opciones == "Registrar Ingreso":
        st.header("Registrar un ingreso")
        with st.form("form_ingreso"):
            fecha = st.date_input("Fecha", value=datetime.today())
            monto = st.number_input("Monto", min_value=0.0, format="%.2f")
            subtipo = st.selectbox("Tipo de ingreso", ["Fijo", "Variable"])
            referencia = st.text_input("Referencia")
            submit = st.form_submit_button("Guardar Ingreso")
            if submit:
                nuevo = {
                    "tipo": "Ingreso",
                    "subtipo": subtipo,
                    "fecha": fecha,
                    "monto": monto,
                    "referencia": referencia,
                    "cuotas": 1,
                    "dolares": False
                }
                datos = pd.concat([datos, pd.DataFrame([nuevo])], ignore_index=True)
                guardar_datos_csv(datos, nombre_archivo_usuario)
                st.success("Ingreso registrado exitosamente.")

    if opciones == "Registrar Gasto":
        st.header("Registrar un gasto")
        with st.form("form_gasto"):
            fecha = st.date_input("Fecha", value=datetime.today())
            monto = st.number_input("Monto", min_value=0.0, format="%.2f")
            en_dolares = st.checkbox("¿El gasto es en dólares?")
            subtipo = st.selectbox("Tipo de gasto", ["Tarjeta", "Débito Automático", "Gasto Vario"])
            cuotas = st.number_input("¿En cuántas cuotas?", min_value=1, step=1, value=1)
            referencia = st.text_input("Referencia")
            submit = st.form_submit_button("Guardar Gasto")

            if submit:
                if en_dolares:
                    cotizacion = obtener_cotizacion_dolar()
                    if cotizacion:
                        monto *= cotizacion
                    else:
                        st.error("No se pudo obtener la cotización del dólar. Intentá más tarde.")
                        return

                nuevo = {
                    "tipo": "Gasto",
                    "subtipo": subtipo,
                    "fecha": fecha,
                    "monto": monto,
                    "referencia": referencia,
                    "cuotas": cuotas,
                    "dolares": en_dolares
                }
                datos = pd.concat([datos, pd.DataFrame([nuevo])], ignore_index=True)
                guardar_datos_csv(datos, nombre_archivo_usuario)
                st.success("Gasto registrado exitosamente.")

    if opciones == "Resumen Mensual":
        st.header("Resumen Mensual")
        mes = st.selectbox("Mes", list(range(1, 13)), format_func=lambda x: datetime(1900, x, 1).strftime('%B'))
        año = st.number_input("Año", value=datetime.today().year, step=1)

        df_mes = datos.copy()
        df_mes["fecha"] = pd.to_datetime(df_mes["fecha"], errors="coerce")
        df_mes = df_mes.dropna(subset=["fecha"])
        df_mes = df_mes[(df_mes["fecha"].dt.month == mes) & (df_mes["fecha"].dt.year == año)]

        total_ingresos = df_mes[df_mes["tipo"] == "Ingreso"]["monto"].sum()
        total_gastos = df_mes[df_mes["tipo"] == "Gasto"]["monto"].sum()

        st.metric("Total de ingresos", f"${total_ingresos:,.2f}")
        st.metric("Total de gastos", f"${total_gastos:,.2f}")
        st.metric("Balance", f"${(total_ingresos - total_gastos):,.2f}")

        st.subheader("Detalle")
        st.dataframe(df_mes)

    if opciones == "Resumen Anual":
        st.header("Resumen Anual")
        año = st.number_input("Año", value=datetime.today().year, step=1)

        df_anual = datos.copy()
        df_anual["fecha"] = pd.to_datetime(df_anual["fecha"], errors="coerce")
        df_anual = df_anual.dropna(subset=["fecha"])
        df_anual = df_anual[df_anual["fecha"].dt.year == año]

        total_ingresos = df_anual[df_anual["tipo"] == "Ingreso"]["monto"].sum()
        total_gastos = df_anual[df_anual["tipo"] == "Gasto"]["monto"].sum()

        st.metric("Total de ingresos", f"${total_ingresos:,.2f}")
        st.metric("Total de gastos", f"${total_gastos:,.2f}")
        st.metric("Balance", f"${(total_ingresos - total_gastos):,.2f}")

        st.subheader("Detalle")
        st.dataframe(df_anual)

    if opciones == "Editar o Eliminar":
        st.header("Editar o Eliminar Registros")
        if not datos.empty:
            datos_reset = datos.reset_index()
            st.dataframe(datos_reset)
            indice = st.number_input("Índice del registro a modificar o eliminar", min_value=0, max_value=len(datos)-1, step=1)
            accion = st.radio("Acción", ["Editar", "Eliminar"])

            if accion == "Editar":
                registro = datos.iloc[indice]
                tipo = st.selectbox("Tipo", ["Ingreso", "Gasto"], index=["Ingreso", "Gasto"].index(registro["tipo"]))
                subtipo = st.selectbox("Subtipo", ["Fijo", "Variable"] if tipo == "Ingreso" else ["Tarjeta", "Débito Automático", "Gasto Vario"], index=["Fijo", "Variable", "Tarjeta", "Débito Automático", "Gasto Vario"].index(registro["subtipo"]))
                fecha = st.date_input("Fecha", value=registro["fecha"])
                monto = st.number_input("Monto", min_value=0.0, format="%.2f", value=registro["monto"])
                referencia = st.text_input("Referencia", value=registro["referencia"])

                if st.button("Guardar Cambios"):
                    datos.at[indice, "tipo"] = tipo
                    datos.at[indice, "subtipo"] = subtipo
                    datos.at[indice, "fecha"] = fecha
                    datos.at[indice, "monto"] = monto
                    datos.at[indice, "referencia"] = referencia
                    guardar_datos_csv(datos, nombre_archivo_usuario)
                    st.success("Registro actualizado exitosamente.")

            if accion == "Eliminar":
                if st.button("Eliminar Registro"):
                    datos = datos.drop(indice)
                    guardar_datos_csv(datos, nombre_archivo_usuario)
                    st.success("Registro eliminado exitosamente.")

    if opciones == "Gráficos":
        st.header("Gráficos de Finanzas")
        if not datos.empty:
            # Cálculos para gráficos
            resumen = datos.groupby(["tipo"]).sum()["monto"]
            fig, ax = plt.subplots()
            ax.pie(resumen, labels=resumen.index, autopct='%1.1f%%', startangle=90)
            st.pyplot(fig)

    if opciones == "Cerrar Sesión":
        st.session_state["sesion_iniciada"] = False
        st.session_state["usuario_actual"] = None
        st.success("Sesión cerrada con éxito.")

# ---------- PANTALLA DE LOGIN O MENÚ ----------
if "sesion_iniciada" not in st.session_state:
    st.session_state["sesion_iniciada"] = False

if not st.session_state["sesion_iniciada"]:
    if login():
        menu()
else:
    menu()
