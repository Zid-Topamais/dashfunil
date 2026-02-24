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
        df = pd.concat([df_dez, df_jan], ignore_index=True)
        df = df.dropna(how='all')
    except Exception as e:
        return pd.DataFrame() # Retorna vazio em caso de erro crítico

    # --- MAPEAMENTO DE CATEGORIAS ---
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
    st.error("Não foi possível carregar os dados. Verifique o compartilhamento da planilha.")
    st.stop()

# --- SIDEBAR ---
digitador_col = 'Digitado por'
st.sidebar.header("Filtros")
if digitador_col in df.columns:
    opcoes = ["Todos"] + sorted(df[digitador_col].dropna().unique().tolist())
    selecao = st.sidebar.selectbox("Selecione o Digitador", opcoes)
    df_filtered = df if selecao == "Todos" else df[df[digitador_col] == selecao]
else:
    df_filtered = df
    selecao = "Geral"

# --- TÍTULO ---
st.title(f"📊 Dashboard Analítico - {selecao}")

# --- MÉTRICAS ---
pago_count = len(df_filtered[df_filtered['Categoria_Excel'] == "3. Contratos Pagos"])
c1, c2, c3 = st.columns(3)
c1.metric("Total Leads", len(df_filtered))
c2.metric("Pagos", pago_count)
c3.metric("% Conversão", f"{(pago_count/len(df_filtered)*100 if len(df_filtered)>0 else 0):.1f}%")

# --- REPLICANDO O DESIGN EXCEL (VERSÃO ESTÁVEL) ---
st.subheader("📋 Tabela de Recusas (Estrutura Excel)")

# Filtrar categorias válidas e ordenar
cats = sorted([str(c) for c in df_filtered['Categoria_Excel'].unique() if "Processamento" not in str(c)])

for cat in cats:
    # Usamos st.error para as faixas vermelhas/azuis e st.success para as verdes
    # Isso evita o uso de HTML manual que está causando o TypeError
    if "Rejeitadas" in cat:
        st.error(f"**{cat.upper()}**")
    else:
        st.success(f"**{cat.upper()}**")
    
    df_cat = df_filtered[df_filtered['Categoria_Excel'] == cat]
    
    # Define a coluna de detalhe
    col_motivo = 'motivo_da_decisao' if "No Motor" in cat and "Pré" not in cat else 'status_da_analise'
    
    if col_motivo in df_cat.columns:
        resumo = df_cat[col_motivo].value_counts().reset_index()
        resumo.columns = ['Motivo Detalhado', 'Quantidade']
        
        # Exibição da Tabela
        st.dataframe(resumo, use_container_width=True, hide_index=True)
        
        # Faixa de Total usando st.warning (Fundo amarelado como no Excel)
        st.warning(f"**TOTAL {cat}: {resumo['Quantidade'].sum()}**")
    st.write("") # Espaçador

# --- FUNIL ---
st.divider()
fig = go.Figure(go.Funnel(
    y = ["Leads", "Aprovados", "Pagos"],
    x = [len(df_filtered), 
         len(df_filtered[df_filtered['status_da_analise'] == 'APPROVED']), 
         pago_count],
    textinfo = "value+percent initial"
))
st.plotly_chart(fig, use_container_width=True)
