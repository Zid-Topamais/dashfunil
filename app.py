import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Dashboard Funil de Recusas", layout="wide")

@st.cache_data
def load_data():
    # Substitua pelos caminhos dos seus arquivos ou leitura direta do Sheets
    # df_dez = pd.read_excel("sua_base.xlsx", sheet_name="Dados brutos - Dez")
    # df_jan = pd.read_excel("sua_base.xlsx", sheet_name="Dados brutos - Jan")
    
    # Exemplo de carregamento manual para teste (ajuste para o seu arquivo)
    df = pd.concat([df_dez, df_jan], ignore_index=True)
    return df

# --- SIMULAÇÃO DE ESTRUTURA (Para o código rodar, certifique-se que os nomes batam) ---
# df = load_data()

st.title("📊 Análise de Funil e Recusas")

# --- SIDEBAR: FILTROS ---
st.sidebar.header("Filtros")
digitadores = df['Digitado por'].unique().tolist()
digitador_selecionado = st.sidebar.selectbox("Selecione o Digitador", ["Todos"] + digitadores)

# Filtragem de dados
if digitador_selecionado != "Todos":
    df_filtered = df[df['Digitado por'] == digitador_selecionado]
else:
    df_filtered = df

# --- CÁLCULO DAS ETAPAS DO FUNIL ---
# Baseado na lógica das suas imagens:
total_leads = len(df_filtered)
token_aprovado = len(df_filtered[df_filtered['status_da_proposta'].notnull()]) # Ajustar critério se necessário
sujeito_motor = len(df_filtered[~df_filtered['status_da_analise'].isin(['NO_AVAILABLE_MARGIN', 'CPF_EMPLOYER', 'FAILED_DATAPREV'])])
contratos_pagos = len(df_filtered[df_filtered['status_da_proposta'] == 'DISBURSED'])

# --- VISUALIZAÇÃO DO FUNIL ---
fig = go.Figure(go.Funnel(
    y = ["Novos Leads", "Token Aprovado", "Sujeito ao Motor", "Contratos Pagos"],
    x = [total_leads, token_aprovado, sujeito_motor, contratos_pagos],
    textinfo = "value+percent initial"
))

st.plotly_chart(fig, use_container_width=True)

# --- DRILL DOWN: MOTIVOS DE RECUSA ---
st.subheader(f"Detalhamento de Recusas - {digitador_selecionado}")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Recusas Pré-Motor (Dataprev/Margem)**")
    recusas_pre = df_filtered['status_da_analise'].value_counts()
    st.dataframe(recusas_pre)

with col2:
    st.markdown("**Recusas no Motor (Políticas)**")
    # Filtra apenas quem chegou no motor mas foi rejeitado
    recusas_motor = df_filtered['motivo_da_decisao'].value_counts()
    st.write(recusas_motor)

# --- TABELA DE DADOS BRUTOS ---
if st.checkbox("Mostrar Dados Brutos Filtrados"):
    st.write(df_filtered)
