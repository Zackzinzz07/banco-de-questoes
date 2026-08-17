FROM python:3.12-slim
WORKDIR /app
# reportlab<4.0 has no prebuilt wheel for Python 3.12 and compiles its C
# extensions from source, which needs a compiler + FreeType headers.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ENV COLETA_DISPONIVEL=0
EXPOSE 8000
CMD ["uvicorn", "web_api:app", "--host", "0.0.0.0", "--port", "8000"]
