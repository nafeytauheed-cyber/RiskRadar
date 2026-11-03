FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend /app/backend
COPY ml /app/ml
COPY simulator /app/simulator
COPY migrations /app/migrations
COPY benchmarks/scientific/model.json /app/benchmarks/scientific/model.json
ENV PYTHONPATH=/app:/app/backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
RUN useradd --uid 10001 --create-home app
USER app
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
