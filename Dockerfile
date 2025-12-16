FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create storage directories
RUN mkdir -p storage/actions storage/learning storage/chromadb

# Expose port
EXPOSE 8080

# Streamlit config
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true

# Run
CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8080", "--server.address=0.0.0.0"]
