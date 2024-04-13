import pandas as pd
import requests
from io import StringIO

def get_csv_file(url):
    """Get a csv file accessible from the url argument, and return a DataFrame with the data
    
    Parameters:
    url (string); the url where to get the file
    
    Returns:
    DataFrame: the data in the csv file"""
    
    response = requests.get(url)
    csv_data = response.text
    csv_file_like_object = StringIO(csv_data)
    df = pd.read_csv(csv_file_like_object)

    return df