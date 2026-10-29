# Image unique : interface web compilée + API FastAPI
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npx vite build

FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY market_news.db ./
COPY --from=frontend /app/frontend/dist frontend/dist
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000
WORKDIR /app/backend
CMD ["python", "main.py"]
