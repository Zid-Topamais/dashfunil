import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. Configuração da Página
st.set_page_config(page_title="Dashboard Funil Topa+", layout="wide")

# 2. Carregamento e Limpeza de Dados
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1-ttYZTqw_8JhU3zA1JAKYaece_iJ-CBrdeoTzNKMZ3I"
    url_dez = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Dez"
    url_jan = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Jan"
    try:
        df_dez = pd.read_csv(url_dez)
        df_dez['Origem'] = 'Dezembro'
        df_jan = pd.read_csv(url_jan)
        df_jan['Origem'] = 'Janeiro'
        
        df = pd.concat([df_dez, df_jan], ignore_index=True).dropna(how='all')
        
        # Tratamento de Datas
        df['Data de Criação'] = pd.to_datetime(df['Data de Criação'], errors='coerce', dayfirst=True)
        meses_pt = {1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho", 
                    7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"}
        df['Filtro_Mes'] = df['Data de Criação'].dt.month.map(meses_pt).fillna(df['Origem'])
        
        # Limpeza de Strings
        for c in ['status_da_proposta', 'status_da_analise', 'motivo_da_decisao']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip()
        
        # CORREÇÃO FINANCEIRA (Coluna K - Índice 10)
        col_valor = df.columns[10] 
        df[col_valor] = (
            df[col_valor].astype(str)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
        )
        df[col_valor] = pd.to_numeric(df[col_valor], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar base: {e}")
        return pd.DataFrame()

df_base = load_data()

if df_base.empty:
    st.warning("Aguardando carregamento de dados...")
    st.stop()

# 3. Funções Auxiliares
def get_count(df, mapping, col):
    return len(df[df[col].isin(mapping.keys())])

def format_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# 4. Filtros Laterais (Sidebar)
st.sidebar.header("🎯 Configurações do Funil")

lista_meses = ["Todos"] + sorted(df_base['Filtro_Mes'].unique().tolist())
mes_sel = st.sidebar.selectbox("Mês de Referência", lista_meses, key="mes_sel")

df_mes = df_base if mes_sel == "Todos" else df_base[df_base['Filtro_Mes'] == mes_sel]

col_empresa = df_base.columns[17]
col_squad = df_base.columns[18]

lista_empresa = ["Todos"] + sorted(df_mes[col_empresa].dropna().unique().tolist())
empresa_sel = st.sidebar.selectbox("Filtrar Empresa", lista_empresa, key="empresa_sel")

df_empresa = df_mes.copy()
if empresa_sel != "Todos":
    df_empresa = df_empresa[df_empresa[col_empresa] == empresa_sel]

lista_equipes = ["Todos"] + sorted(df_empresa[col_squad].dropna().unique().tolist())
equipe_sel = st.sidebar.selectbox("Filtrar Equipe", lista_equipes, key="squad_sel")

df_equipe = df_empresa.copy()
if equipe_sel != "Todos":
    df_equipe = df_equipe[df_equipe[col_squad] == equipe_sel]

# Filtros de Digitador
dig_sel = st.sidebar.selectbox("Digitador Único", ["Todos"] + sorted(df_equipe['Digitado por'].unique().tolist()), key="digitador_unico")

# 5. Definição do df_sel (Resolve o NameError)
df_sel = df_equipe.copy()
if dig_sel != "Todos":
    df_sel = df_sel[df_sel['Digitado por'] == dig_sel]

# 6. Mapeamentos
map_nao_engajados = {'CREATED': 'Proposta Iniciada', 'TOKEN_SENT': 'Token Enviado'}
map_pre_motor = {'NO_AVAILABLE_MARGIN': 'Sem Margem', 'CPF_EMPLOYER': 'Não CLT', 'CREDIT_ENGINE_ERROR': 'Erro Motor'}
map_motor = {'FGTS Irregular': 'FGTS', 'Faixa de Renda': 'Renda', 'Tempo de Emprego': 'Tempo Emprego'}
map_nao_avancaram = {'CREDIT_CHECK_COMPLETED': 'ñ Aceita', 'CONTRACT_GENERATION_FAILED': 'Erro Contrato'}
map_nao_validados = {'CANCELED': 'Cancelado', 'EXPIRED': 'Expirado'}

# 7. Lógica de Cálculo
col_valor = df_base.columns[10]
n_leads_sel = len(df_sel)
token_aprov_sel = n_leads_sel - get_count(df_sel, map_nao_engajados, 'status_da_proposta')
sujeito_motor_sel = token_aprov_sel - get_count(df_sel, map_pre_motor, 'status_da_analise')
prop_disp_sel = sujeito_motor_sel - get_count(df_sel, map_motor, 'motivo_da_decisao')

# Cálculo de Valores Financeiros
df_prop_disp = df_sel[
    (~df_sel['status_da_proposta'].isin(map_nao_engajados.keys())) & 
    (~df_sel['status_da_analise'].isin(map_pre_motor.keys())) & 
    (~df_sel['motivo_da_decisao'].isin(map_motor.keys()))
]
val_prop_disp = float(df_prop_disp[col_valor].sum())

df_contrato_ger = df_prop_disp[~df_prop_disp['status_da_proposta'].isin(map_nao_avancaram.keys())]
contrato_ger_sel = len(df_contrato_ger)
val_contrato_ger = float(df_contrato_ger[col_valor].sum())

df_pagos = df_sel[df_sel['status_da_proposta'] == 'DISBURSED']
contratos_pagos_sel = len(df_pagos)
val_pagos = float(df_pagos[col_valor].sum())

# 8. Renderização
st.title("📊 Dashboard Funil Analítico Topa+")
col1, col2 = st.columns([1.2, 1])

with col1:
    labels_funil = [
        f"{n_leads_sel}", f"{token_aprov_sel}", f"{sujeito_motor_sel}",
        f"{prop_disp_sel}<br>{format_br(val_prop_disp)}",
        f"{contrato_ger_sel}<br>{format_br(val_contrato_ger)}",
        f"{contratos_pagos_sel}<br>{format_br(val_pagos)}"
    ]

    fig = go.Figure(go.Funnel(
        y=["Novos Leads", "Token Aprovado", "Sujeito Motor", "Prop. Disponíveis", "Contrato Gerado", "Pagos"],
        x=[n_leads_sel, token_aprov_sel, sujeito_motor_sel, prop_disp_sel, contrato_ger_sel, contratos_pagos_sel],
        text=labels_funil,
        textinfo="text+percent initial",
        textposition="inside",
        insidetextanchor="middle",
        marker=dict(color="royalblue")
    ))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=600)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.write("### Detalhamento")
    st.info(f"💰 **Total Pago: {format_br(val_pagos)}**")
    # Aqui você pode reinserir suas funções de drill_down_table
