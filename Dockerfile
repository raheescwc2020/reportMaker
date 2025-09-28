# Start with an official Python base image
# Using a specific tag to ensure cache is cleared for dependency installation
FROM python:3.12.3-slim 

# Install system dependencies required for reportlab, common image libraries, and MySQL connection
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    pkg-config \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff-dev \
    libwebp-dev \
    # MySQL client libraries are often needed for pymysql to work robustly
    default-libmysqlclient-dev \
    # Clean up APT cache to reduce image size
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies first
# This will execute fully and install Flask-SQLAlchemy due to the cache break above
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code (app.py, templates, static)
COPY . .

# Command to run your application using gunicorn.
# It binds to 0.0.0.0 and uses the $PORT environment variable provided by Railway (defaulting to 8000).
CMD gunicorn --bind 0.0.0.0:${PORT:-8000} app:app