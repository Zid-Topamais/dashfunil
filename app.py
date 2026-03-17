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

        # Limpeza de strings
        for c in ['status_da_proposta', 'status_da_analise', 'motivo_da_decisao']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip()

        # FIX 1: Identificar coluna de valor pelo nome (não por índice fixo)
        # Tenta encontrar a coluna de valor pelo nome; fallback para índice 10
        colunas_valor = [c for c in df.columns if 'valor' in c.lower() or 'liberado' in c.lower() or 'aprovado' in c.lower()]
        col_valor_nome = colunas_valor[0] if colunas_valor else df.columns[10]

        def limpa_moeda(valor):
            v = str(valor).upper().replace('R$', '').replace(' ', '').strip()
            if not v or v == 'NAN': return 0.0
            if ',' not in v and '.' in v:
                try: return float(v)
                except: return 0.0
            v = v.replace('.', '').replace(',', '.')
            try: return float(v)
            except: return 0.0

        df[col_valor_nome] = df[col_valor_nome].apply(limpa_moeda)

        # Salva o nome da coluna de valor como atributo para uso posterior
        df.attrs['col_valor'] = col_valor_nome

        return df
    except Exception as e:
        st.error(f"Erro ao carregar base: {e}")
        return pd.DataFrame()


df_base = load_data()

# --- FILTROS LATERAIS ---
if df_base.empty:
    st.error("Não foi possível carregar os dados. Verifique a conexão com a planilha.")
    st.stop()

# FIX 2: col_valor definido a partir do nome salvo no load, não por índice
col_valor = df_base.attrs.get('col_valor', df_base.columns[10])

# Mapeamento dinâmico das colunas R (17) e S (18)
nome_col_r = df_base.columns[17]  # Empresa
nome_col_s = df_base.columns[18]  # Squad/Equipe


def reset_filtros():
    """Limpa o estado da sessão, cache de dados e recarrega a página"""
    chaves = ['digitador_unico', 'top15_multi', 'empresa_sel', 'squad_sel', 'mes_sel']
    for k in chaves:
        if k in st.session_state:
            del st.session_state[k]
    # FIX 3: Limpa o cache para forçar recarregamento dos dados da planilha
    load_data.clear()
    st.rerun()


# --- FILTROS LATERAIS (SIDEBAR) ---

st.sidebar.header("🎯 Configurações do Funil")

# 1. Filtro de Mês
lista_meses = ["Todos"] + sorted(df_base['Filtro_Mes'].unique().tolist())
mes_sel = st.sidebar.selectbox("Mês de Referência", lista_meses, key="mes_sel")

df_mes = df_base if mes_sel == "Todos" else df_base[df_base['Filtro_Mes'] == mes_sel]

# 2. Filtro de Empresa
lista_empresa = ["Todos"] + sorted(df_mes[nome_col_r].dropna().unique().tolist())
empresa_sel = st.sidebar.selectbox("Filtrar Empresa", lista_empresa, key="empresa_sel")

df_empresa = df_mes.copy()
if empresa_sel != "Todos":
    df_empresa = df_empresa[df_empresa[nome_col_r] == empresa_sel]

# 3. Filtro de Equipe
lista_equipes = ["Todos"] + sorted(df_empresa[nome_col_s].dropna().unique().tolist())
equipe_sel = st.sidebar.selectbox("Filtrar Equipe", lista_equipes, key="squad_sel")

df_equipe = df_empresa.copy()
if equipe_sel != "Todos":
    df_equipe = df_equipe[df_equipe[nome_col_s] == equipe_sel]

# 4. Top 15 Pagos
top_15_pagos = (
    df_equipe[df_equipe['status_da_proposta'] == 'DISBURSED']['Digitado por']
    .value_counts()
    .nlargest(15)
    .index.tolist()
)

st.sidebar.divider()

# 5. Filtros de Digitador (mutex entre si)
disable_unico = bool(st.session_state.get('top15_multi'))
disable_top15 = bool(st.session_state.get('digitador_unico') and st.session_state.digitador_unico != "Todos")

dig_sel = st.sidebar.selectbox(
    "Filtrar Digitador Único",
    ["Todos"] + sorted(df_equipe['Digitado por'].dropna().unique().tolist()),
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
df_sel = df_equipe.copy()

if st.session_state.get('top15_multi'):
    df_sel = df_sel[df_sel['Digitado por'].isin(st.session_state['top15_multi'])]
elif st.session_state.get('digitador_unico') and st.session_state['digitador_unico'] != "Todos":
    df_sel = df_sel[df_sel['Digitado por'] == st.session_state['digitador_unico']]


# --- DICIONÁRIOS DE MAPEAMENTO ---

map_nao_engajados = {
    'CREATED': 'Proposta Iniciada',
    'TOKEN_SENT': 'Token Enviado'
}

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


# 1. Novos Leads
n_leads_sel = len(df_sel)

# 2. Token Aprovado
v_nao_eng_sel = get_count(df_sel, map_nao_engajados, 'status_da_proposta')
token_aprov_sel = n_leads_sel - v_nao_eng_sel

# 3. Sujeito a Motor
v_rej_pre_sel = get_count(df_sel, map_pre_motor, 'status_da_analise')
sujeito_motor_sel = token_aprov_sel - v_rej_pre_sel

# 4. Propostas Disponíveis + VALOR
v_rej_motor_sel = get_count(df_sel, map_motor, 'motivo_da_decisao')
prop_disp_sel = sujeito_motor_sel - v_rej_motor_sel

# FIX 4: Máscara completa — exclui todas as etapas anteriores para não inflar o valor
mask_prop_disp = (
    ~df_sel['status_da_proposta'].isin(map_nao_engajados.keys()) &
    ~df_sel['status_da_analise'].isin(map_pre_motor.keys()) &
    ~df_sel['motivo_da_decisao'].isin(map_motor.keys())
)
df_prop_disp = df_sel[mask_prop_disp]
val_prop_disp = float(df_prop_disp[col_valor].sum())

# 5. Contrato Gerado + VALOR
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
            res_s = sub_s.groupby('Descrição').size().reset_index(name='Qtd Sel')
            res_m = sub_m.groupby('Descrição').size().reset_index(name='Total Mês')
            res = pd.merge(res_s, res_m, on='Descrição', how='left').fillna(0)
            res['Total Mês'] = res['Total Mês'].astype(int)
            res['%'] = (res['Qtd Sel'] / res['Total Mês'].replace(0, 1) * 100).map("{:.1f}%".format)
            st.table(res.sort_values(by='Qtd Sel', ascending=False))
        else:
            st.write("Sem subcategorias registradas.")


# --- RENDERIZAÇÃO ---

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
        textposition="inside",
        insidetextanchor="middle",
        insidetextfont=dict(color="white", size=14),
        marker=dict(color="royalblue")
    ))

    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=600,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

with col2:
    drill_down_table("Novos Leads", n_leads_sel, df_sel, df_mes, map_nao_engajados, 'status_da_proposta')
    drill_down_table("Leads com Token Aprovado", token_aprov_sel, df_sel, df_mes, map_pre_motor, 'status_da_analise')
    drill_down_table("Leads Sujeito a Motor de Crédito", sujeito_motor_sel, df_sel, df_mes, map_motor, 'motivo_da_decisao')
    drill_down_table("Leads Com Propostas Disponíveis", prop_disp_sel, df_sel, df_mes, map_nao_avancaram, 'status_da_proposta')
    drill_down_table("Leads com Contrato Gerado", contrato_ger_sel, df_sel, df_mes, map_nao_validados, 'status_da_proposta')

    st.info(f"💰 **Contratos Pagos: {contratos_pagos_sel}**")
