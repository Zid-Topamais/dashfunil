import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go

# 1. Configuração da página (Deve ser um dos primeiros comandos)
st.set_page_config(page_title="Dashboard Topa+ Realtime", layout="wide")

# 2. Conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600) # Atualiza os dados a cada 10 minutos
def load_data():
    # ID da planilha extraído da sua URL
    sheet_id = "1-ttYZTqw_8JhU3zA1JAKYaece_iJ-CBrdeoTzNKMZ3I"
    
    # URL de exportação direta (mais estável para evitar erros de caracteres especiais e Erro 400)
    url_dez = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Dez"
    url_jan = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Jan"
    
    # Lendo os dados usando pandas diretamente pela URL de exportação
    df_dez = pd.read_csv(url_dez)
    df_jan = pd.read_csv(url_jan)
    
    # Concatenando as duas abas
    df_full = pd.concat([df_dez, df_jan], ignore_index=True)
    
    # Limpeza básica: remove linhas totalmente vazias
    df_full = df_full.dropna(how='all')
    
    return df_full

# 3. Execução da carga de dados com tratamento de erro
try:
    df = load_data()
except Exception as e:
    st.error(f"⚠️ Erro ao carregar dados: {e}")
    st.info("Verifique se as abas na planilha se chamam 'Dados_Dez' e 'Dados_Jan' e se o compartilhamento está como 'Qualquer pessoa com o link'.")
    st.stop()

# --- SIDEBAR (Filtros) ---
st.sidebar.header("Filtros")

# Verificação de segurança para a coluna 'Digitado por'
if 'Digitado por' in df.columns:
    digitadores = sorted(df['Digitado por'].dropna().unique().tolist())
    digitador_selecionado = st.sidebar.selectbox("Selecione o Digitador", ["Todos"] + digitadores)
    
    # Aplicando o filtro
    df_filtered = df if digitador_selecionado == "Todos" else df[df['Digitado por'] == digitador_selecionado]
else:
    st.warning("Coluna 'Digitado por' não encontrada. Exibindo dados gerais.")
    df_filtered = df
    digitador_selecionado = "Geral"

# --- TÍTULO ---
st.title(f"📊 Funil de Recusas - {digitador_selecionado}")

# --- MÉTRICAS DO FUNIL ---
# Mapeamento dinâmico conforme as colunas da sua planilha
leads = len(df_filtered)
token_ok = len(df_filtered[df_filtered['status_da_proposta'].notna()]) if 'status_da_proposta' in df_filtered.columns else 0
no_motor = len(df_filtered[df_filtered['status_da_analise'] == 'REJECTED']) if 'status_da_analise' in df_filtered.columns else 0
pagos = len(df_filtered[df_filtered['status_da_proposta'] == 'DISBURSED']) if 'status_da_proposta' in df_filtered.columns else 0

# Gráfico de Funil
fig = go.Figure(go.Funnel(
    y = ["Novos Leads", "Token Enviado/Aprovado", "Chegou no Motor", "Contratos Pagos"],
    x = [leads, token_ok, no_motor, pagos],
    textinfo = "value+percent initial",
    marker = {"color": ["#636EFA", "#EF553B", "#00CC96", "#AB63FA"]}
))

st.plotly_chart(fig, use_container_width=True)

# --- ANÁLISE DE RECUSAS (DRILL DOWN) ---
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("⚠️ Motivos Pré-Motor")
    if 'status_da_analise' in df_filtered.columns:
        # Filtra apenas o que não é sucesso nem erro final do motor
        motivos_pre = df_filtered[~df_filtered['status_da_analise'].isin(['REJECTED', 'APPROVED', 'DISBURSED'])]['status_da_analise'].value_counts()
        if not motivos_pre.empty:
            st.bar_chart(motivos_pre)
        else:
            st.write("Nenhum motivo específico encontrado nesta categoria.")
    else:
        st.info("Coluna 'status_da_analise' não disponível.")

with col2:
    st.subheader("🚫 Detalhes de Decisão (Motor)")
    if 'motivo_da_decisao' in df_filtered.columns:
        motivos_motor = df_filtered['motivo_da_decisao'].value_counts()
        st.dataframe(motivos_motor, use_container_width=True)
    else:
        st.info("Coluna 'motivo_da_decisao' não disponível.")

# --- DADOS BRUTOS ---
with st.expander("📂 Visualizar Dados Detalhados"):
    st.dataframe(df_filtered, use_container_width=True)
