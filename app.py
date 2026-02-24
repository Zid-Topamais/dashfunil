import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. Configuração da página
st.set_page_config(page_title="Dashboard Topa+ Realtime", layout="wide")

# 2. Função de Carga com tratamento de valores nulos
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1-ttYZTqw_8JhU3zA1JAKYaece_iJ-CBrdeoTzNKMZ3I"
    url_dez = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Dez"
    url_jan = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Jan"
    
    df_dez = pd.read_csv(url_dez)
    df_jan = pd.read_csv(url_jan)
    df = pd.concat([df_dez, df_jan], ignore_index=True)
    
    # Limpeza de linhas totalmente vazias
    df = df.dropna(how='all')

    # --- DICIONÁRIO DE MAPEAMENTO (REPLICANDO O EXCEL) ---
    def mapear_categoria(row):
        # Converte para string e remove espaços para evitar erros
        status_analise = str(row.get('status_da_analise', '')).strip().upper()
        status_proposta = str(row.get('status_da_proposta', '')).strip().upper()
        
        # 1. Propostas Rejeitadas Pré-Motor
        pre_motor_errors = [
            'NO_AVAILABLE_MARGIN', 'CPF_EMPLOYER_SEM_DADOS_DATAPREV', 
            'NOT_AUTHORIZED_DATAPREV', 'FAILED_DATAPREV', 'CREDIT_ENGINE_ERROR'
        ]
        if status_analise in pre_motor_errors:
            return "⚠️ Propostas Rejeitadas Pré-Motor"
        
        # 2. Propostas Rejeitadas No Motor
        if status_analise == 'REJECTED':
            return "🚫 Propostas Rejeitadas No Motor"
        
        # 3. Sucesso / Pagos
        if status_proposta == 'DISBURSED':
            return "✅ Contratos Pagos"
            
        return "🔍 Outros / Em Processamento"

    df['Categoria_Excel'] = df.apply(mapear_categoria, axis=1)
    return df

# Execução da carga
try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

# --- SIDEBAR ---
st.sidebar.header("Filtros")
digitador_col = 'Digitado por'
if digitador_col in df.columns:
    digitadores = sorted(df[digitador_col].dropna().unique().tolist())
    digitador_selecionado = st.sidebar.selectbox("Selecione o Digitador", ["Todos"] + digitadores)
    df_filtered = df if digitador_selecionado == "Todos" else df[df[digitador_col] == digitador_selecionado]
else:
    df_filtered = df
    digitador_selecionado = "Geral"

# --- TÍTULO ---
st.title(f"📊 Dashboard Analítico - {digitador_selecionado}")

# --- MÉTRICAS RÁPIDAS ---
c1, c2, c3 = st.columns(3)
total = len(df_filtered)
pagos = len(df_filtered[df_filtered['Categoria_Excel'] == "✅ Contratos Pagos"])
c1.metric("Total Leads", total)
c2.metric("Pagos", pagos)
c3.metric("% Conversão", f"{(pagos/total*100 if total > 0 else 0):.1f}%")

st.divider()

# --- REPLICANDO O DESIGN DO EXCEL ---
st.subheader("📋 Tabela de Recusas (Estrutura Excel)")

# Pegamos as categorias únicas, garantindo que não há NaNs que causam o TypeError
categorias_unificadas = [cat for cat in df_filtered['Categoria_Excel'].unique() if pd.notna(cat)]

for cat in sorted(categorias_unificadas):
    if "Processamento" in str(cat): continue
    
    # Define a cor baseada no nome (Azul para erros, Verde para Sucesso)
    cor_box = "#1f4e78" if "Rejeitadas" in str(cat) else "#548235"
    
    # Renderização do cabeçalho da categoria (A correção do erro está no str(cat))
    st.markdown(f"""
        <div style="background-color:{cor_box}; color:white; padding:8px; border-radius:5px; font-weight:bold; margin-top:20px;">
            {str(cat).upper()}
        </div>
    """, unsafe_allow_all_with_html=True)
    
    # Filtra os dados desta categoria
    df_cat = df_filtered[df_filtered['Categoria_Excel'] == cat]
    
    # Decide qual coluna mostrar como "Motivo"
    # Se for motor, mostra 'motivo_da_decisao', se for pré-motor, mostra 'status_da_analise'
    col_detalhe = 'motivo_da_decisao' if "Motor" in str(cat) and "Pré" not in str(cat) else 'status_da_analise'
    
    if col_detalhe in df_cat.columns:
        resumo = df_cat[col_detalhe].value_counts().reset_index()
        resumo.columns = ['Motivo Detalhado', 'Qtd']
        
        # Exibe a tabela estilizada
        st.dataframe(resumo, use_container_width=True, hide_index=True)
        
        # Faixa de Total (Amarela igual ao Excel)
        total_cat = resumo['Qtd'].sum()
        st.markdown(f"""
            <div style="background-color:#fff2cc; padding:5px; text-align:right; font-weight:bold; border:1px solid #d6ad33;">
                TOTAL {str(cat)}: {total_cat}
            </div>
        """, unsafe_allow_all_with_html=True)

# --- FUNIL ---
st.divider()
st.subheader("🎯 Visão Funil de Vendas")
fig = go.Figure(go.Funnel(
    y = ["Leads Total", "Aprovados Motor", "Contratos Pagos"],
    x = [len(df_filtered), 
         len(df_filtered[df_filtered['status_da_analise'] == 'APPROVED']), 
         pagos],
    textinfo = "value+percent initial"
))
st.plotly_chart(fig, use_container_width=True)
