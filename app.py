import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. Configuração da página
st.set_page_config(page_title="Dashboard Topa+ Realtime", layout="wide")

# 2. Função de Carga e Tratamento de Dados
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1-ttYZTqw_8JhU3zA1JAKYaece_iJ-CBrdeoTzNKMZ3I"
    url_dez = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Dez"
    url_jan = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Jan"
    
    try:
        # Carregando as abas
        df_dez = pd.read_csv(url_dez)
        df_jan = pd.read_csv(url_jan)
        df = pd.concat([df_dez, df_jan], ignore_index=True)
        
        # Limpeza: remove linhas totalmente vazias
        df = df.dropna(how='all')

        # --- TRATAMENTO DE DATA (COLUNA D - Data de Criação) ---
        # Convertendo a coluna para data (Pandas tenta identificar o formato automaticamente)
        df['Data de Criação'] = pd.to_datetime(df['Data de Criação'], errors='coerce', dayfirst=True)
        
        # Criando coluna de Mês/Ano para o filtro
        # Criamos um nome amigável: "Dezembro/2025"
        meses_pt = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }
        
        df['Mes_Nome'] = df['Data de Criação'].dt.month.map(meses_pt)
        df['Ano'] = df['Data de Criação'].dt.year
        df['Filtro_Mes'] = df['Mes_Nome'] # Usado no selectbox

    except Exception as e:
        st.error(f"Erro no processamento dos dados: {e}")
        return pd.DataFrame()

    # --- MAPEAMENTO DE CATEGORIAS (CONFORME SUA IMAGEM DO EXCEL) ---
    def mapear_categoria(row):
        status_analise = str(row.get('status_da_analise', '')).strip().upper()
        status_proposta = str(row.get('status_da_proposta', '')).strip().upper()
        
        # Categoria 1: Pré-Motor
        pre_motor = ['NO_AVAILABLE_MARGIN', 'CPF_EMPLOYER_SEM_DADOS_DATAPREV', 
                     'NOT_AUTHORIZED_DATAPREV', 'FAILED_DATAPREV', 'CREDIT_ENGINE_ERROR']
        
        if status_analise in pre_motor:
            return "1. Propostas Rejeitadas Pré-Motor"
        elif status_analise == 'REJECTED':
            return "2. Propostas Rejeitadas No Motor"
        elif status_proposta == 'DISBURSED':
            return "3. Contratos Pagos"
        
        # Categoria 4: Disponíveis/Em andamento (Geralmente CREDIT_CHECK_COMPLETED, etc)
        disponiveis = ['CREDIT_CHECK_COMPLETED', 'PRE_ACCEPTED', 'CONTRACT_GENERATION_FAILED']
        if status_analise in disponiveis:
            return "4. Propostas Disponíveis"
            
        return "5. Outros / Processamento"

    df['Categoria_Excel'] = df.apply(mapear_categoria, axis=1)
    return df

# Execução da carga
df = load_data()

if df.empty:
    st.warning("Aguardando dados ou erro na conexão com a planilha.")
    st.stop()

# --- SIDEBAR (FILTROS) ---
st.sidebar.header("Filtros de Visão")

# Filtro de Mês dinâmico baseado na 'Data de Criação'
lista_meses = ["Todos"] + sorted(df['Filtro_Mes'].dropna().unique().tolist())
mes_selecionado = st.sidebar.selectbox("Selecione o Mês", lista_meses)

# Filtro de Digitador (Coluna Q)
digitador_col = 'Digitado por'
opcoes_digitador = ["Todos"] + sorted(df[digitador_col].dropna().unique().tolist())
digitador_selecionado = st.sidebar.selectbox("Selecione o Digitador", opcoes_digitador)

# --- APLICAÇÃO DOS FILTROS ---
df_filtered = df.copy()

if mes_selecionado != "Todos":
    df_filtered = df_filtered[df_filtered['Filtro_Mes'] == mes_selecionado]

if digitador_selecionado != "Todos":
    df_filtered = df_filtered[df_filtered[digitador_col] == digitador_selecionado]

# --- DASHBOARD ---
st.title(f"📊 Dashboard Analítico")
st.caption(f"Baseado na Data de Criação | Visão: {mes_selecionado}")

# Métricas Principais
total = len(df_filtered)
pagos = len(df_filtered[df_filtered['status_da_proposta'].str.strip().str.upper() == 'DISBURSED'])
conv = (pagos / total * 100) if total > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("Total Leads", total)
c2.metric("Pagos", pagos)
c3.metric("% Conversão", f"{conv:.1f}%")

st.divider()

# --- ESTRUTURA REPLICADA DO EXCEL ---
st.subheader("📋 Estrutura de Recusas (Replica do Excel)")

# Ordenamos as categorias para aparecerem na ordem 1, 2, 3...
ordem_categorias = sorted(df_filtered['Categoria_Excel'].unique())

for cat in ordem_categorias:
    if "5." in cat: continue # Pula a categoria de outros se quiser um layout limpo
    
    # Estilização baseada na categoria
    if "Rejeitadas" in cat:
        st.error(f"**{cat.upper()}**")
    elif "Pagos" in cat:
        st.success(f"**{cat.upper()}**")
    else:
        st.info(f"**{cat.upper()}**")
    
    # Filtragem para a tabela
    df_cat = df_filtered[df_filtered['Categoria_Excel'] == cat]
    
    # Seleção da coluna de motivo (Motor vs Analise)
    col_motivo = 'motivo_da_decisao' if "No Motor" in cat else 'status_da_analise'
    
    if col_motivo in df_cat.columns:
        resumo = df_cat[col_motivo].value_counts().reset_index()
        resumo.columns = ['Motivo Detalhado', 'Qtd']
        
        st.dataframe(resumo, use_container_width=True, hide_index=True)
        
        # Faixa de Total Amarela (Excel Style)
        st.warning(f"**TOTAL {cat}: {resumo['Qtd'].sum()}**")
    st.write("") 

# --- FUNIL ---
st.divider()
fig = go.Figure(go.Funnel(
    y = ["Leads (Criação)", "Aprovados", "Pagos"],
    x = [total, 
         len(df_filtered[df_filtered['status_da_analise'] == 'APPROVED']), 
         pagos],
    textinfo = "value+percent initial"
))
st.plotly_chart(fig, use_container_width=True)
