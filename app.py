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
        df_jan = pd.read_csv(url_jan)
        df = pd.concat([df_dez, df_jan], ignore_index=True)
        df = df.dropna(how='all')
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
st.sidebar.header("Filtros de Visão")
lista_meses = ["Todos"] + sorted(df_base['Filtro_Mes'].dropna().unique().tolist())
mes_sel = st.sidebar.selectbox("Selecione o Mês", lista_meses)
opcoes_digitador = ["Todos"] + sorted(df_base['Digitado por'].dropna().unique().tolist())
dig_sel = st.sidebar.selectbox("Selecione o Digitador", opcoes_digitador)

df = df_base.copy()
if mes_sel != "Todos": df = df[df['Filtro_Mes'] == mes_sel]
if dig_sel != "Todos": df = df[df['Digitado por'] == dig_sel]

# --- LÓGICA DO FUNIL COM NOMENCLATURA OFICIAL ---

# 1. Novos Leads
novos_leads = len(df)
# Sub: Leads Não Engajados
map_nao_engajados = {
    'CREATED': 'Proposta Iniciada',
    'TOKEN_SENT': 'Token Enviado'
}
df_nao_engajados = df[df['status_da_proposta'].isin(map_nao_engajados.keys())]
total_nao_engajados = len(df_nao_engajados)

# 2. Leads com Token Aprovado
leads_token_aprovado = novos_leads - total_nao_engajados
# Sub: Propostas Rejeitadas Pré Motor de Crédito
map_pre_motor = {
    'NO_AVAILABLE_MARGIN': 'Dataprev - Negado - Sem Margem',
    'CPF_EMPLOYER': 'Dataprev - Negado - Não É CLT',
    'SEM_DADOS_DATAPREV': 'Dataprev - Negado - Não É CLT',
    'NOT_AUTHORIZED_DATAPREV': 'Dataprev - Negado - Não É Elegível',
    'FAILED_DATAPREV': 'Dataprev - DataPrev Fora',
    'CREDIT_ENGINE_ERROR': 'Bull - Erro no Motor Bull'
}
df_pre_motor = df[df['status_da_analise'].isin(map_pre_motor.keys())]
total_pre_motor = len(df_pre_motor)

# 3. Leads Sujeito a Motor de Crédito
leads_sujeito_motor = leads_token_aprovado - total_pre_motor
# Sub: Propostas Rejeitadas No Motor De Crédito
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
df_no_motor = df[df['motivo_da_decisao'].isin(map_motor.keys())]
total_no_motor = len(df_no_motor)

# 4. Leads Com Propostas Disponíveis
propostas_disponiveis = leads_sujeito_motor - total_no_motor
# Sub: Propostas Que Não Avançaram para Contrato
map_nao_avancaram = {
    'CREDIT_CHECK_COMPLETED': 'Proposta não Aceita',
    'PRE_ACCEPTED': 'Proposta Ajustada',
    'CONTRACT_GENERATION_FAILED': 'Erro no Contrato'
}
df_nao_avancaram = df[df['status_da_proposta'].isin(map_nao_avancaram.keys())]
total_nao_avancaram = len(df_nao_avancaram)

# 5. Leads com Contrato Gerado
contrato_gerado = propostas_disponiveis - total_nao_avancaram
# Sub: Contratos Não Validados
map_nao_validados = {
    'SIGNATURE_FAILED': 'Contrato Recusado no AntiFraude',
    'CANCELED': 'Cancelado pelo Tomador Pré Desembolso',
    'EXPIRED': 'Contrato Expirado',
    'ANALYSIS_REPROVED': 'Analise Mesa Reprovada',
    'ERROR': 'Falha na averbação',
    'CANCELLED_BY_USER': 'Cancelado pelo Tomador Pós Desembolso'
}
df_nao_validados = df[df['status_da_proposta'].isin(map_nao_validados.keys())]
total_nao_validados = len(df_nao_validados)

# 6. Contratos Pagos
contratos_pagos = len(df[df['status_da_proposta'] == 'DISBURSED'])

# --- DISPLAY 50/50 ---
st.title("📊 Dashboard Analítico Funil Topa+")
st.divider()

col_funil, col_detalhe = st.columns([1, 1])

with col_funil:
    st.subheader("🎯 Funil de Conversão")
    fig = go.Figure(go.Funnel(
        y = ["Novos Leads", "Token Aprovado", "Sujeito a Motor", "Propostas Disp.", "Contrato Gerado", "Pagos"],
        x = [novos_leads, leads_token_aprovado, leads_sujeito_motor, propostas_disponiveis, contrato_gerado, contratos_pagos],
        textinfo = "value+percent initial",
        marker = {"color": ["#1f4e78", "#2e75b6", "#5b9bd5", "#9bc2e6", "#ddebf7", "#548235"]}
    ))
    st.plotly_chart(fig, use_container_width=True)

with col_detalhe:
    st.subheader("📂 Categorias e Subcategorias")

    def render_block(titulo, total_cat, df_sub, mapping, col_ref):
        with st.expander(f"📌 {titulo}: {total_cat}"):
            if not df_sub.empty:
                res = df_sub[col_ref].value_counts().reset_index()
                res.columns = ['Status', 'Qtd']
                res['Descrição Apresentada'] = res['Status'].map(mapping)
                final = res.groupby('Descrição Apresentada')['Qtd'].sum().reset_index()
                st.table(final)
                st.warning(f"**Total: {final['Qtd'].sum()}**")
            else:
                st.info("Sem registros nesta subcategoria.")

    render_block("Novos Leads", novos_leads, df_nao_engajados, map_nao_engajados, 'status_da_proposta')
    render_block("Leads com Token Aprovado", leads_token_aprovado, df_pre_motor, map_pre_motor, 'status_da_analise')
    render_block("Leads Sujeito a Motor de Crédito", leads_sujeito_motor, df_no_motor, map_motor, 'motivo_da_decisao')
    render_block("Leads Com Propostas Disponíveis", propostas_disponiveis, df_nao_avancaram, map_nao_avancaram, 'status_da_proposta')
    render_block("Leads com Contrato Gerado", contrato_gerado, df_nao_validados, map_nao_validados, 'status_da_proposta')
    
    with st.expander(f"✅ Contratos Pagos: {contratos_pagos}"):
        st.success(f"Contrato Pago: {contratos_pagos}")
