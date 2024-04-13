import streamlit as st
import os
import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt


def fetch_data(table_name):
    # Connect to PostgreSQL database
    engine = create_engine(os.environ['DATABASE_URL'])
    
    # Query data from the table
    df = pd.read_sql_table(table_name, engine)
    
    return df

def plot_data(df):
    # Plotting the first 5 rows
    st.write("First 5 rows of the 'zones' table:")
    st.write(df[:5])
    
    # df[:10].plot(kind='bar', x='nom_departement', y='surface_departement', color='skyblue')
    # Create a bar plot
    # st.bar_chart(df[:5].set_index('nom_departement'))

def main():
    # Fetch data from database
    df = fetch_data('zones')
    
    # Display data on Streamlit web app
    st.title('Dashboard: Zones Data')
    plot_data(df)

if __name__ == "__main__":
    main()
