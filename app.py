import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Funil Topa+ [DEBUG]", layout="wide")

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

        df['Data de Criação'] = pd.to_datetime(df['Data de Criação'], errors='coerce', dayfirst=True)
        meses_pt = {1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho",
                    7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"}
        df['Filtro_Mes'] = df['Data de Criação'].dt.month.map(meses_pt).fillna(df['Origem'])

        for c in ['status_da_proposta', 'status_da_analise', 'motivo_da_decisao']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip()

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
        df.attrs['col_valor'] = col_valor_nome
        return df
    except Exception as e:
        st.error(f"Erro ao carregar base: {e}")
        return pd.DataFrame()


df_base = load_data()

if df_base.empty:
    st.error("Não foi possível carregar os dados.")
    st.stop()

col_valor = df_base.attrs.get('col_valor', df_base.columns[10])

# ============================================================
# PAINEL DE DEBUG — Mostra os valores reais das colunas-chave
# ============================================================
with st.expander("🔍 DEBUG — Inspecionar colunas-chave (remover em produção)", expanded=True):
    st.markdown("#### Colunas disponíveis no DataFrame")
    st.write(list(df_base.columns))

    st.markdown(f"#### Coluna de valor identificada: `{col_valor}`")

    st.markdown("#### Valores únicos em `status_da_proposta`")
    st.write(sorted(df_base['status_da_proposta'].dropna().unique().tolist()))

    st.markdown("#### Valores únicos em `status_da_analise`")
    st.write(sorted(df_base['status_da_analise'].dropna().unique().tolist()))

    st.markdown("#### Valores únicos em `motivo_da_decisao`")
    st.write(sorted(df_base['motivo_da_decisao'].dropna().unique().tolist()))

    st.markdown("#### Top 30 valores mais frequentes em `motivo_da_decisao`")
    st.dataframe(
        df_base['motivo_da_decisao']
        .value_counts()
        .head(30)
        .reset_index()
        .rename(columns={'index': 'motivo_da_decisao', 'motivo_da_decisao': 'count'})
    )

    st.markdown("#### Top 30 valores mais frequentes em `status_da_analise`")
    st.dataframe(
        df_base['status_da_analise']
        .value_counts()
        .head(30)
        .reset_index()
        .rename(columns={'index': 'status_da_analise', 'status_da_analise': 'count'})
    )
