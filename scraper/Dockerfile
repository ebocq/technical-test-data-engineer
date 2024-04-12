# Use the official Python image as a base
FROM python:3.12

# Set working directory in the container
WORKDIR /app

# Copy requirements file
COPY scraper/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the scraper code
COPY scraper/src/scraper.py .

# Command to run the application
CMD [ "python", "scraper.py" ]
