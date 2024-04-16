import os
from flask import Flask, jsonify
from sqlalchemy import create_engine
from .utils.utils import get_csv_file


app = Flask(__name__)

@app.route('/scrape', methods=['GET'])
def scrape_data():
    try:
        # Download file from URL
        URL_ZONES = 'https://www.data.gouv.fr/fr/datasets/r/ac45ed59-7f4b-453a-9b3d-3124af470056'
        df_zones = get_csv_file(URL_ZONES)

        URL_ARRETES = 'https://www.data.gouv.fr/fr/datasets/r/782aac32-29c8-4b66-b231-ab4c3005f574'
        df_arretes = get_csv_file(URL_ARRETES)
        
        # URL_DEPARTEMENTS = 'https://www.data.gouv.fr/fr/datasets/r/90b9341a-e1f7-4d75-a73c-bbc010c7feeb'
        # gdf_departements = get_departements(URL_DEPARTEMENTS)

        # Connect to PostgreSQL
        engine = create_engine(os.environ['DATABASE_URL'])

        # Create tables if not exists, replace otherwise
        df_zones.to_sql('zones', con=engine, if_exists='replace', index=False)
        df_arretes.to_sql('arretes', con=engine, if_exists='replace', index=False)
        
        # with engine.connect() as conn:
        #     command = text("""CREATE EXTENSION postgis;""")
        #     conn.execute(command)
            
            # command = text("""DROP TABLE IF EXISTS public.departements;
            #                     CREATE TABLE IF NOT EXISTS public.departements (
            #                     geometry geometry(Geometry, 4326),
            #                     code TEXT,
            #                     nom TEXT
            #                 );
            #                 """)
            # conn.execute(command)
        # gdf_departements.to_postgis('departements', engine, index=False)
        
        # Ensure GeoPandas can handle the 'geometry' column
        # gdf_departements['geometry'] = gdf_departements['geometry'].apply(lambda x: x.wkt if x is not None else None)

        # Store GeoPandas dataframe into PostgreSQL
        # gdf_departements[:10].to_postgis('departements', engine, if_exists='replace', index=False)

        return jsonify({"success": "Data scraped and stored in database with success"}), 200
    
    except Exception as e:
        # If an exception occurs during scraping, return an error message
        return jsonify({"error": "An error occurred during scraping: " + str(e)}), 500