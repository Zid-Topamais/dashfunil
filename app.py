import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. Configuração da página
st.set_page_config(page_title="Dashboard Topa+ Realtime", layout="wide")

# 2. Função de Carga (Usando o método direto para evitar erros de conexão)
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1-ttYZTqw_8JhU3zA1JAKYaece_iJ-CBrdeoTzNKMZ3I"
    # Certifique-se de que os nomes abaixo são EXATAMENTE os das abas na sua planilha
    url_dez = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Dez"
    url_jan = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Jan"
    
    df_dez = pd.read_csv(url_dez)
    df_jan = pd.read_csv(url_jan)
    df = pd.concat([df_dez, df_jan], ignore_index=True)
    
    # --- LÓGICA DE MAPEAMENTO (REPLICANDO O EXCEL) ---
    def mapear_categoria(row):
        status_bull = str(row.get('status_da_analise', '')).upper()
        # Categoria: Pré-Motor
        if status_bull in ['NO_AVAILABLE_MARGIN', 'CPF_EMPLOYER_SEM_DADOS_DATAPREV', 'NOT_AUTHORIZED_DATAPREV', 'FAILED_DATAPREV', 'CREDIT_ENGINE_ERROR']:
            return "⚠️ Propostas Rejeitadas Pré-Motor"
        # Categoria: No Motor
        elif status_bull == 'REJECTED':
            return "🚫 Propostas Rejeitadas No Motor"
        # Categoria: Sucesso/Pagos
        elif str(row.get('status_da_proposta', '')).upper() == 'DISBURSED':
            return "✅ Contratos Pagos"
        return "Outros / Em processamento"

    df['Categoria_Excel'] = df.apply(mapear_categoria, axis=1)
    return df

# Execução
try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

# --- SIDEBAR ---
st.sidebar.header("Filtros")
digitadores = sorted(df['Digitado por'].dropna().unique().tolist())
digitador_selecionado = st.sidebar.selectbox("Selecione o Digitador", ["Todos"] + digitadores)
df_filtered = df if digitador_selecionado == "Todos" else df[df['Digitado por'] == digitador_selecionado]

# --- DESIGN REPLICADO (ESTILO EXCEL) ---
st.title(f"📊 Dashboard Analítico - {digitador_selecionado}")

# Cards de Resumo Superior
m1, m2, m3 = st.columns(3)
m1.metric("Total Leads", len(df_filtered))
m2.metric("Pagos", len(df_filtered[df_filtered['status_da_proposta'] == 'DISBURSED']))
m3.metric("% Conversão", f"{(len(df_filtered[df_filtered['status_da_proposta'] == 'DISBURSED'])/len(df_filtered)*100):.1f}%")

st.divider()

# Replicando a tabela de "Motivos de Recusa" da imagem
st.subheader("📋 Tabela de Recusas (Design Excel)")

# Criando a estrutura de tópicos
categorias = df_filtered['Categoria_Excel'].unique()

for cat in sorted(categorias):
    if cat == "Outros / Em processamento": continue
    
    # Estilização de "Cabeçalho de Categoria" igual ao Excel (Azul/Verde)
    cor = "#1f4e78" if "Rejeitadas" in cat else "#548235"
    st.markdown(f"""<div style="background-color:{cor};color:white;padding:5px;border-radius:5px;font-weight:bold;">{cat}</div>""", unsafe_allow_all_with_html=True)
    
    # Subtabela com os motivos específicos
    df_cat = df_filtered[df_filtered['Categoria_Excel'] == cat]
    
    # Se for "No Motor", detalhamos pela coluna 'motivo_da_decisao'
    col_detalhe = 'motivo_da_decisao' if "No Motor" in cat else 'status_da_analise'
    
    if col_detalhe in df_cat.columns:
        resumo = df_cat[col_detalhe].value_counts().reset_index()
        resumo.columns = ['Motivo Específico', 'Quantidade']
        
        # Exibe a tabela sem o índice para ficar limpo
        st.dataframe(resumo, use_container_width=True, hide_index=True)
        
        # Linha de TOTAL da categoria igual ao Excel (Amarelo claro)
        total_cat = resumo['Quantidade'].sum()
        st.markdown(f"""<div style="background-color:#fff2cc;padding:3px;text-align:right;font-weight:bold;margin-bottom:20px;">TOTAL: {total_cat}</div>""", unsafe_allow_all_with_html=True)

# --- GRÁFICO DE FUNIL ---
st.divider()
st.subheader("🎯 Visão Funil")
fig = go.Figure(go.Funnel(
    y = ["Leads", "Aprovados Motor", "Pagos"],
    x = [len(df_filtered), len(df_filtered[df_filtered['status_da_analise'] == 'APPROVED']), len(df_filtered[df_filtered['status_da_proposta'] == 'DISBURSED'])],
    textinfo = "value+percent initial"
))
st.plotly_chart(fig, use_container_width=True)
