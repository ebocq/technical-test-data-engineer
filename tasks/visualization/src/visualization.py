import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from datetime import datetime


def fetch_data(table_name):
    # Connect to PostgreSQL database
    engine = create_engine(os.environ['DATABASE_URL'])
    
    # Query data from the table
    df = pd.read_sql_table(table_name, engine)
    
    return df

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

    return df_zones[df_zones_essentials_columns].merge(df_arretes[df_arretes_essentials_columns], how='inner', on='id_zone')

def df_at_date(df, date_to_consider):
    return df[(df['debut_validite_arrete'] <= date_to_consider) & (date_to_consider <= df['fin_validite_arrete'])]

def plot_nb_dep_per_alert(df, date_to_consider, cmap, norm):
    df_date = df_at_date(df, date_to_consider)

    df_max_alert_per_dep = df_date.sort_values('numero_niveau', ascending=False).drop_duplicates('code_departement', keep='first')
    df_nb_dep_per_alert = df_max_alert_per_dep.groupby(by=['numero_niveau', 'nom_niveau']).agg({'code_departement': 'count'}).rename(columns={'code_departement': 'nb_departements'}).reset_index()
    df_sorted = df_nb_dep_per_alert.sort_values('numero_niveau', ascending=False)

    st.title(f"Nombre de départements par niveau d'alerte au {date_to_consider}")
    fig, ax = plt.subplots()
    # red_palette = sns.light_palette("red", as_cmap=True)
    # sns.barplot(data=df_sorted, x='nom_niveau', y='nb_departements', palette='viridis', ax=ax)
    df_sorted.plot(kind='bar', x='nom_niveau', y='nb_departements', color=cmap(norm(df_sorted['numero_niveau'])), legend=False, ax=ax)

    plt.xticks(rotation=45)
    st.pyplot(fig)

def plot_data(df):

    df_sup = df[df['type_zone'] == 'SUP']

    df_sup['days_list'] = df_sup.apply(lambda row: list(pd.date_range(start=row['debut_validite_arrete'], end=row['fin_validite_arrete'], freq='D')), axis=1)

    # Explode the date ranges into separate rows
    df_days = df_sup.explode('days_list').rename(columns={'days_list': 'day'})

    # Reset the index
    df_days.reset_index(drop=True, inplace=True)

    df_superficie_grav = df_days.groupby(['day', 'nom_niveau', 'numero_niveau']).agg({'surface_zone': 'sum'}).reset_index()

    st.title('Surface Zone by Day and Nom Niveau')
    # Plot line chart for each nom_niveau
    for nom_niveau in df_superficie_grav['nom_niveau'].unique():
        st.subheader(f"Nom Niveau: {nom_niveau}")
        subset = df_superficie_grav[df_superficie_grav['nom_niveau'] == nom_niveau]
        st.line_chart(subset.set_index('day')['surface_zone'])
    
   
def main():
    df = prep_data()
    
    # Define the date range
    start_date = df['debut_validite_arrete'].min()
    end_date = df['fin_validite_arrete'].max() 

    # Display a date input widget
    selected_date = st.date_input("Select a date:", value=datetime.now(), min_value=start_date, max_value=end_date)

    cmap = plt.get_cmap('Reds')
    norm = plt.Normalize(0, 5)
    # Display data on Streamlit web app
    plot_nb_dep_per_alert(df, date_to_consider=selected_date, cmap=cmap, norm=norm)

    # st.title('Dashboard: Zones Data')
    # plot_data(df)

if __name__ == "__main__":
    main()
