FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npx vite build

FROM python:3.12-slim
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy backend
COPY tools/ ./tools/
COPY config.yaml pyproject.toml llmbase.py wsgi.py ./
COPY entrypoint.sh ./
RUN pip install --no-cache-dir -e .
RUN chmod +x entrypoint.sh

# Copy built frontend
COPY --from=frontend-build /app/static/dist ./static/dist

# Expose port
EXPOSE 5555

# entrypoint ensures data dirs exist on the mounted volume
CMD ["./entrypoint.sh"]
