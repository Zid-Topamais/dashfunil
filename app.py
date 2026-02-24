@st.cache_data(ttl=600)
def load_data():
    # URL corrigida sem o #gid duplicado
    url = "https://docs.google.com/spreadsheets/d/1-ttYZTqw_8JhU3zA1JAKYaece_iJ-CBrdeoTzNKMZ3I/edit#gid=945417474"
    
    # Nomes novos das abas
    df_dez = conn.read(spreadsheet=url, worksheet="Dados_Dez")
    df_jan = conn.read(spreadsheet=url, worksheet="Dados_Jan")
    
    # Limpeza básica (remove linhas totalmente vazias que o Sheets às vezes gera)
    df_dez = df_dez.dropna(how='all')
    df_jan = df_jan.dropna(how='all')
    
    df = pd.concat([df_dez, df_jan], ignore_index=True)
    return df
