import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. Configuração da página
st.set_page_config(page_title="Dashboard Topa+ Realtime", layout="wide")

# 2. Função de Carga Robusta
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1-ttYZTqw_8JhU3zA1JAKYaece_iJ-CBrdeoTzNKMZ3I"
    url_dez = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Dez"
    url_jan = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Jan"
    
    try:
        df_dez = pd.read_csv(url_dez)
        df_jan = pd.read_csv(url_jan)
        
        # Adiciona identificação de mês baseada na aba de origem
        df_dez['Mes_Ref'] = 'Dezembro'
        df_jan['Mes_Ref'] = 'Janeiro'
        
        df = pd.concat([df_dez, df_jan], ignore_index=True)
        df = df.dropna(how='all')
    except Exception as e:
        return pd.DataFrame()

    # --- MAPEAMENTO DE CATEGORIAS (ESTILO EXCEL) ---
    def mapear_categoria(row):
        status_analise = str(row.get('status_da_analise', '')).strip().upper()
        status_proposta = str(row.get('status_da_proposta', '')).strip().upper()
        
        pre_motor = ['NO_AVAILABLE_MARGIN', 'CPF_EMPLOYER_SEM_DADOS_DATAPREV', 
                     'NOT_AUTHORIZED_DATAPREV', 'FAILED_DATAPREV', 'CREDIT_ENGINE_ERROR']
        
        if status_analise in pre_motor:
            return "1. Propostas Rejeitadas Pré-Motor"
        elif status_analise == 'REJECTED':
            return "2. Propostas Rejeitadas No Motor"
        elif status_proposta == 'DISBURSED':
            return "3. Contratos Pagos"
        return "4. Outros / Processamento"

    df['Categoria_Excel'] = df.apply(mapear_categoria, axis=1)
    return df

# Execução
df = load_data()

if df.empty:
    st.error("Erro ao carregar dados. Verifique a planilha.")
    st.stop()

# --- SIDEBAR (FILTROS) ---
st.sidebar.header("Filtros de Visão")

# Filtro de Mês [Novo]
meses_disponiveis = ["Todos"] + sorted(df['Mes_Ref'].unique().tolist(), reverse=True)
mes_selecionado = st.sidebar.selectbox("Selecione o Mês", meses_disponiveis)

# Filtro de Digitador
digitador_col = 'Digitado por'
if digitador_col in df.columns:
    opcoes_digitador = ["Todos"] + sorted(df[digitador_col].dropna().unique().tolist())
    digitador_selecionado = st.sidebar.selectbox("Selecione o Digitador", opcoes_digitador)
else:
    digitador_selecionado = "Todos"

# --- APLICAÇÃO DOS FILTROS ---
df_filtered = df.copy()

if mes_selecionado != "Todos":
    df_filtered = df_filtered[df_filtered['Mes_Ref'] == mes_selecionado]

if digitador_selecionado != "Todos":
    df_filtered = df_filtered[df_filtered[digitador_col] == digitador_selecionado]

# --- TÍTULO ---
st.title(f"📊 Dashboard Analítico")
st.subheader(f"Visão: {mes_selecionado} | Digitador: {digitador_selecionado}")

# --- MÉTRICAS ---
total_leads = len(df_filtered)
pago_count = len(df_filtered[df_filtered['Categoria_Excel'] == "3. Contratos Pagos"])
c1, c2, c3 = st.columns(3)
c1.metric("Total Leads", total_leads)
c2.metric("Pagos", pago_count)
c3.metric("% Conversão", f"{(pago_count/total_leads*100 if total_leads > 0 else 0):.1f}%")

# --- TABELA DE RECUSAS (ESTILO EXCEL) ---
st.divider()
st.subheader("📋 Estrutura de Recusas (Replica do Excel)")

cats = sorted([str(c) for c in df_filtered['Categoria_Excel'].unique() if "Processamento" not in str(c)])

for cat in cats:
    if "Rejeitadas" in cat:
        st.error(f"**{cat.upper()}**")
    else:
        st.success(f"**{cat.upper()}**")
    
    df_cat = df_filtered[df_filtered['Categoria_Excel'] == cat]
    col_motivo = 'motivo_da_decisao' if "No Motor" in cat and "Pré" not in cat else 'status_da_analise'
    
    if col_motivo in df_cat.columns:
        resumo = df_cat[col_motivo].value_counts().reset_index()
        resumo.columns = ['Motivo Detalhado', 'Quantidade']
        st.dataframe(resumo, use_container_width=True, hide_index=True)
        st.warning(f"**TOTAL {cat}: {resumo['Quantidade'].sum()}**")
    st.write("")

# --- GRÁFICO ---
fig = go.Figure(go.Funnel(
    y = ["Leads", "Pagos"],
    x = [total_leads, pago_count],
    textinfo = "value+percent initial"
))
st.plotly_chart(fig, use_container_width=True)
