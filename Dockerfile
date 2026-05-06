FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data uploads/scans static

ENV BASESECRETS_HOST=0.0.0.0
ENV BASESECRETS_PORT=8000
ENV BASESECRETS_RELOAD=false

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/login')" || exit 1

CMD ["python", "run.py"]
