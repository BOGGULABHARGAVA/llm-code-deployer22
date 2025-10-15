# Use official Python 3.12 slim image as the base
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock /app/

# Upgrade pip and install required packages
RUN pip install --upgrade pip \
  && pip install "uvicorn[standard]" sqlalchemy aiosqlite python-dotenv openai fastapi httpx PyGithub

# Copy the rest of your application code
COPY . /app

# Expose port 8000 for FastAPI
EXPOSE 8000

# Default command to run your app with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
