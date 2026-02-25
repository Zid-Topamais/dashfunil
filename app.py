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
        
        # Converte data e limpa textos
        df['Data de Criação'] = pd.to_datetime(df['Data de Criação'], errors='coerce', dayfirst=True)
        meses_pt = {1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho", 
                    7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"}
        df['Filtro_Mes'] = df['Data de Criação'].dt.month.map(meses_pt).fillna(df['Origem'])
        
        # Limpa espaços em branco que sabotam a contagem
        for c in ['status_da_proposta', 'status_da_analise', 'motivo_da_decisao']:
            df[c] = df[c].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame()

df_base = load_data()

# --- FILTROS ---
def reset():
    for k in ['digitador_unico', 'top15_multi']:
        if k in st.session_state: del st.session_state[k]
    st.rerun()

st.sidebar.header("Filtros")
mes_sel = st.sidebar.selectbox("Mês", ["Todos"] + sorted(df_base['Filtro_Mes'].unique().tolist()))
df_mes = df_base if mes_sel == "Todos" else df_base[df_base['Filtro_Mes'] == mes_sel]

top_15 = df_mes[df_mes['status_da_proposta'] == 'DISBURSED']['Digitado por'].value_counts().nlargest(15).index.tolist()
dig_sel = st.sidebar.selectbox("Digitador", ["Todos"] + sorted(df_base['Digitado por'].unique().tolist()), key="digitador_unico", disabled=bool(st.session_state.get('top15_multi')))
top_sel = st.sidebar.multiselect("Top 15 Pagos", top_15, key="top15_multi", disabled=bool(st.session_state.get('digitador_unico') and st.session_state.digitador_unico != "Todos"))

if st.sidebar.button("Limpar"): reset()

df_sel = df_mes.copy()
if top_sel: df_sel = df_sel[df_sel['Digitado por'].isin(top_sel)]
elif dig_sel != "Todos": df_sel = df_sel[df_sel['Digitado por'] == dig_sel]

# --- MAPEAMENTOS ---
map_pre = {
    'NO_AVAILABLE_MARGIN': 'Dataprev - Negado - Sem Margem',
    'CPF_EMPLOYER': 'Dataprev - Negado - Não É CLT',
    'SEM_DADOS_DATAPREV': 'Dataprev - Negado - Não É CLT',
    'NOT_AUTHORIZED_DATAPREV': 'Dataprev - Negado - Não É Elegível',
    'FAILED_DATAPREV': 'Dataprev - DataPrev Fora',
    'CREDIT_ENGINE_ERROR': 'Bull - Erro no Motor Bull'
}

map_mot = {
    'Quantidade de Funcionarios': 'Porte Empresa - CNPJ',
    'Negar = Quantidade de Funcionarios entre 1 e 50': 'Porte Empresa - CNPJ',
    'Porte do empregador': 'Port
