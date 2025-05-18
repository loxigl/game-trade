#!/usr/bin/env python
"""
Скрипт для инициализации Redis.
Добавляет базовые ключи и структуры данных, необходимые для работы сервиса аутентификации.
"""

import redis
import os
import json
import argparse
from datetime import datetime

def initialize_redis(redis_url):
    """
    Инициализация Redis для сервиса аутентификации
    
    Args:
        redis_url: URL для подключения к Redis
        
    Returns:
        bool: True если инициализация успешна, иначе False
    """
    try:
        # Подключаемся к Redis
        r = redis.from_url(redis_url, decode_responses=True)
        
        # Проверяем соединение
        r.ping()
        print(f"✅ Успешное подключение к Redis: {redis_url}")
        
        # Очищаем существующие ключи (опционально, для чистой инициализации)
        # r.flushdb()
        # print("✅ Redis база очищена")
        
        # Устанавливаем ключ с информацией о сервисе
        service_info = {
            "name": "auth-service",
            "version": "0.1.0",
            "initialized_at": datetime.now().isoformat()
        }
        r.set("auth:service:info", json.dumps(service_info))
        print("✅ Установлена информация о сервисе")
        
        # Устанавливаем ключ для отслеживания количества запросов аутентификации
        r.set("auth:stats:login_attempts", 0)
        print("✅ Установлены начальные счетчики статистики")
        
        # Устанавливаем TTL для сессий по умолчанию (24 часа в секундах)
        r.set("auth:config:session_ttl", 86400)
        print("✅ Установлены конфигурационные параметры")
        
        print("\n🚀 Инициализация Redis успешно завершена!")
        return True
    except redis.exceptions.ConnectionError as e:
        print(f"❌ Ошибка подключения к Redis: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка инициализации Redis: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Инициализация Redis для сервиса аутентификации")
    parser.add_argument(
        "--redis-url", 
        default=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        help="URL для подключения к Redis"
    )
    
    args = parser.parse_args()
    success = initialize_redis(args.redis_url)
    
    # Возвращаем код статуса для скриптов
    exit(0 if success else 1) 