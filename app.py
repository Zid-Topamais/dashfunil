import streamlit as st
import pandas as pd
import plotly.graph_objects as go

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
        
        # Limpeza de strings para evitar erros de contagem
        for c in ['status_da_proposta', 'status_da_analise', 'motivo_da_decisao']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip()
        
        col_valor = df.columns[10] # Coluna K
        df[col_valor] = pd.to_numeric(df[col_valor].astype(str).str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar base: {e}")
        return pd.DataFrame()

df_base = load_data()

# --- FILTROS LATERAIS (SIDEBAR) ---

def reset_filtros():
    """Limpa o estado da sessão e recarrega a página"""
    chaves = ['digitador_unico', 'top15_multi', 'empresa_sel', 'squad_sel', 'mes_sel']
    for k in chaves:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

st.sidebar.header("🎯 Configurações do Funil")

# 1. Filtro de Mês (Base para todos os outros)
lista_meses = ["Todos"] + sorted(df_base['Filtro_Mes'].unique().tolist())
mes_sel = st.sidebar.selectbox("Mês de Referência", lista_meses, key="mes_sel")

# Aplica filtro de mês inicial
df_mes = df_base if mes_sel == "Todos" else df_base[df_base['Filtro_Mes'] == mes_sel]

# Mapeamento dinâmico das colunas R (17) e S (18)
# Usamos o índice para garantir que funcione mesmo se o nome do cabeçalho mudar
nome_col_r = df_base.columns[17] # Empresa
nome_col_s = df_base.columns[18] # Squad/Equipe

# 2. Filtro de Empresa (Coluna R)
lista_empresa = ["Todos"] + sorted(df_mes[nome_col_r].dropna().unique().tolist())
empresa_sel = st.sidebar.selectbox("Filtrar Empresa", lista_empresa, key="empresa_sel")

df_empresa = df_mes.copy()
if empresa_sel != "Todos":
    df_empresa = df_empresa[df_empresa[nome_col_r] == empresa_sel]

# 3. Filtro de Equipe (Coluna S - Squad)
# Nota: Só mostra as equipes da empresa selecionada
lista_equipes = ["Todos"] + sorted(df_empresa[nome_col_s].dropna().unique().tolist())
equipe_sel = st.sidebar.selectbox("Filtrar Equipe", lista_equipes, key="squad_sel")

df_equipe = df_empresa.copy()
if equipe_sel != "Todos":
    df_equipe = df_equipe[df_equipe[nome_col_s] == equipe_sel]

# 4. Top 15 Pagos (Contextualizado pelo Mês, Empresa e Equipe)
top_15_pagos = df_equipe[df_equipe['status_da_proposta'] == 'DISBURSED']['Digitado por'].value_counts().nlargest(15).index.tolist()

st.sidebar.divider()

# 5. Filtros de Digitador
# Regra: Se usar o Top 15, bloqueia o Unitário. Se usar o Unitário, bloqueia o Top 15.
disable_unico = bool(st.session_state.get('top15_multi'))
disable_top15 = bool(st.session_state.get('digitador_unico') and st.session_state.digitador_unico != "Todos")

dig_sel = st.sidebar.selectbox(
    "Filtrar Digitador Único", 
    ["Todos"] + sorted(df_equipe['Digitado por'].unique().tolist()), 
    key="digitador_unico", 
    disabled=disable_unico
)

top_sel = st.sidebar.multiselect(
    "Filtrar por Top 15 Pagos", 
    top_15_pagos, 
    key="top15_multi", 
    disabled=disable_top15
)

if st.sidebar.button("🧹 Limpar Todos os Filtros"):
    reset_filtros()

# --- APLICAÇÃO FINAL DA SELEÇÃO ---
# Esta variável df_sel é a que você usará para todos os cálculos do Funil (Lado Esquerdo)
df_sel = df_equipe.copy()

if top_sel: 
    df_sel = df_sel[df_sel['Digitado por'].isin(top_sel)]
elif dig_sel != "Todos": 
    df_sel = df_sel[df_sel['Digitado por'] == dig_sel]

# O df_mes continua sendo usado como comparativo (Lado Direito) para as porcentagens totais

# --- DICIONÁRIOS DE MAPEAMENTO (DRILL-DOWN) ---

map_nao_engajados = {'CREATED': 'Proposta Iniciada', 'TOKEN_SENT': 'Token Enviado'}

map_pre_motor = {
    'NO_AVAILABLE_MARGIN': 'Dataprev - Negado - Sem Margem',
    'CPF_EMPLOYER': 'Dataprev - Negado - Não É CLT',
    'SEM_DADOS_DATAPREV': 'Dataprev - Negado - Não É CLT',
    'NOT_AUTHORIZED_DATAPREV': 'Dataprev - Negado - Não É Elegível',
    'FAILED_DATAPREV': 'Dataprev - DataPrev Fora',
    'CREDIT_ENGINE_ERROR': 'Bull - Erro no Motor Bull'
}

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

map_nao_avancaram = {
    'CREDIT_CHECK_COMPLETED': 'Proposta não Aceita',
    'PRE_ACCEPTED': 'Proposta Ajustada',
    'CONTRACT_GENERATION_FAILED': 'Erro no Contrato'
}

map_nao_validados = {
    'SIGNATURE_FAILED': 'Contrato Recusado no AntiFraude',
    'CANCELED': 'Cancelado pelo Tomador Pré Desembolso',
    'EXPIRED': 'Contrato Expirado',
    'ANALYSIS_REPROVED': 'Analise Mesa Reprovada',
    'ERROR': 'Falha na averbação',
    'CANCELLED_BY_USER': 'Cancelado pelo Tomador Pós Desembolso'
}

# --- LÓGICA DE CÁLCULO DO FUNIL ---

def get_count(df, mapping, col):
    """Conta registros baseados nos mapeamentos de status"""
    return len(df[df[col].isin(mapping.keys())])

def format_br(valor):
    """Formata número para o padrão brasileiro R$ 1.234,56"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Coluna K - Valor Liberado (Índice 10)
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

# Filtrando o DataFrame para somar valores de quem chegou nesta etapa
df_prop_disp = df_sel[~df_sel['status_da_proposta'].isin(map_nao_engajados.keys()) & 
                      ~df_sel['status_da_analise'].isin(map_pre_motor.keys()) & 
                      ~df_sel['motivo_da_decisao'].isin(map_motor.keys())]
val_prop_disp = float(df_prop_disp[col_valor].sum())

# 5. Leads com Contrato Gerado + VALOR
df_contrato_ger = df_prop_disp[~df_prop_disp['status_da_proposta'].isin(map_nao_avancaram.keys())]
contrato_ger_sel = len(df_contrato_ger)
val_contrato_ger = float(df_contrato_ger[col_valor].sum())

# 6. Contratos Pagos + VALOR
df_pagos = df_sel[df_sel['status_da_proposta'] == 'DISBURSED']
contratos_pagos_sel = len(df_pagos)
val_pagos = float(df_pagos[col_valor].sum())

# --- FUNÇÃO DE EXIBIÇÃO DRILL-DOWN ---

def drill_down_table(title, total_cat, df_s, df_m, mapping, col):
    with st.expander(f"📌 {title}: {total_cat}"):
        sub_s = df_s[df_s[col].isin(mapping.keys())].copy()
        sub_m = df_m[df_m[col].isin(mapping.keys())].copy()
        if not sub_s.empty:
            sub_s['Descrição'] = sub_s[col].map(mapping)
            sub_m['Descrição'] = sub_m[col].map(mapping)
            # Consolidação (Agrupa nomes iguais e soma)
            res_s = sub_s.groupby('Descrição').size().reset_index(name='Qtd Sel')
            res_m = sub_m.groupby('Descrição').size().reset_index(name='Total Mês')
            res = pd.merge(res_s, res_m, on='Descrição')
            res['%'] = (res['Qtd Sel'] / res['Total Mês'] * 100).map("{:.1f}%".format)
            st.table(res.sort_values(by='Qtd Sel', ascending=False))
        else:
            st.write("Sem subcategorias registradas.")

# --- RENDERIZAÇÃO ---

st.title("📊 Dashboard Funil Analítico Topa+")

col1, col2 = st.columns([1.2, 1])

Python
with col1:
    # Rótulos que combinam Quantidade e Valor R$
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
        textinfo="text+percent initial"
    ))
    
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    drill_down_table("Novos Leads", n_leads_sel, df_sel, df_mes, map_nao_engajados, 'status_da_proposta')
    drill_down_table("Leads com Token Aprovado", token_aprov_sel, df_sel, df_mes, map_pre_motor, 'status_da_analise')
    drill_down_table("Leads Sujeito a Motor de Crédito", sujeito_motor_sel, df_sel, df_mes, map_motor, 'motivo_da_decisao')
    drill_down_table("Leads Com Propostas Disponíveis", prop_disp_sel, df_sel, df_mes, map_nao_avancaram, 'status_da_proposta')
    drill_down_table("Leads com Contrato Gerado", contrato_ger_sel, df_sel, df_mes, map_nao_validados, 'status_da_proposta')
    
    st.info(f"💰 **Contratos Pagos: {contratos_pagos_sel}**")
