# Start with an official Python base image
FROM python:3.13-slim

# Install system dependencies required for pycairo and ReportLab
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    pkg-config \
    # The following are also good to have for other common libraries
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff-dev \
    libwebp-dev \
    # Clean up APT cache to reduce image size
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Set the command to run your application
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT:-8000}", "main:app"]