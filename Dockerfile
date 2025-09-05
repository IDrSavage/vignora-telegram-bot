# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's source code
COPY . .

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run the web server on container startup using Gunicorn for production
# --workers 1: Cloud Run is single-threaded per instance, so 1 worker is optimal.
# --threads 8: Use threads within the worker to handle concurrent I/O efficiently.
# --timeout 300: Increase timeout to 300 seconds to handle bot initialization.
# --preload: Preload the application for faster startup.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "300", "--preload", "telegram_bot:app"]