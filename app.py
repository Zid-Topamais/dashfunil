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

# Adicione isso para testar
if not df_base.empty:
    st.write("Contagem por mês encontrada:", df_base['Filtro_Mes'].value_counts())

# --- LÓGICA DE FILTROS ---

def reset_filtros():
    for key in ['digitador_unico', 'top15_multi', 'bloqueio']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

st.sidebar.header("Filtros de Visão")

# 1. Filtro de Mês
lista_meses = ["Todos"] + sorted(df_base['Filtro_Mes'].dropna().unique().tolist())
mes_sel = st.sidebar.selectbox("Selecione o Mês", lista_meses)

df_mes = df_base.copy()
if mes_sel != "Todos":
    df_mes = df_mes[df_mes['Filtro_Mes'] == mes_sel]

# 2. Top 15 Dinâmico (Ajustado para 15)
top_15_list = df_mes[df_mes['status_da_proposta'] == 'DISBURSED']['Digitado por'].value_counts().nlargest(15).index.tolist()

st.sidebar.divider()

# --- Lógica de Bloqueio ---
disable_unico = False
disable_top15 = False

if st.session_state.get('top15_multi'):
    disable_unico = True
elif st.session_state.get('digitador_unico') and st.session_state.digitador_unico != "Todos":
    disable_top15 = True

# Filtro Único
dig_sel = st.sidebar.selectbox(
    "Selecione o Digitador", 
    ["Todos"] + sorted(df_base['Digitado por'].unique().tolist()),
    key="digitador_unico",
    disabled=disable_unico
)

# Filtro Top 15 (Ajustado para 15)
top15_sel = st.sidebar.multiselect(
    "Digitadores Top 15 (Pagos)", 
    top_15_list,
    key="top15_multi",
    disabled=disable_top15
)

if st.sidebar.button("Limpar Filtros e Bloqueios"):
    reset_filtros()

# --- APLICAÇÃO DOS DADOS ---
df_sel = df_mes.copy()
if top15_sel:
    df_sel = df_sel[df_sel['Digitado por'].isin(top15_sel)]
elif dig_sel != "Todos":
    df_sel = df_sel[df_sel['Digitado por'] == dig_sel]

# --- MAPEAMENTOS ---
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
map_nao_avancaram = {'CREDIT_CHECK_COMPLETED': 'Proposta não Aceita', 'PRE_ACCEPTED': 'Proposta Ajustada', 'CONTRACT_GENERATION_FAILED': 'Erro no Contrato'}
map_nao_validados = {
    'SIGNATURE_FAILED': 'Contrato Recusado no AntiFraude',
    'CANCELED': 'Cancelado pelo Tomador Pré Desembolso',
    'EXPIRED': 'Contrato Expirado',
    'ANALYSIS_REPROVED': 'Analise Mesa Reprovada',
    'ERROR': 'Falha na averbação',
    'CANCELLED_BY_USER': 'Cancelado pelo Tomador Pós Desembolso'
}

# --- CÁLCULOS ---
def calc_metrics(df_s, df_m, keys, col):
    v_sel = len(df_s[df_s[col].isin(keys)])
    v_mes = len(df_m[df_m[col].isin(keys)])
    p = (v_sel / v_mes * 100) if v_mes > 0 else 0
    return v_sel, v_mes, p

n_sel, n_mes = len(df_sel), len(df_mes)
p_leads = (n_sel / n_mes * 100) if n_mes > 0 else 0

v_eng_s, v_eng_m, _ = calc_metrics(df_sel, df_mes, map_nao_engajados.keys(), 'status_da_proposta')
tok_s, tok_m = n_sel - v_eng_s, n_mes - v_eng_m
p_tok = (tok_s / tok_m * 100) if tok_m > 0 else 0

v_pre_s, v_pre_m, _ = calc_metrics(df_sel, df_mes, map_pre_motor.keys(), 'status_da_analise')
mot_s, mot_m = tok_s - v_pre_s, tok_m - v_pre_m
p_mot_cat = (mot_s / mot_m * 100) if mot_m > 0 else 0

v_mot_s, v_mot_m, _ = calc_metrics(df_sel, df_mes, map_motor.keys(), 'motivo_da_decisao')
dis_s, dis_m = mot_s - v_mot_s, mot_m - v_mot_m
p_dis = (dis_s / dis_m * 100) if dis_m > 0 else 0

v_nav_s, v_nav_m, _ = calc_metrics(df_sel, df_mes, map_nao_avancaram.keys(), 'status_da_proposta')
ger_s, ger_m = dis_s - v_nav_s, dis_m - v_nav_m
p_ger = (ger_s / ger_m * 100) if ger_m > 0 else 0

v_nva_s, v_nva_m, _ = calc_metrics(df_sel, df_mes, map_nao_validados.keys(), 'status_da_proposta')

pag_s = len(df_sel[df_sel['status_da_proposta'] == 'DISBURSED'])
pag_m = len(df_mes[df_mes['status_da_proposta'] == 'DISBURSED'])
p_pag = (pag_s / pag_m * 100) if pag_m > 0 else 0

# --- INTERFACE ---
st.title("📊 Funil Topa+ Analítico")
c1, c2 = st.columns([1, 1])

with c1:
    fig = go.Figure(go.Funnel(
        y=["Novos Leads", "Token Aprovado", "Sujeito a Motor", "Disp.", "Gerado", "Pagos"],
        x=[n_sel, tok_s, mot_s, dis_s, ger_s, pag_s],
        textinfo="value+percent initial"
    ))
    st.plotly_chart(fig, use_container_width=True)

with c2:
   def block_ui(label, val, p, df_s, df_m, mapping, col):
    with st.expander(f"📌 {label}: {val} ({p:.1f}%)"):
        if not df_s.empty:
            # 1. Mapeia os status originais para as descrições finais
            df_s_mapped = df_s[df_s[col].isin(mapping.keys())].copy()
            df_s_mapped['Descrição'] = df_s_mapped[col].map(mapping)
            
            df_m_mapped = df_m[df_m[col].isin(mapping.keys())].copy()
            df_m_mapped['Descrição'] = df_m_mapped[col].map(mapping)

            # 2. Agrupa por 'Descrição' para somar os status duplicados (como o CLT)
            counts_s = df_s_mapped.groupby('Descrição').size().reset_index(name='Qtd_Sel')
            counts_m = df_m_mapped.groupby('Descrição').size().reset_index(name='Total_Mes')
            
            # 3. Faz o merge final para exibição
            res = pd.merge(counts_s, counts_m, on='Descrição')
            res['%'] = (res['Qtd_Sel'] / res['Total_Mes'] * 100).map("{:.1f}%".format)
            
            st.table(res[['Descrição', 'Qtd_Sel', '%']])

    block_ui("Novos Leads", n_sel, p_leads, df_sel, df_mes, map_nao_engajados, 'status_da_proposta')
    block_ui("Leads com Token Aprovado", tok_s, p_tok, df_sel, df_mes, map_pre_motor, 'status_da_analise')
    block_ui("Leads Sujeito a Motor", mot_s, p_mot_cat, df_sel, df_mes, map_motor, 'motivo_da_decisao')
    block_ui("Propostas Disponíveis", dis_s, p_dis, df_sel, df_mes, map_nao_avancaram, 'status_da_proposta')
    block_ui("Contrato Gerado", ger_s, p_ger, df_sel, df_mes, map_nao_validados, 'status_da_proposta')
    with st.expander(f"✅ Contratos Pagos: {pag_s} ({p_pag:.1f}%)"):
        st.success(f"Representatividade: {p_pag:.1f}% ( {pag_s} de {pag_m} totais no mês)")
