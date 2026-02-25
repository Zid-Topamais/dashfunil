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

# --- LÓGICA DE FILTROS ---
st.sidebar.header("Filtros de Visão")

# Mês é a base de tudo
lista_meses = ["Todos"] + sorted(df_base['Filtro_Mes'].dropna().unique().tolist())
mes_sel = st.sidebar.selectbox("Selecione o Mês", lista_meses)

df_mes = df_base.copy()
if mes_sel != "Todos":
    df_mes = df_mes[df_mes['Filtro_Mes'] == mes_sel]

# Cálculo do Top 10 para o Sidebar
top_10_list = df_mes[df_mes['status_da_proposta'] == 'DISBURSED']['Digitado por'].value_counts().nlargest(10).index.tolist()

# Bloqueio de Filtros
if 'last_filter' not in st.session_state: st.session_state.last_filter = None

dig_sel = st.sidebar.selectbox("Selecione o Digitador", ["Todos"] + sorted(df_base['Digitado por'].unique().tolist()), 
                               disabled=(st.session_state.last_filter == "top10"))
top10_sel = st.sidebar.multiselect("Digitadores Top 10 (Pagos)", top_10_list, 
                                   disabled=(st.session_state.last_filter == "unico" and dig_sel != "Todos"))

if dig_sel != "Todos": st.session_state.last_filter = "unico"
elif top10_sel: st.session_state.last_filter = "top10"
else: st.session_state.last_filter = None

if st.sidebar.button("Limpar Filtros"):
    st.session_state.last_filter = None
    st.rerun()

# Aplicação da seleção
df_sel = df_mes.copy()
if top10_sel: df_sel = df_sel[df_sel['Digitado por'].isin(top10_sel)]
elif dig_sel != "Todos": df_sel = df_sel[df_sel['Digitado por'] == dig_sel]

# --- DICIONÁRIOS DE MAPEAMENTO (EXATAMENTE COMO VOCÊ PASSOU) ---
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

# --- PROCESSAMENTO DO FUNIL (Soma e % ) ---
def calc_etapa(df_current, df_ref_mes, keys, col):
    sel = len(df_current[df_current[col].isin(keys)])
    total_mes = len(df_ref_mes[df_ref_mes[col].isin(keys)])
    perc = (sel / total_mes * 100) if total_mes > 0 else 0
    return sel, total_mes, perc

# 1. Novos Leads
n_leads_sel = len(df_sel)
n_leads_mes = len(df_mes)
perc_leads = (n_leads_sel / n_leads_mes * 100) if n_leads_mes > 0 else 0

# Sub: Não Engajados
v_eng_sel, v_eng_mes, p_eng = calc_etapa(df_sel, df_mes, map_nao_engajados.keys(), 'status_da_proposta')

# 2. Token Aprovado
token_sel = n_leads_sel - v_eng_sel
token_mes = n_leads_mes - v_eng_mes
perc_token = (token_sel / token_mes * 100) if token_mes > 0 else 0

# Sub: Rejeitadas Pré Motor
v_pre_sel, v_pre_mes, p_pre = calc_etapa(df_sel, df_mes, map_pre_motor.keys(), 'status_da_analise')

# 3. Sujeito a Motor
motor_sel = token_sel - v_pre_sel
motor_mes = token_mes - v_pre_mes
perc_motor_cat = (motor_sel / motor_mes * 100) if motor_mes > 0 else 0

# Sub: Rejeitadas No Motor
v_mot_sel, v_mot_mes, p_mot = calc_etapa(df_sel, df_mes, map_motor.keys(), 'motivo_da_decisao')

# 4. Propostas Disponíveis
disp_sel = motor_sel - v_mot_sel
disp_mes = motor_mes - v_mot_mes
perc_disp = (disp_sel / disp_mes * 100) if disp_mes > 0 else 0

# Sub: Não Avançaram
v_nav_sel, v_nav_mes, p_nav = calc_etapa(df_sel, df_mes, map_nao_avancaram.keys(), 'status_da_proposta')

# 5. Contrato Gerado
ger_sel = disp_sel - v_nav_sel
ger_mes = disp_mes - v_nav_mes
perc_ger = (ger_sel / ger_mes * 100) if ger_mes > 0 else 0

# Sub: Não Validados
v_nva_sel, v_nva_mes, p_nva = calc_etapa(df_sel, df_mes, map_nao_validados.keys(), 'status_da_proposta')

# 6. Pagos
pag_sel = len(df_sel[df_sel['status_da_proposta'] == 'DISBURSED'])
pag_mes = len(df_mes[df_mes['status_da_proposta'] == 'DISBURSED'])
perc_pag = (pag_sel / pag_mes * 100) if pag_mes > 0 else 0

# --- INTERFACE ---
st.title("📊 Funil Topa+ Analítico")
col1, col2 = st.columns([1, 1])

with col1:
    fig = go.Figure(go.Funnel(
        y=["Novos Leads", "Token Aprovado", "Sujeito a Motor", "Disp.", "Gerado", "Pagos"],
        x=[n_leads_sel, token_sel, motor_sel, disp_sel, ger_sel, pag_sel],
        textinfo="value+percent initial"
    ))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    def draw_expander(label, val_sel, p_cat, df_s, df_m, mapping, col):
        with st.expander(f"📌 {label}: {val_sel} ({p_cat:.1f}%)"):
            if not df_s.empty:
                counts_s = df_s[df_s[col].isin(mapping.keys())][col].value_counts().reset_index()
                counts_m = df_m[df_m[col].isin(mapping.keys())][col].value_counts().reset_index()
                counts_s.columns = ['ID', 'Qtd_Sel']
                counts_m.columns = ['ID', 'Total_Mes']
                df_res = pd.merge(counts_s, counts_m, on='ID')
                df_res['Descrição'] = df_res['ID'].map(mapping)
                df_res['%'] = (df_res['Qtd_Sel'] / df_res['Total_Mes'] * 100).map("{:.1f}%".format)
                st.table(df_res[['Descrição', 'Qtd_Sel', '%']])
            else: st.info("Sem dados.")

    draw_expander("Novos Leads", n_leads_sel, perc_leads, df_sel, df_mes, map_nao_engajados, 'status_da_proposta')
    draw_expander("Leads com Token Aprovado", token_sel, perc_token, df_sel, df_mes, map_pre_motor, 'status_da_analise')
    draw_expander("Leads Sujeito a Motor", motor_sel, perc_motor_cat, df_sel, df_mes, map_motor, 'motivo_da_decisao')
    draw_expander("Propostas Disponíveis", disp_sel, perc_disp, df_sel, df_mes, map_nao_avancaram, 'status_da_proposta')
    draw_expander("Contrato Gerado", ger_sel, perc_ger, df_sel, df_mes, map_nao_validados, 'status_da_proposta')
    with st.expander(f"✅ Contratos Pagos: {pag_sel} ({perc_pag:.1f}%)"):
        st.success(f"Pago: {pag_sel} de {pag_mes} totais.")
