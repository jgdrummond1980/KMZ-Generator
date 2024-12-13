# Base image with Python
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    exiftool \
    libheif-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the Streamlit default port
EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.enableCORS=false", "--server.headless=true"]
