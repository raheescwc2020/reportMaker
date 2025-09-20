# Start with an official Python base image
# Using a specific, well-tested version for better stability
FROM python:3.12-slim

# Install system dependencies required for pycairo and other common libraries
# The `-y` flag is added to automatically approve installations
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
    # Clean up APT cache to reduce image size
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container at the working directory
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Set the command to run your application using the shell form for variable expansion.
# The ${PORT:-8000} syntax uses the PORT environment variable if available,
# otherwise, it defaults to 8000.
CMD gunicorn --bind 0.0.0.0:${PORT:-8000} main:app
