# Use the official Python image as a base
FROM python:3.12

# Set working directory in the container
WORKDIR /app

# Copy requirements file
COPY tasks/scraper/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the scraper code
COPY tasks/scraper/src src

# Command to run the application
CMD [ "python", "src/scraper.py" ]
