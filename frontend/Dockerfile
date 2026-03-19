FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        unzip \
        curl \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --upgrade reflex

COPY . .

# Initialise Reflex (downloads Next.js components)
RUN reflex init

EXPOSE 3000 8001
