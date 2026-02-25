import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. Configuração inicial
st.set_page_config(page_title="Dashboard Funil Topa+", layout="wide")

@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1-ttYZTqw_8JhU3zA1JAKYaece_iJ-CBrdeoTzNKMZ3I"
    url_dez = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Dez"
    url_jan = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Jan"
    
    try:
        df_dez = pd.read_csv(url_dez)
        df_dez['Origem_Aba'] = 'Dezembro'
        df_jan = pd.read_csv(url_jan)
        df_jan['Origem_Aba'] = 'Janeiro'
        
        df = pd.concat([df_dez, df_jan], ignore_index=True)
        df = df.dropna(how='all')

        df['Data de Criação'] = pd.to_datetime(df['Data de Criação'], errors='coerce', dayfirst=True)
        meses_pt = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 
                    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        
        df['Filtro_Mes'] = df['Data de Criação'].dt.month.map(meses_pt)
        df['Filtro_Mes'] = df['Filtro_Mes'].fillna(df['Origem_Aba'])
        
        # LIMPEZA CRÍTICA: Remove espaços extras no início e fim de todas as colunas de status
        for col in ['status_da_proposta', 'status_da_analise', 'motivo_da_decisao']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame()

df_base = load_data()

# --- SIDEBAR E FILTROS ---
def reset_filtros():
    for key in ['digitador_unico', 'top15_multi']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

st.sidebar.header("Filtros de Visão")
lista_meses = ["Todos"] + sorted(df_base['Filtro_Mes'].dropna().unique().tolist())
mes_sel = st.sidebar.selectbox("Selecione o Mês", lista_meses)

df_mes = df_base.copy()
if mes_sel != "Todos":
    df_mes = df_mes[df_mes['Filtro_Mes'] == mes_sel]

top_15_list = df_mes[df_mes['status_da_proposta'] == 'DISBURSED']['Digitado por'].value_counts().nlargest(15).index.tolist()

st.sidebar.divider()
disable_unico = bool(st.session_state.get('top15_multi'))
disable_top15 = bool(st.session_state.get('digitador_unico') and st.session_state.digitador_unico != "Todos")

dig_sel = st.sidebar.selectbox("Selecione o Digitador", ["Todos"] + sorted(df_base['Digitado por'].unique().tolist()), 
                               key="digitador_unico", disabled=disable_unico)
top15_sel = st.sidebar.multiselect("Digitadores Top 15 (Pagos)", top_15_list, 
                                   key="top15_multi", disabled=disable_top15)

if st.sidebar.button("Limpar Filtros"):
    reset_filtros()

df_sel = df_mes.copy()
if top15_sel: df_sel = df_sel[df_sel['Digitado por'].isin(top15_sel)]
elif dig_sel != "Todos": df_sel = df_sel[df_sel['Digitado por'] == dig_sel]

# --- MAPEAMENTOS CONSOLIDADOS (CONFORME SOLICITADO) ---

map_nao_engajados = {'CREATED': 'Proposta Iniciada', 'TOKEN_SENT': 'Token Enviado'}

map_pre_motor = {
    'NO_AVAILABLE_MARGIN': 'Dataprev - Negado - Sem Margem',
    'CPF_EMPLOYER': 'Dataprev - Negado - Não É CLT',
    'SEM_DADOS_DATAPREV': 'Dataprev - Negado - Não É CLT',
    'NOT_AUTHORIZED_DATAPREV': 'Dataprev - Negado - Não É Elegível',
    'FAILED_DATAPREV': 'Dataprev - DataPrev Fora',
    'CREDIT_ENGINE_ERROR': 'Bull - Erro no Motor Bull'
}

# Aqui estão as correções de consolidação para os 313 de Porte Empresa
map_motor = {
    'Quantidade de Funcionarios': 'Porte Empresa - CNPJ',
    'Negar = Quantidade de Funcionarios entre 1 e 50': 'Porte Empresa - CNPJ',
    'Porte do empregador': 'Porte Empresa - CNPJ',
    'Negar = Tempo Fundacao da Empresa menor que 12 meses': 'Tempo Fundação - CNPJ',
    'Tempo Fundacao da Empresa': 'Tempo Fundação - CNPJ',
    'FGTS Irregular': 'FGTS CNPJ Irregular - CNPJ',
    'Valor margem rejeitado': 'Margem Mínima - PF',
    'Limite inferior ao piso mínimo': 'Valor Min de Margem - PF (dupla checagem)',
    'Faixa de Renda': 'Faixa de Renda - PF',
    'Faixa de Renda < 1 Salario Minimo': 'Faixa de Renda - PF',
    'Possui Alertas': 'Alertas - PF',
    'Tempo de Emprego': 'Tempo de Emprego Atual - PF',
    'Tempo de Emprego Menor que 3 meses': 'Tempo de Emprego Atual - PF',
    'Tempo do contrato do primeiro emprego < 12 meses': 'Tempo de Carteira Assinada - PF',
    'CPF Nao Esta Regular na Receita Federal': 'CPF Irregular - PF',
    'Esta sob sancao': 'Sob Sanção - PF',
    'Nacionalidade diferente de brasileiro': 'Não Brasileiro - PF',
    'Faixa etaria': 'Faixa Etária - PF',
    'Faixa etaria Ate 17 anos OU Acima de 60 anos': 'Faixa Etária - PF',
    'Pessoa Exposta Politicamente': 'PEP - PF',
    'Cliente nao encontrado na base Quod Consulta PF': 'CPF ñ Encontrado Quod - PF'
}

map_nao_avancaram = {'CREDIT_CHECK_COMPLETED': 'Proposta não Aceita', 'PRE_ACCEPTED': 'Proposta Ajustada', 'CONTRACT_GENERATION_FAILED': 'Erro no Contrato'}

map_nao_validados = {
    'SIGNATURE_FAILED': 'Contrato Recusado no AntiFraude',
    'CANCELED': 'Cancelado pelo Tomador Pré Desembolso',
    'EXPIRED': 'Contrato Expirado',
    'ANALYSIS_REPROVED': 'Analise Mesa Reprovada',
    'ERROR': 'Falha na averbação',
    'CANCELLED_BY_USER': 'Cancelado pelo Tomador Pós Desembolso'
}

# --- FUNÇÃO DE CÁLCULO E TABELA ---

def block_ui(label, val, p, df_s, df_m, mapping, col):
    with st.expander(f"📌 {label}: {val} ({p:.1f}%)"):
        # Filtra as linhas que batem com as chaves do mapa
        df_sub_s = df_s[df_s[col].isin(mapping.keys())].copy()
        df_sub_m = df_m[df_m[col].isin(mapping.keys())].copy()
