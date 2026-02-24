import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go

# A configuração da página deve ser um dos primeiros comandos st
st.set_page_config(page_title="Dashboard Topa+ Realtime", layout="wide")

# Inicializa a conexão
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def load_data():
    # URL limpa e sem espaços
    url = "https://docs.google.com/spreadsheets/d/1-ttYZTqw_8JhU3zA1JAKYaece_iJ-CBrdeoTzNKMZ3I/edit#gid=945417474"
    
    # Lendo as abas com os nomes novos (sem espaços)
    df_dez = conn.read(spreadsheet=url, worksheet="Dados_Dez")
    df_jan = conn.read(spreadsheet=url, worksheet="Dados_Jan")
    
    # Concatenando
    df = pd.concat([df_dez, df_jan], ignore_index=True)
    return df

# Chama a função de carga
try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

# --- Restante do seu código de filtros e gráficos abaixo ---
st.title("📊 Dashboard Topa+ Realtime")
st.write(df.head()) # Teste para ver se os dados aparecem
