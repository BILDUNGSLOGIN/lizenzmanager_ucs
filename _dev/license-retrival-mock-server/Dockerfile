FROM python:3.10-slim-buster
WORKDIR /app
# Install requirements
COPY requirements.txt ./
RUN pip install -r requirements.txt
# Copy code
COPY src ./
# Start web server
CMD uvicorn main:app --host 0.0.0.0 --port 8080
