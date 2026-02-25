import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. Configuração inicial da página
st.set_page_config(page_title="Dashboard Funil Topa+", layout="wide")

# 2. Função de Carga Robusta (Ajustada para suas abas e colunas)
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1-ttYZTqw_8JhU3zA1JAKYaece_iJ-CBrdeoTzNKMZ3I"
    url_dez = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Dez"
    url_jan = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados_Jan"
    
    try:
        # Carregando e unificando as bases
        df_dez = pd.read_csv(url_dez)
        df_jan = pd.read_csv(url_jan)
        df = pd.concat([df_dez, df_jan], ignore_index=True)
        df = df.dropna(how='all')

        # Tratamento da Data de Criação (Coluna D) como guia principal
        df['Data de Criação'] = pd.to_datetime(df['Data de Criação'], errors='coerce', dayfirst=True)
        
        # Mapeamento de meses para o filtro
        meses_pt = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 
                    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        df['Filtro_Mes'] = df['Data de Criação'].dt.month.map(meses_pt)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha: {e}")
        return pd.DataFrame()

# Inicialização da base
df_base = load_data()

# Se a base estiver vazia, interrompe a execução com aviso
if df_base.empty:
    st.warning("⚠️ Verifique se a planilha está compartilhada como 'Qualquer pessoa com o link' e se os nomes das abas estão corretos.")
    st.stop()

# --- SIDEBAR (FILTROS) ---
st.sidebar.header("Filtros de Visão")
lista_meses = ["Todos"] + sorted(df_base['Filtro_Mes'].dropna().unique().tolist())
mes_sel = st.sidebar.selectbox("Selecione o Mês", lista_meses)

opcoes_digitador = ["Todos"] + sorted(df_base['Digitado por'].dropna().unique().tolist())
dig_sel = st.sidebar.selectbox("Selecione o Digitador", opcoes_digitador)

# Aplicação dos Filtros no DataFrame
df = df_base.copy()
if mes_sel != "Todos": 
    df = df[df['Filtro_Mes'] == mes_sel]
if dig_sel != "Todos": 
    df = df[df['Digitado por'] == dig_sel]

# --- LÓGICA DE CÁLCULO DO FUNIL ---

# 1. Novos Leads (Total da base filtrada)
novos_leads = len(df)
df_nao_engajados = df[df['status_da_proposta'].isin(['CREATED', 'TOKEN_SENT'])]
total_nao_engajados = len(df_nao_engajados)

# 2. Leads com Token Aprovado (Anterior - Não Engajados)
leads_token_aprovado = novos_leads - total_nao_engajados
pre_motor_status = ['NO_AVAILABLE_MARGIN', 'CPF_EMPLOYER', 'SEM_DADOS_DATAPREV', 'NOT_AUTHORIZED_DATAPREV', 'FAILED_DATAPREV', 'CREDIT_ENGINE_ERROR']
df_pre_motor = df[df['status_da_analise'].isin(pre_motor_status)]
total_pre_motor = len(df_pre_motor)

# 3. Leads Sujeito a Motor (Anterior - Pré Motor)
leads_sujeito_motor = leads_token_aprovado - total_pre_motor

# Mapeamento do Motor (Coluna AD)
motor_map = {
    'Quantidade de Funcionarios': 'Porte Empresa - CNPJ',
    'Negar = Quantidade de Funcionarios entre 1 e 50': 'Porte Empresa - CNPJ',
    'Porte do empregador': 'Porte Empresa - CNPJ',
    'Negar = Tempo Fundacao da Empresa menor que 12 meses': 'Tempo Fundação - CNPJ',
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

# 4. Propostas Disponíveis (Anterior - No Motor)
propostas_disponiveis = leads_sujeito_motor - total_no_motor
df_nao_avancaram = df[df['status_da_proposta'].isin(['CREDIT_CHECK_COMPLETED', 'PRE_ACCEPTED', 'CONTRACT_GENERATION_FAILED'])]
total_nao_avancaram = len(df_nao_avancaram)

# 5. Contrato Gerado (Anterior - Não Avançaram)
contrato_gerado = propostas_disponiveis - total_nao_avancaram
nao_validados_status = ['SIGNATURE_FAILED', 'CANCELED', 'EXPIRED', 'ANALYSIS_REPROVED', 'ERROR', 'CANCELLED_BY_USER']
df_nao_validados = df[df['status_da_proposta'].isin(nao_validados_status)]
total_nao_validados = len(df_nao_validados)

# 6. Contratos Pagos
contratos_pagos = len(df[df['status_da_proposta'] == 'DISBURSED'])

# --- LAYOUT DASHBOARD (DIVISÃO 50/50) ---
st.title("📊 Dashboard Analítico Funil Topa+")
st.markdown(f"**Visão Selecionada:** {mes_sel} | **Digitador:** {dig_sel}")
st.divider()

col_esq, col_dir = st.columns([1, 1])

with col_esq:
    st.subheader("🎯 Funil de Conversão")
    fig = go.Figure(go.Funnel(
        y = ["Novos Leads", "Token Aprovado", "Sujeito a Motor", "Propostas Disp.", "Contrato Gerado", "Pagos"],
        x = [novos_leads, leads_token_aprovado, leads_sujeito_motor, propostas_disponiveis, contrato_gerado, contratos_pagos],
        textinfo = "value+percent initial",
        marker = {"color": ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728", "#9467bd", "#8c564b"]}
    ))
    fig.update_layout(height=600, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

with col_dir:
    st.subheader("📂 Detalhamento e Recusas")
    
    # Função para renderizar as tabelas dentro dos expanders
    def render_sub_table(df_sub, mapping, col_ref):
        if not df_sub.empty:
            res = df_sub[col_ref].value_counts().reset_index()
            res.columns = ['Status Técnico', 'Qtd']
            if mapping:
                res['Descrição Amigável'] = res['Status Técnico'].map(mapping)
                # Reorganiza para mostrar descrição primeiro se existir
                res = res[['Descrição Amigável', 'Qtd']]
            st.dataframe(res, hide_index=True, use_container_width=True)
            st.warning(f"**Soma da Subcategoria: {res['Qtd'].sum()}**")
        else:
            st.info("Nenhum dado encontrado para esta etapa.")

    # Drill Down das Categorias
    with st.expander(f"🔵 1. Novos Leads: {novos_leads}"):
        st.write("**Leads Não Engajados (Perda)**")
        render_sub_table(df_nao_engajados, {'CREATED':'Proposta Iniciada', 'TOKEN_SENT':'Token Enviado'}, 'status_da_proposta')

    with st.expander(f"🟢 2. Leads com Token Aprovado: {leads_token_aprovado}"):
        st.write("**Rejeitadas Pré Motor (Perda)**")
        pre_motor_labels = {
            'NO_AVAILABLE_MARGIN': 'Dataprev - Sem Margem',
            'CPF_EMPLOYER': 'Dataprev - Não É CLT',
            'SEM_DADOS_DATAPREV': 'Dataprev - Sem Dados',
            'NOT_AUTHORIZED_DATAPREV': 'Dataprev - Não Elegível',
            'FAILED_DATAPREV': 'Dataprev Fora',
            'CREDIT_ENGINE_ERROR': 'Erro Motor Bull'
        }
        render_sub_table(df_pre_motor, pre_motor_labels, 'status_da_analise')

    with st.expander(f"🟠 3. Leads Sujeito a Motor: {leads_sujeito_motor}"):
        st.write("**Rejeitadas No Motor (Perda)**")
        render_table_motor = df_no_motor['motivo_da_decisao'].value_counts().reset_index()
        render_table_motor.columns = ['Motivo Detalhado', 'Qtd']
        st.dataframe(render_table_motor, hide_index=True, use_container_width=True)
        st.warning(f"**Total Rejeição Motor: {total_no_motor}**")

    with st.expander(f"🟡 4. Propostas Disponíveis: {propostas_disponiveis}"):
        st.write("**Não Avançaram para Contrato (Perda)**")
        nao_avanc_labels = {'CREDIT_CHECK_COMPLETED':'Proposta não Aceita', 'PRE_ACCEPTED':'Proposta Ajustada', 'CONTRACT_GENERATION_FAILED':'Erro no Contrato'}
        render_sub_table(df_nao_avancaram, nao_avanc_labels, 'status_da_proposta')

    with st.expander(f"🟣 5. Contrato Gerado: {contrato_gerado}"):
        st.write("**Contratos Não Validados (Perda)**")
        nao_valid_labels = {
            'SIGNATURE_FAILED': 'Falha AntiFraude', 'CANCELED': 'Cancelado Tomador (Pré)', 
            'EXPIRED': 'Contrato Expirado', 'ANALYSIS_REPROVED': 'Mesa Reprovada', 
            'ERROR': 'Falha Averbação', 'CANCELLED_BY_USER': 'Cancelado Tomador (Pós)'
        }
        render_sub_table(df_nao_validados, nao_valid_labels, 'status_da_proposta')

    with st.expander(f"🏆 6. Contratos Pagos: {contratos_pagos}"):
        st.success(f"Finalizados com Sucesso: {contratos_pagos}")
