import os
from sqlalchemy import create_engine
from utils.utils import get_csv_file

# Download file from URL
URL_ZONES = 'https://www.data.gouv.fr/fr/datasets/r/ac45ed59-7f4b-453a-9b3d-3124af470056'
df_zones = get_csv_file(URL_ZONES)

URL_ARRETES = 'https://www.data.gouv.fr/fr/datasets/r/782aac32-29c8-4b66-b231-ab4c3005f574'
df_arretes = get_csv_file(URL_ARRETES)

# Connect to PostgreSQL
engine = create_engine(os.environ['DATABASE_URL'])

# Create tables if not exists
df_zones.to_sql('zones', con=engine, if_exists='replace', index=False)
df_arretes.to_sql('arretes', con=engine, if_exists='replace', index=False)

engine.close()