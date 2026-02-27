import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Dashboard Funil Topa+", layout="wide")

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
        
        # Datas e Meses
        df['Data de Criação'] = pd.to_datetime(df['Data de Criação'], errors='coerce', dayfirst=True)
        meses_pt = {1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho", 
                    7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"}
        df['Filtro_Mes'] = df['Data de Criação'].dt.month.map(meses_pt).fillna(df['Origem'])
        
        # Limpeza de strings
        for c in ['status_da_proposta', 'status_da_analise', 'motivo_da_decisao']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip()
        
        # --- LIMPEZA DE VALORES (COLUNA K) ---
        col_valor = df.columns[10] 
        # Força a remoção de pontos de milhar e troca vírgula por ponto para o Python somar certo
        df[col_valor] = (
            df[col_valor].astype(str)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
        )
        df[col_valor] = pd.to_numeric(df[col_valor], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Erro crítico no carregamento: {e}")
        return pd.DataFrame()

# Definição crucial para evitar o NameError
df_base = load_data()

# --- LÓGICA DE EXIBIÇÃO ---
# Se o df_base falhar, paramos o app aqui para não dar erro de NameError depois
if df_base.empty:
    st.warning("A base de dados está vazia ou não pôde ser carregada.")
    st.stop()

# ... [Mantenha aqui seu código de Filtros Laterais até chegar na Lógica de Cálculo] ...

# --- LÓGICA DE CÁLCULO DO FUNIL ---

def get_count(df, mapping, col):
    return len(df[df[col].isin(mapping.keys())])

def format_br(valor):
    """Formata número para o padrão brasileiro R$ 1.234,56"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

col_valor = df_base.columns[10]

# 1. Novos Leads
n_leads_sel = len(df_sel)

# 2. Leads com Token Aprovado
v_nao_eng_sel = get_count(df_sel, map_nao_engajados, 'status_da_proposta')
token_aprov_sel = n_leads_sel - v_nao_eng_sel

# 3. Leads Sujeito a Motor
v_rej_pre_sel = get_count(df_sel, map_pre_motor, 'status_da_analise')
sujeito_motor_sel = token_aprov_sel - v_rej_pre_sel

# 4. Leads com Propostas Disponíveis + VALOR
v_rej_motor_sel = get_count(df_sel, map_motor, 'motivo_da_decisao')
prop_disp_sel = sujeito_motor_sel - v_rej_motor_sel
df_prop_disp = df_sel[
    (~df_sel['status_da_proposta'].isin(map_nao_engajados.keys())) & 
    (~df_sel['status_da_analise'].isin(map_pre_motor.keys())) & 
    (~df_sel['motivo_da_decisao'].isin(map_motor.keys()))
]
val_prop_disp = float(df_prop_disp[col_valor].sum())

# 5. Leads com Contrato Gerado + VALOR
df_contrato_ger = df_prop_disp[~df_prop_disp['status_da_proposta'].isin(map_nao_avancaram.keys())]
contrato_ger_sel = len(df_contrato_ger)
val_contrato_ger = float(df_contrato_ger[col_valor].sum())

# 6. Contratos Pagos + VALOR
df_pagos = df_sel[df_sel['status_da_proposta'] == 'DISBURSED']
contratos_pagos_sel = len(df_pagos)
val_pagos = float(df_pagos[col_valor].sum())

# --- RENDERIZAÇÃO DO GRÁFICO ---

st.title("📊 Dashboard Funil Analítico Topa+")
col1, col2 = st.columns([1.2, 1])

with col1:
    labels_funil = [
        f"{n_leads_sel}",
        f"{token_aprov_sel}",
        f"{sujeito_motor_sel}",
        f"{prop_disp_sel}<br>{format_br(val_prop_disp)}",
        f"{contrato_ger_sel}<br>{format_br(val_contrato_ger)}",
        f"{contratos_pagos_sel}<br>{format_br(val_pagos)}"
    ]

    fig = go.Figure(go.Funnel(
        y=["Novos Leads", "Token Aprovado", "Sujeito Motor", "Prop. Disponíveis", "Contrato Gerado", "Pagos"],
        x=[n_leads_sel, token_aprov_sel, sujeito_motor_sel, prop_disp_sel, contrato_ger_sel, contratos_pagos_sel],
        text=labels_funil,
        textinfo="text+percent initial",
        textposition="inside",      # Coloca o valor DENTRO da barra
        insidetextanchor="middle",   # Centraliza o texto
        insidetextfont=dict(color="white", size=14),
        marker=dict(color="royalblue")
    ))
    
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=600)
    st.plotly_chart(fig, use_container_width=True)
