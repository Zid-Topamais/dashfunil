import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. Configuração da página
st.set_page_config(page_title="Dashboard Funil Topa+", layout="wide")

# 2. Função de Carga
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

        # Tratamento de Data
        df['Data de Criação'] = pd.to_datetime(df['Data de Criação'], errors='coerce', dayfirst=True)
        meses_pt = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 
                    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        df['Filtro_Mes'] = df['Data de Criação'].dt.month.map(meses_pt)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

df_base = load_data()

# --- SIDEBAR ---
st.sidebar.header("Filtros")
lista_meses = ["Todos"] + sorted(df_base['Filtro_Mes'].dropna().unique().tolist())
mes_sel = st.sidebar.selectbox("Mês", lista_meses)
opcoes_digitador = ["Todos"] + sorted(df_base['Digitado por'].dropna().unique().tolist())
dig_sel = st.sidebar.selectbox("Digitador", opcoes_digitador)

# Filtros
df = df_base.copy()
if mes_sel != "Todos": df = df[df['Filtro_Mes'] == mes_sel]
if dig_sel != "Todos": df = df[df['Digitado por'] == dig_sel]

# --- LÓGICA DO FUNIL ---

# 1. Novos Leads
novos_leads = len(df)

# Sub: Leads Não Engajados (CREATED, TOKEN_SENT na Col AB)
status_proposta_map = {
    'CREATED': 'Proposta Iniciada',
    'TOKEN_SENT': 'Token Enviado'
}
df_nao_engajados = df[df['status_da_proposta'].isin(['CREATED', 'TOKEN_SENT'])]
total_nao_engajados = len(df_nao_engajados)

# 2. Leads com Token Aprovado
leads_token_aprovado = novos_leads - total_nao_engajados

# Sub: Pré Motor (Col AA)
pre_motor_map = {
    'NO_AVAILABLE_MARGIN': 'Dataprev - Negado - Sem Margem',
    'CPF_EMPLOYER': 'Dataprev - Negado - Não É CLT',
    'SEM_DADOS_DATAPREV': 'Dataprev - Negado - Não É CLT',
    'NOT_AUTHORIZED_DATAPREV': 'Dataprev - Negado - Não É Elegível',
    'FAILED_DATAPREV': 'Dataprev - DataPrev Fora',
    'CREDIT_ENGINE_ERROR': 'Bull - Erro no Motor Bull'
}
df_pre_motor = df[df['status_da_analise'].isin(pre_motor_map.keys())]
total_pre_motor = len(df_pre_motor)

# 3. Leads Sujeito a Motor
leads_sujeito_motor = leads_token_aprovado - total_pre_motor

# Sub: No Motor (Col AD - motivo_da_decisao)
motor_map = {
    'Quantidade de Funcionarios': 'Porte Empresa - CNPJ',
    'Quantidade de Funcionarios entre 1 e 50': 'Porte Empresa - CNPJ',
    'Porte do empregador': 'Porte Empresa - CNPJ',
    'Tempo Fundacao da Empresa menor que 12 meses': 'Tempo Fundação - CNPJ',
    'Tempo Fundacao da Empresa': 'Tempo Fundação - CNPJ',
    'FGTS Irregular': 'FGTS CNPJ Irregular - CNPJ',
    'Valor margem rejeitado': 'Margem Mínima - PF',
    'Limite inferior ao piso mínimo': 'Valor Min de Margem - PF',
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
df_no_motor = df[df['motivo_da_decisao'].isin(motor_map.keys())]
total_no_motor = len(df_no_motor)

# 4. Propostas Disponíveis
propostas_disponiveis = leads_sujeito_motor - total_no_motor

# Sub: Não avançaram (Col AB)
nao_avancaram_map = {
    'CREDIT_CHECK_COMPLETED': 'Proposta não Aceita',
    'PRE_ACCEPTED': 'Proposta Ajustada',
    'CONTRACT_GENERATION_FAILED': 'Erro no Contrato'
}
df_nao_avancaram = df[df['status_da_proposta'].isin(nao_avancaram_map.keys())]
total_nao_avancaram = len(df_nao_avancaram)

# 5. Contrato Gerado
contrato_gerado = propostas_disponiveis - total_nao_avancaram

# Sub: Não validados (Col AB)
nao_validados_map = {
    'SIGNATURE_FAILED': 'Contrato Recusado no AntiFraude',
    'CANCELED': 'Cancelado pelo Tomador Pré Desembolso',
    'EXPIRED': 'Contrato Expirado',
    'ANALYSIS_REPROVED': 'Analise Mesa Reprovada',
    'ERROR': 'Falha na averbação',
    'CANCELLED_BY_USER': 'Cancelado pelo Tomador Pós Desembolso'
}
df_nao_validados = df[df['status_da_proposta'].isin(nao_validados_map.keys())]
total_nao_validados = len(df_nao_validados)

# 6. Contratos Pagos
contratos_pagos = len(df[df['status_da_proposta'] == 'DISBURSED'])

# --- EXIBIÇÃO ---
st.title("📊 Funil de Conversão Analítico")

# Gráfico de Funil
fig = go.Figure(go.Funnel(
    y = ["Novos Leads", "Token Aprovado", "Sujeito a Motor", "Propostas Disponíveis", "Contrato Gerado", "Pagos"],
    x = [novos_leads, leads_token_aprovado, leads_sujeito_motor, propostas_disponiveis, contrato_gerado, contratos_pagos],
    textinfo = "value+percent initial"
))
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- DRILL DOWN POR CATEGORIAS ---

def render_sub(df_sub, mapping, col_ref):
    if len(df_sub) > 0:
        counts = df_sub[col_ref].value_counts().reset_index()
        counts.columns = ['Status Base', 'Qtd']
        counts['Descrição'] = counts['Status Base'].map(mapping)
        # Agrupa por descrição para somar status que tem o mesmo nome amigável
        final = counts.groupby('Descrição')['Qtd'].sum().reset_index()
        st.table(final)
        st.warning(f"**Total da Subcategoria: {final['Qtd'].sum()}**")
    else:
        st.info("Nenhum registro nesta subcategoria.")

# Categoria 1
with st.expander(f"🔵 Novos Leads: {novos_leads}"):
    st.subheader("Leads Não Engajados")
    render_sub(df_nao_engajados, status_proposta_map, 'status_da_proposta')

# Categoria 2
with st.expander(f"🟢 Leads com Token Aprovado: {leads_token_aprovado}"):
    st.subheader("Propostas Rejeitadas Pré Motor")
    render_sub(df_pre_motor, pre_motor_map, 'status_da_analise')

# Categoria 3
with st.expander(f"🟠 Leads Sujeito a Motor: {leads_sujeito_motor}"):
    st.subheader("Propostas Rejeitadas No Motor")
    render_sub(df_no_motor, motor_map, 'motivo_da_decisao')

# Categoria 4
with st.expander(f"🟡 Leads com Propostas Disponíveis: {propostas_disponiveis}"):
    st.subheader("Propostas Que Não Avançaram para Contrato")
    render_sub(df_nao_avancaram, nao_avancaram_map, 'status_da_proposta')

# Categoria 5
with st.expander(f"🟣 Leads com Contrato Gerado: {contrato_gerado}"):
    st.subheader("Contratos Não Validados")
    render_sub(df_nao_validados, nao_validados_map, 'status_da_proposta')

# Categoria 6
with st.expander(f"🏆 Contratos Pagos: {contratos_pagos}"):
    st.success(f"Total de Contratos Pagos: {contratos_pagos}")
