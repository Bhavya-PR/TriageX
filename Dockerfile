FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download HuggingFace models so container starts instantly
RUN python - <<'EOF'
from transformers import pipeline
pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment-latest")
EOF

COPY . .
