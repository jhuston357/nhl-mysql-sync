FROM python:3.12-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a directory for logs
RUN mkdir -p /app/logs

# Expose the web server port
EXPOSE 7443

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create an entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Run the web server
ENTRYPOINT ["/docker-entrypoint.sh"]