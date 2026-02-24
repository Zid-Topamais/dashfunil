import streamlit as st  # <--- ESSA LINHA É OBRIGATÓRIA NO TOPO
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go

# Configuração da página deve vir logo após os imports
st.set_page_config(page_title="Dashboard Topa+ Realtime", layout="wide")

# Agora sim você pode usar o st.connection e o st.cache_data
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def load_data():
    # URL corrigida para evitar o erro anterior de InvalidURL
    url = "https://docs.google.com/spreadsheets/d/1-ttYZTqw_8JhU3zA1JAKYaece_iJ-CBrdeoTzNKMZ3I/edit#gid=945417474"
    
    df_dez = conn.read(spreadsheet=url, worksheet="Dados brutos - Dez")
    df_jan = conn.read(spreadsheet=url, worksheet="Dados brutos - Jan")
    
    df = pd.concat([df_dez, df_jan], ignore_index=True)
    return df

# O restante do seu código segue abaixo...
