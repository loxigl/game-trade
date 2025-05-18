FROM python:3.10-slim

WORKDIR /app

# Установка дополнительных зависимостей
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Экспортируем порт, на котором будет работать приложение
EXPOSE 8000

# Команда для запуска приложения
# Параметры можно переопределить через docker-compose или Kubernetes конфигурацию
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"] 