import os
import requests
import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, MetaData
from datetime import datetime
from matplotlib.patches import Patch

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


def prep_data(cmap, norm):
    """Prepare the data for the analysis

    Args:
        cmap: colormap
        norm (_type_): normalization function

    Returns:
        pandas.DataFrame: the data from 'zones' and 'arretes' files, merged
    """
    # Fetch data from database
    df_zones = fetch_data('zones')
    df_arretes = fetch_data('arretes')

    df_arretes.loc[:, 'debut_validite_arrete'] = df_arretes['debut_validite_arrete'].fillna('1900-01-01')
    df_arretes.loc[:, 'fin_validite_arrete'] = df_arretes['fin_validite_arrete'].str.replace('0023', '2023')
    df_arretes.loc[:, 'fin_validite_arrete'] = df_arretes['fin_validite_arrete'].fillna('2024-12-31')
    df_arretes.loc[:, 'debut_validite_arrete'] = pd.to_datetime(df_arretes['debut_validite_arrete']).dt.date
    df_arretes.loc[:, 'fin_validite_arrete'] = pd.to_datetime(df_arretes['fin_validite_arrete']).dt.date

    
    df_legend = df_arretes[['nom_niveau', 'numero_niveau']].value_counts().reset_index().drop('count', axis=1)
    df_legend.loc[:, 'color'] = df_legend.loc[:, 'numero_niveau'].map(lambda x: cmap(norm(x)))
    st.session_state.color_dict = df_legend.sort_values('numero_niveau').set_index('nom_niveau')['color'].to_dict()

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


def load_data(cmap, norm):
    """Load the data when the session starts
    Args:
        cmap: colormap
        norm (_type_): normalization function
    """
    if not tables_exist():
        response = requests.get(SCRAPER_URL)
        if response.status_code == 200:
            st.success("Données récupérées depuis le site")
        else:
            st.error("Erreur lors de la récupération des données depuis le site")
            
    st.session_state.df = prep_data(cmap, norm)
    st.session_state.initialized = True  # Set initialized flag to True
    
    # get departments
    URL_DEPARTEMENTS = 'https://www.data.gouv.fr/fr/datasets/r/90b9341a-e1f7-4d75-a73c-bbc010c7feeb'
    st.session_state.gdf_departements = get_departements(URL_DEPARTEMENTS)


def df_at_date(df, date_to_consider):
    return df[(df['debut_validite_arrete'] <= date_to_consider) & (date_to_consider <= df['fin_validite_arrete'])]

def plot_nb_dep_per_alert(df, date_to_consider, cmap, norm):
    df_date = df_at_date(df, date_to_consider)

    df_max_alert_per_dep = df_date.sort_values('numero_niveau', ascending=False).drop_duplicates('code_departement', keep='first')
    df_nb_dep_per_alert = df_max_alert_per_dep.groupby(by=['numero_niveau', 'nom_niveau']).agg({'code_departement': 'count'}).rename(columns={'code_departement': 'nb_departements'}).reset_index()
    df_sorted = df_nb_dep_per_alert.sort_values('numero_niveau', ascending=False)

    formatted_date = date_to_consider.strftime("%d/%m/%Y")
    st.title(f"1. Nombre de départements par niveau d'alerte au {formatted_date}")
    fig, ax = plt.subplots()
    df_sorted.plot(kind='bar', x='nom_niveau', y='nb_departements', color=cmap(norm(df_sorted['numero_niveau'])), legend=False, ax=ax)

    plt.xticks(rotation=45)
    st.pyplot(fig)
    
def plot_legend(ax):
    legend_elements = [Patch(facecolor=color, label=label) for label, color in st.session_state.color_dict.items()]
    legend = ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1), prop={'size': 15})

    for handle in legend.legendHandles:
        handle.set_height(8)
        handle.set_linewidth(3)

def plot_repart_restriction(df, gdf_departements, date_to_consider, cmap, norm, grouping='departement'):
    if grouping == 'departement':
        prefix = 'code_'
    else:
        prefix = 'id_'

    df_date = df_at_date(df, date_to_consider)
    df_max_alert_per_grouping = df_date.sort_values('numero_niveau', ascending=False).drop_duplicates(prefix + grouping, keep='first')
    df_sorted = df_max_alert_per_grouping.sort_values(['numero_niveau', 'nom_' + grouping], ascending=[False, True])

    formatted_date = date_to_consider.strftime("%d/%m/%Y")
    st.title(f"2. Niveau d'alerte par {grouping} au {formatted_date}")
    
    options = sorted(df_sorted.loc[:, 'nom_' + grouping].unique())

    selected_options = st.multiselect("Sélectionnez les départements pour lesquels voir le niveau d'alerte", options, default=options[:10])
    all_options = st.checkbox("Tout sélectionner")

    if all_options:
        selected_options = options
        
    if selected_options:
        fig, ax = plt.subplots(figsize=(15, 10))
        df_bar_plots = df_sorted[df_sorted['nom_' + grouping].isin(selected_options)]
        df_bar_plots.plot(kind='bar', x='nom_' + grouping, y='numero_niveau', color=cmap(norm(df_bar_plots['numero_niveau'])), legend=False, ax=ax)
        plot_legend(ax)

        ax.tick_params(axis='x', which='major', labelsize=12, rotation=45)
        st.pyplot(fig)
    
    gdf_alertes = gdf_departements.merge(df_max_alert_per_grouping, how='left', left_on='code', right_on='code_departement')
    gdf_alertes.loc[:, 'numero_niveau'] = gdf_alertes.loc[:, 'numero_niveau'].fillna(0)

    fig, ax = plt.subplots(figsize=(15, 10))
    gdf_alertes.plot(column='numero_niveau', cmap='Reds', ax=ax, edgecolor='black', legend=False)
    ax.set_axis_off()  # Turn off the axis
    ax.grid(False)  
    
    ax.set_title(f"Carte des niveaux d'alerte par département au {formatted_date}", fontsize=30)
    
    plot_legend(ax)
    
    st.pyplot(fig)
    


def plot_duration_evolution(df, nom_zone, cmap, norm):
    df_zone = df[df['nom_zone'] == nom_zone]    
    
    # # Plot horizontal bars for each period
    fig, ax = plt.subplots()
    ax.barh(y=df_zone['nom_niveau'], width=df_zone['Duration'], left=df_zone['debut_validite_arrete']
             , edgecolor='black', color=cmap(norm(df_zone['numero_niveau'])), height=0.2)


    plt.xlabel('Date')
    plt.ylabel("Type d'alerte")
    plt.title(f"Périodes d'application des arrêtés pour la zone {nom_zone}")
    plt.xticks(rotation=45)
    st.pyplot(fig)
    
def plot_surface_evolution(df):
    df_sup = df[df['type_zone'] == 'SUP']
    df_sup['days_list'] = df_sup.apply(lambda row: list(pd.date_range(start=row['debut_validite_arrete'], end=row['fin_validite_arrete'], freq='D')), axis=1)

    # Explode the date ranges into separate rows
    df_days = df_sup.explode('days_list').rename(columns={'days_list': 'day'})

    # Reset the index
    df_days.reset_index(drop=True, inplace=True)
    df_superficie_grav = df_days.groupby(['day', 'nom_niveau', 'numero_niveau']).agg({'surface_zone': 'sum'}).reset_index().sort_values('numero_niveau')

    st.title("4. Evolution de la superficie française concernée par des niveaux de gravité (pour les eaux superficielles uniquement)")
    sns.set_style("whitegrid")
    fig, ax = plt.subplots()
    sns.lineplot(data=df_superficie_grav, x='day', y='surface_zone', hue='nom_niveau', palette=st.session_state.color_dict, ax=ax)
    plt.xlabel('Date')
    plt.ylabel('Superficie (km²)')
    plt.xticks(rotation=45)
    st.pyplot(fig)
    
def plot_insight(text):
    # Define the CSS style for the box
    box_style = """
        background-color: #f0f0f0;
        color: black;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px grey;
    """
    st.markdown(f'<div style="{box_style}">{text}</div>', unsafe_allow_html=True)
    
    
    
def main():
    cmap = plt.get_cmap('Reds')
    norm = plt.Normalize(0, 5)
    
    st.title("Visualisation des données")

    if 'initialized' not in st.session_state or not st.session_state.initialized:
        load_data(cmap, norm)
    
    if st.button("Charger les dernières données depuis le site"):
        response = requests.get(SCRAPER_URL)
        if response.status_code == 200:
            st.session_state.df = prep_data(cmap, norm)
            st.success("Données mises à jour")
        else:
            st.error("Erreur lors de la mise à jour")
            st.write(response.json().get("error"))
            
    
    # Define the date range
    start_date = st.session_state.df['debut_validite_arrete'].min()
    end_date = st.session_state.df['fin_validite_arrete'].max() 

    # Display a date input widget
    selected_date = st.date_input("Sélectionnez une date à laquelle voir la situation des arrêtés :", value=datetime.now(), min_value=start_date, max_value=end_date)
    
    # 1st plot
    plot_nb_dep_per_alert(st.session_state.df, date_to_consider=selected_date, cmap=cmap, norm=norm)
    plot_insight("""On n'observe pas spécialement de tendance claire quant à la répartition des départements par niveau de crise.
                 On aura parfois une majorité de départements en crise, et parfois une majorité avec des alertes plus modérées.
                 Le dernier graphique nous apporte plus de visibilité.""")

    # 2nd plot
    plot_repart_restriction(st.session_state.df, st.session_state.gdf_departements, date_to_consider=selected_date, cmap=cmap, norm=norm, grouping='departement')
    plot_insight("""Ce sont les pays du sud qui sont généralement touchés, en particulier l'été, à cause des fortes chaleurs.""")
    
    # 3rd plot
    st.title('3. Durée des arrêtés au cours du temps par zone')
    selected_nom_zone = st.selectbox('Sélectionnez une zone:', sorted(st.session_state.df['nom_zone'].unique()), index=0)
    st.write('Chaque arrêté est délimité par les bordures noires')
    plot_duration_evolution(st.session_state.df, nom_zone=selected_nom_zone, cmap=cmap, norm=norm)
    
    plot_insight("""On voit que les arrêtés se succèdent, avec des durées différentes.
                 On a en général une succession d'arrêtés qui couvrent tout l'été, plutôt que des arrêtés isolés.""")
    
    # 4th plot
    plot_surface_evolution(st.session_state.df)
    plot_insight("""On constate, sans grande surprise, que les alertes les plus importantes sont déclarées en été.
                 On peut tout de même noter l'apparition de vigilances bien plus tôt dans l'année !""")

if __name__ == "__main__":
    main()
