# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose port 8004 for the core events API
EXPOSE 8004

# Expose port 8005 for the webhooks service
EXPOSE 8005

# Command to run the core events API
CMD ["python", "core/events/core_events.py"]