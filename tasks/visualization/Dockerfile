# Use the official Python image as a base
FROM python:3.12

# Set working directory in the container
WORKDIR /app

# Copy requirements file
COPY tasks/visualization/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the visualization code
COPY tasks/visualization/src src

# Command to run the application
CMD ["streamlit", "run", "src/visualization.py"]
