import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Topa+ Realtime", layout="wide")

# Conectando ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600) # Atualiza os dados a cada 10 minutos
def load_data():
    # Lendo as abas específicas via nome
    df_dez = conn.read(worksheet="Dados brutos - Dez")
    df_jan = conn.read(worksheet="Dados brutos - Jan")
    
    # Concatenando
    df = pd.concat([df_dez, df_jan], ignore_index=True)
    return df

df = load_data()

# --- SIDEBAR ---
st.sidebar.header("Filtros")
# Coluna Q é "Digitado por"
digitadores = sorted(df['Digitado por'].dropna().unique().tolist())
digitador_selecionado = st.sidebar.selectbox("Selecione o Digitador", ["Todos"] + digitadores)

# Filtragem
df_filtered = df if digitador_selecionado == "Todos" else df[df['Digitado por'] == digitador_selecionado]

# --- FUNIL DE VENDAS ---
st.title(f"📊 Funil de Recusas - {digitador_selecionado}")

# Mapeamento conforme colunas da sua planilha
leads = len(df_filtered)
token_ok = len(df_filtered[df_filtered['status_da_proposta'].notna()])
no_motor = len(df_filtered[df_filtered['status_da_analise'] == 'REJECTED'])
pagos = len(df_filtered[df_filtered['status_da_proposta'] == 'DISBURSED'])

fig = go.Figure(go.Funnel(
    y = ["Novos Leads", "Token Enviado/Aprovado", "Chegou no Motor", "Contratos Pagos"],
    x = [leads, token_ok, no_motor, pagos],
    textinfo = "value+percent initial"
))

st.plotly_chart(fig, use_container_width=True)

# --- DRILL DOWN DE RECUSAS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("⚠️ Motivos Pré-Motor (Analítico)")
    # Analisando motivos de 'status_da_analise' que não são REJECTED/APPROVED
    motivos_pre = df_filtered[~df_filtered['status_da_analise'].isin(['REJECTED', 'APPROVED'])]['status_da_analise'].value_counts()
    st.bar_chart(motivos_pre)

with col2:
    st.subheader("🚫 Motivos de Decisão (Motor)")
    # Analisando a coluna 'motivo_da_decisao'
    motivos_motor = df_filtered['motivo_da_decisao'].value_counts()
    st.dataframe(motivos_motor)

# Dados detalhados
with st.expander("Visualizar Dados Brutos"):
    st.write(df_filtered)
