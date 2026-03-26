import streamlit as st
import pandas as pd
from datetime import datetime

# =========================================================
# CONFIGURACIÓN
# =========================================================
EXCEL_PATH = "portfolio.xlsx"

st.set_page_config(page_title="AI PMO Assistant", layout="wide")

# =========================================================
# FUNCIONES
# =========================================================
def cargar_datos(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)

    # Normalizar columnas esperadas
    columnas_esperadas = [
        "ID_Proyecto", "Proyecto", "Tipo_Proyecto", "Cliente", "Area",
        "ID_Tarea", "Tarea", "Responsable",
        "Fecha_Inicio", "Fecha_Fin_Planeada", "Fecha_Fin_Real",
        "Avance_Porcentaje", "Presupuesto_Plan", "Presupuesto_Real",
        "Horas_Plan", "Horas_Reales",
        "Estado", "Prioridad", "Cambio_Solicitado", "Impacto_Cambio",
        "Aprobacion_Cambio", "Riesgo", "Dependencias",
        "Fecha_Actualizacion", "Comentarios"
    ]

    for col in columnas_esperadas:
        if col not in df.columns:
            df[col] = None

    # Convertir fechas
    for col in ["Fecha_Inicio", "Fecha_Fin_Planeada", "Fecha_Fin_Real", "Fecha_Actualizacion"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Convertir numéricos
    for col in ["Avance_Porcentaje", "Presupuesto_Plan", "Presupuesto_Real", "Horas_Plan", "Horas_Reales"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Limpiar textos
    for col in ["Proyecto", "Tarea", "Responsable", "Estado", "Prioridad", "Cambio_Solicitado",
                "Impacto_Cambio", "Aprobacion_Cambio", "Riesgo", "Comentarios"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df


def calcular_estado_presupuesto(row):
    plan = row["Presupuesto_Plan"]
    real = row["Presupuesto_Real"]

    if pd.isna(plan) or pd.isna(real):
        return "SIN DATO"
    if real > plan:
        return "OVERBUDGET"
    if real < plan:
        return "UNDERBUDGET"
    return "CONTROLADO"


def calcular_desviacion_presupuesto(row):
    plan = row["Presupuesto_Plan"]
    real = row["Presupuesto_Real"]

    if pd.isna(plan) or pd.isna(real):
        return None
    return real - plan


def calcular_desviacion_presupuesto_pct(row):
    plan = row["Presupuesto_Plan"]
    real = row["Presupuesto_Real"]

    if pd.isna(plan) or pd.isna(real) or plan == 0:
        return None
    return round(((real - plan) / plan) * 100, 2)


def calcular_estado_cronograma(row):
    hoy = pd.Timestamp(datetime.now().date())
    fin_plan = row["Fecha_Fin_Planeada"]
    fin_real = row["Fecha_Fin_Real"]
    avance = row["Avance_Porcentaje"]

    if pd.isna(avance):
        return "SIN DATO"

    if avance == 100:
        if pd.notna(fin_real) and pd.notna(fin_plan):
            if fin_real <= fin_plan:
                return "FINALIZADA EN TIEMPO"
            return "FINALIZADA FUERA DE PLAZO"
        return "FINALIZADA"

    if pd.notna(fin_plan) and hoy > fin_plan and avance < 100:
        return "ATRASADA"

    return "EN CURSO"


def calcular_avance_esperado(row):
    hoy = pd.Timestamp(datetime.now().date())
    inicio = row["Fecha_Inicio"]
    fin_plan = row["Fecha_Fin_Planeada"]

    if pd.isna(inicio) or pd.isna(fin_plan):
        return None

    duracion_total = (fin_plan - inicio).days
    duracion_transcurrida = (hoy - inicio).days

    if duracion_total <= 0:
        return 100.0 if hoy >= fin_plan else 0.0

    if hoy <= inicio:
        return 0.0
    if hoy >= fin_plan:
        return 100.0

    return round((duracion_transcurrida / duracion_total) * 100, 2)


def calcular_senal_ejecucion(row):
    esperado = row["Avance_Esperado"]
    real = row["Avance_Porcentaje"]

    if esperado is None or pd.isna(esperado) or pd.isna(real):
        return "SIN DATO"

    if real >= 100:
        return "COMPLETADA"
    if real >= esperado + 15:
        return "ADELANTADA"
    if real < esperado - 15:
        return "REZAGADA"
    return "EN LÍNEA"


def calcular_estado_cambio(row):
    cambio = str(row["Cambio_Solicitado"]).strip()
    aprobacion = str(row["Aprobacion_Cambio"]).strip().lower()

    if not cambio:
        return "SIN CAMBIO"
    if aprobacion == "aprobado":
        return "CAMBIO APROBADO"
    if aprobacion == "pendiente":
        return "CAMBIO PENDIENTE"
    return "CAMBIO SIN DEFINIR"


def calcular_criticidad(row):
    prioridad_alta = str(row["Prioridad"]).lower() == "alta"
    atraso = row["Estado_Cronograma"] == "ATRASADA"
    riesgo_alto = str(row["Riesgo"]).lower() == "alto"
    return prioridad_alta and (atraso or riesgo_alto)


def calcular_risk_score(row):
    score = 0

    if row["Es_Critica"]:
        score += 2
    if row["Estado_Cronograma"] == "ATRASADA":
        score += 2
    if row["Estado_Presupuesto"] == "OVERBUDGET":
        score += 2
    if row["Estado_Cambio"] in ["CAMBIO PENDIENTE", "CAMBIO SIN DEFINIR"]:
        score += 1
    if str(row["Riesgo"]).lower() == "alto":
        score += 2
    if row["Senal_Ejecucion"] == "REZAGADA":
        score += 1

    return score


def aplicar_reglas_pmo(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["Estado_Presupuesto"] = df.apply(calcular_estado_presupuesto, axis=1)
    df["Desviacion_Presupuesto"] = df.apply(calcular_desviacion_presupuesto, axis=1)
    df["Desviacion_Presupuesto_Pct"] = df.apply(calcular_desviacion_presupuesto_pct, axis=1)

    df["Estado_Cronograma"] = df.apply(calcular_estado_cronograma, axis=1)
    df["Avance_Esperado"] = df.apply(calcular_avance_esperado, axis=1)
    df["Senal_Ejecucion"] = df.apply(calcular_senal_ejecucion, axis=1)

    df["Estado_Cambio"] = df.apply(calcular_estado_cambio, axis=1)
    df["Es_Critica"] = df.apply(calcular_criticidad, axis=1)
    df["Risk_Score"] = df.apply(calcular_risk_score, axis=1)

    return df


def semaforo_proyecto(grupo: pd.DataFrame) -> str:
    tareas_criticas = int(grupo["Es_Critica"].sum())
    overbudget = int((grupo["Estado_Presupuesto"] == "OVERBUDGET").sum())
    cambios_pendientes = int(grupo["Estado_Cambio"].isin(["CAMBIO PENDIENTE", "CAMBIO SIN DEFINIR"]).sum())

    if tareas_criticas >= 2 or overbudget >= 2:
        return "ROJO"
    if tareas_criticas >= 1 or overbudget >= 1 or cambios_pendientes >= 2:
        return "AMARILLO"
    return "VERDE"


def resumen_portafolio(df: pd.DataFrame):
    resumen = []

    for proyecto, grupo in df.groupby("Proyecto"):
        resumen.append({
            "Proyecto": proyecto,
            "Total_Tareas": len(grupo),
            "Tareas_Atrasadas": int((grupo["Estado_Cronograma"] == "ATRASADA").sum()),
            "Tareas_Criticas": int(grupo["Es_Critica"].sum()),
            "Overbudget": int((grupo["Estado_Presupuesto"] == "OVERBUDGET").sum()),
            "Cambios_Pendientes": int(grupo["Estado_Cambio"].isin(["CAMBIO PENDIENTE", "CAMBIO SIN DEFINIR"]).sum()),
            "Semaforo": semaforo_proyecto(grupo)
        })

    return pd.DataFrame(resumen)


def responder_pregunta(df: pd.DataFrame, pregunta: str):
    q = pregunta.lower()

    if "atrasad" in q:
        return df[df["Estado_Cronograma"] == "ATRASADA"][
            ["Proyecto", "Tarea", "Responsable", "Fecha_Fin_Planeada", "Avance_Porcentaje", "Prioridad", "Es_Critica"]
        ]

    if "adelantad" in q:
        return df[df["Senal_Ejecucion"] == "ADELANTADA"][
            ["Proyecto", "Tarea", "Responsable", "Avance_Porcentaje", "Avance_Esperado", "Prioridad"]
        ]

    if "overbudget" in q or "sobrecosto" in q or "presupuesto" in q:
        return df[df["Estado_Presupuesto"] == "OVERBUDGET"][
            ["Proyecto", "Tarea", "Responsable", "Presupuesto_Plan", "Presupuesto_Real",
             "Desviacion_Presupuesto", "Desviacion_Presupuesto_Pct"]
        ]

    if "riesgo" in q or "rojo" in q:
        return df[df["Risk_Score"] >= 4][
            ["Proyecto", "Tarea", "Responsable", "Risk_Score", "Riesgo", "Estado_Cronograma", "Estado_Presupuesto", "Es_Critica"]
        ]

    if "cambio" in q or "alcance" in q:
        return df[df["Estado_Cambio"] != "SIN CAMBIO"][
            ["Proyecto", "Tarea", "Cambio_Solicitado", "Impacto_Cambio", "Aprobacion_Cambio", "Estado_Cambio"]
        ]

    if "responsable" in q:
        temp = df.copy()
        temp["Tareas_Criticas"] = temp["Es_Critica"].astype(int)
        temp["Tareas_Atrasadas"] = (temp["Estado_Cronograma"] == "ATRASADA").astype(int)

        return (
            temp.groupby("Responsable")[["Tareas_Criticas", "Tareas_Atrasadas"]]
            .sum()
            .reset_index()
            .sort_values(["Tareas_Criticas", "Tareas_Atrasadas"], ascending=False)
        )

    return None


# =========================================================
# APP
# =========================================================
st.title("AI PMO Assistant")
st.caption("Chatbot para monitoreo de proyectos, riesgos, presupuesto y cronograma")

try:
    df_raw = cargar_datos(EXCEL_PATH)
    df = aplicar_reglas_pmo(df_raw)
except Exception as e:
    st.error(f"No se pudo cargar el archivo Excel: {e}")
    st.stop()

# KPIs
st.subheader("Resumen del Portafolio")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Proyectos", df["Proyecto"].nunique())
col2.metric("Tareas", len(df))
col3.metric("Tareas Atrasadas", int((df["Estado_Cronograma"] == "ATRASADA").sum()))
col4.metric("Tareas Críticas", int(df["Es_Critica"].sum()))

# Semáforo
st.subheader("Semáforo de Proyectos")
df_resumen = resumen_portafolio(df)
st.dataframe(df_resumen, use_container_width=True)

# Preguntas sugeridas
st.subheader("Consulta al AI PMO Assistant")
preguntas_sugeridas = [
    "¿Qué tareas están atrasadas?",
    "¿Qué tareas están adelantadas?",
    "¿Qué proyectos están en overbudget?",
    "¿Qué proyectos están en riesgo?",
    "¿Qué cambios solicitados afectan el alcance?",
    "¿Qué responsables tienen más tareas críticas?"
]

pregunta = st.selectbox("Preguntas sugeridas", [""] + preguntas_sugeridas)
pregunta_manual = st.text_input("O escribe tu pregunta")

consulta_final = pregunta_manual if pregunta_manual else pregunta

if st.button("Analizar"):
    if not consulta_final:
        st.warning("Escribe o selecciona una pregunta.")
    else:
        resultado = responder_pregunta(df, consulta_final)

        st.markdown("## Resumen Ejecutivo")
        st.write(f"Consulta realizada: **{consulta_final}**")

        if resultado is not None and not resultado.empty:
            st.markdown("## Tabla de Resultados")
            st.dataframe(resultado, use_container_width=True)

            st.markdown("## Recomendación del Project Manager")
            st.write(
                "Se recomienda revisar los elementos identificados, validar impacto en tiempo, costo y alcance, "
                "y escalar de inmediato las tareas críticas o proyectos con desviaciones relevantes."
            )
        elif resultado is not None and resultado.empty:
            st.info("No se encontraron registros que cumplan con esa condición.")
        else:
            st.info("La pregunta fue recibida, pero aún no tiene una lógica específica programada.")

# Datos detallados
st.subheader("Detalle de Datos Analizados")
st.dataframe(df, use_container_width=True)
