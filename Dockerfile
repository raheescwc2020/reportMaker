# Use a base image with Python
FROM python:3.13-slim

# Install the necessary system dependencies for cairo
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    libgirepository1.0-dev \
    pkg-config \
    
# Set the working directory
WORKDIR /usr/src/app

# Copy the requirements file and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Set the command to run your application
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT:-8000}", "main:app"]