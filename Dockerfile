FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" reportlab requests \
    beautifulsoup4 pdfplumber
ENV COLETA_DISPONIVEL=0
EXPOSE 8000
CMD ["uvicorn", "web_api:app", "--host", "0.0.0.0", "--port", "8000"]
