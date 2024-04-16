import os
import requests
import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, text, MetaData
from datetime import datetime

SCRAPER_URL = "http://scraper:5001/scrape"

def fetch_data(table_name):
    # Connect to PostgreSQL database
    engine = create_engine(os.environ['DATABASE_URL'])
    
    # Query data from the table
    df = pd.read_sql_table(table_name, engine)

    return df

def get_departements(url):
    response = requests.get(url)
    geojson_data = response.json()
    return gpd.GeoDataFrame.from_features(geojson_data.get('features'))

def delete_table(table_name):
    sql_query = text(f"""DELETE FROM {table_name}""")

    engine = create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as connection:
        connection.execute(sql_query)
        connection.commit()

def prep_data():
    # Fetch data from database
    df_zones = fetch_data('zones')
    df_arretes = fetch_data('arretes')

    df_arretes.loc[:, 'debut_validite_arrete'] = df_arretes['debut_validite_arrete'].fillna('1900-01-01')
    df_arretes['fin_validite_arrete'] = df_arretes['fin_validite_arrete'].str.replace('0023', '2023')
    df_arretes.loc[:, 'fin_validite_arrete'] = df_arretes['fin_validite_arrete'].fillna('2024-12-31')
    df_arretes.loc[:, 'debut_validite_arrete'] = pd.to_datetime(df_arretes['debut_validite_arrete']).dt.date
    df_arretes.loc[:, 'fin_validite_arrete'] = pd.to_datetime(df_arretes['fin_validite_arrete']).dt.date

    df_zones_essentials_columns = ['id_zone', 'nom_zone', 'code_departement', 'nom_departement', 'surface_zone', 'type_zone']

    df_arretes_essentials_columns = ['id_zone', 'debut_validite_arrete', 'fin_validite_arrete', 'numero_niveau',
        'nom_niveau', 'statut_arrete']
    
    df =  df_zones[df_zones_essentials_columns].merge(df_arretes[df_arretes_essentials_columns], how='inner', on='id_zone')
    df['Duration'] = df['fin_validite_arrete'] - df['debut_validite_arrete'] + pd.Timedelta(days=1)
    
    return df

def tables_exist():
    engine = create_engine(os.environ['DATABASE_URL'])
    # Create a MetaData object
    metadata = MetaData()

    # Reflect the tables in the database
    metadata.reflect(bind=engine)

    # Check if the 'zones' table exists in the database
    return 'zones' in metadata.tables and 'arretes' in metadata.tables

# @st.cache(allow_output_mutation=True)
def load_data():
    if not tables_exist():
        response = requests.get(SCRAPER_URL)
        if response.status_code == 200:
            st.success("Données récupérées depuis le site")
        else:
            st.error("Erreur lors de la récupération des données depuis le site")
            
    st.session_state.df = prep_data()
    st.session_state.initialized = True  # Set initialized flag to True
    
    # get departments
    URL_DEPARTEMENTS = 'https://www.data.gouv.fr/fr/datasets/r/90b9341a-e1f7-4d75-a73c-bbc010c7feeb'
    st.session_state.gdf_departements = get_departements(URL_DEPARTEMENTS)
        
    st.write("Initialisation terminée")

def df_at_date(df, date_to_consider):
    return df[(df['debut_validite_arrete'] <= date_to_consider) & (date_to_consider <= df['fin_validite_arrete'])]

def plot_nb_dep_per_alert(df, date_to_consider, cmap, norm):
    df_date = df_at_date(df, date_to_consider)

    df_max_alert_per_dep = df_date.sort_values('numero_niveau', ascending=False).drop_duplicates('code_departement', keep='first')
    df_nb_dep_per_alert = df_max_alert_per_dep.groupby(by=['numero_niveau', 'nom_niveau']).agg({'code_departement': 'count'}).rename(columns={'code_departement': 'nb_departements'}).reset_index()
    df_sorted = df_nb_dep_per_alert.sort_values('numero_niveau', ascending=False)

    st.title(f"1. Nombre de départements par niveau d'alerte au {date_to_consider}")
    fig, ax = plt.subplots()
    df_sorted.plot(kind='bar', x='nom_niveau', y='nb_departements', color=cmap(norm(df_sorted['numero_niveau'])), legend=False, ax=ax)

    plt.xticks(rotation=45)
    st.pyplot(fig)

def plot_repart_restriction(df, date_to_consider, cmap, norm, grouping='departement'):
    if grouping == 'departement':
        prefix = 'code_'
    else:
        prefix = 'id_'

    df_date = df_at_date(df, date_to_consider)
    df_max_alert_per_grouping = df_date.sort_values('numero_niveau', ascending=False).drop_duplicates(prefix + grouping, keep='first')
    df_sorted = df_max_alert_per_grouping.sort_values('nom_' + grouping, ascending=True)

    st.title(f"2. Niveau d'alerte par {grouping} au {date_to_consider}")
    fig, ax = plt.subplots()
    df_sorted.plot(kind='bar', x='nom_' + grouping, y='numero_niveau', color=cmap(norm(df_sorted['numero_niveau'])), legend=False, ax=ax)

    plt.xticks(rotation=45)
    st.pyplot(fig)

def plot_duration_evolution(df, nom_zone, cmap, norm):
    df_zone = df[df['nom_zone'] == nom_zone]    
    # st.bar_chart(df_zone.set_index('nom_niveau')[['debut_validite_arrete', 'Duration']])
    
    # # Plot horizontal bars for each period
    fig, ax = plt.subplots()
    ax.barh(y=df_zone['nom_niveau'], width=df_zone['Duration'], left=df_zone['debut_validite_arrete']
             , edgecolor='black', color=cmap(norm(df_zone['numero_niveau'])), height=0.2)

    # for bar in bars:
    #     width = bar.get_width()
    #     ax.text(width, bar.get_y() + bar.get_height()/2, f'{width}', va='center', ha='left')
    plt.xlabel('Date')
    plt.ylabel(f"Type d'alerte")
    plt.title("Périodes d'application des arrêtés")
    plt.xticks(rotation=45)
    st.pyplot(fig)
    
def plot_surface_evolution(df):
    df_sup = df[df['type_zone'] == 'SUP']
    df_sup['days_list'] = df_sup.apply(lambda row: list(pd.date_range(start=row['debut_validite_arrete'], end=row['fin_validite_arrete'], freq='D')), axis=1)

    # Explode the date ranges into separate rows
    df_days = df_sup.explode('days_list').rename(columns={'days_list': 'day'})

    # Reset the index
    df_days.reset_index(drop=True, inplace=True)
    df_superficie_grav = df_days.groupby(['day', 'nom_niveau', 'numero_niveau']).agg({'surface_zone': 'sum'}).reset_index()

    st.title("4. Evolution de la superficie française concernée par des niveaux de gravité (pour les eaux superficielles uniquement)")
    sns.set_style("whitegrid")
    fig, ax = plt.subplots()
    sns.lineplot(data=df_superficie_grav, x='day', y='surface_zone', hue='nom_niveau', ax=ax) #, marker='o')
    plt.xlabel('Date')
    plt.ylabel('Superficie')
    plt.xticks(rotation=45)
    st.pyplot(fig)
    
def main():
    st.title("Visualisation des données")

    if 'initialized' not in st.session_state or not st.session_state.initialized:
        load_data()
        
    fig, ax = plt.subplots()
    st.session_state.gdf_departements.plot(ax=ax)
    st.pyplot(fig)
    
    # delete_button = st.button("Effacer les données")
    # if delete_button:
    #     try:
    #         delete_table('zones')
    #         delete_table('arretes')
    #         st.success('Données effacées')
    #         st.session_state.df = prep_data()
    #     except Exception as e:
    #         st.error("Erreur lors de l'effacement : " + str(e))
    
    
    if st.button("Charger les dernières données depuis le site"):
        response = requests.get(SCRAPER_URL)
        if response.status_code == 200:
            st.session_state.df = prep_data()
            st.success("Données mises à jour")
        else:
            st.error("Erreur lors de la mise à jour")
            st.write(response.json().get("error"))

    
    # Define the date range
    start_date = st.session_state.df['debut_validite_arrete'].min()
    end_date = st.session_state.df['fin_validite_arrete'].max() 

    # Display a date input widget
    selected_date = st.date_input("Select a date:", value=datetime.now(), min_value=start_date, max_value=end_date)

    cmap = plt.get_cmap('Reds')
    norm = plt.Normalize(0, 5)
    
    # Display data on Streamlit web app
    
    # 1st plot
    plot_nb_dep_per_alert(st.session_state.df, date_to_consider=selected_date, cmap=cmap, norm=norm)

    # 2nd plot
    plot_repart_restriction(st.session_state.df, date_to_consider=selected_date, cmap=cmap, norm=norm, grouping='departement')

    # 3rd plot
    st.title('3. Durée des arrêtés au cours du temps')
    selected_nom_zone = st.selectbox('Sélectionnez une zone:', sorted(st.session_state.df['nom_zone'].unique()), index=0)
    # selected_noms_zones = st.multiselect('Select nom_zone:', sorted(st.session_state.df['nom_zone'].unique()))
    plot_duration_evolution(st.session_state.df, nom_zone=selected_nom_zone, cmap=cmap, norm=norm)
    
    # 4th plot
    plot_surface_evolution(st.session_state.df)

if __name__ == "__main__":
    main()
