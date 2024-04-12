import os
import requests
import psycopg2

# Download file from URL
url = 'https://www.data.gouv.fr/fr/datasets/r/ac45ed59-7f4b-453a-9b3d-3124af470056'
# response = requests.get(url)
# new_data = response.text

# Connect to PostgreSQL
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Create table if not exists
cur.execute("""
    CREATE TABLE IF NOT EXISTS scraped_data (
        id SERIAL PRIMARY KEY,
        content TEXT
    );
""")

# Retrieve previous data from the table
cur.execute("""
    SELECT content FROM scraped_data ORDER BY id DESC LIMIT 1;
""")
result = cur.fetchone()

# If no previous data found or new data is different from previous data, update the table
# if not result or new_data != result[0]:
#     # Insert new data into the table
#     cur.execute("""
#         INSERT INTO scraped_data (content) VALUES (%s);
#     """, (new_data,))
#     print("Data updated.")
# else:
#     print("Data is up to date.")

conn.commit()
conn.close()