from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import asyncio

from .services.rabbitmq_service import get_rabbitmq_service
from .services.message_handler import setup_rabbitmq_consumers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GameTrade Chat Service",
    description="API для обмена сообщениями между пользователями",
    version="0.1.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на реальные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """
    Выполняется при запуске приложения
    Инициализирует соединение с RabbitMQ и настраивает потребителей сообщений
    """
    try:
        # Инициализация соединения с RabbitMQ
        rabbitmq_service = get_rabbitmq_service()
        await rabbitmq_service.connect()
        logger.info("Successfully connected to RabbitMQ")
        
        # Настройка потребителей сообщений
        await setup_rabbitmq_consumers()
        logger.info("RabbitMQ consumers are set up")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Выполняется при остановке приложения
    Закрывает соединение с RabbitMQ
    """
    try:
        rabbitmq_service = get_rabbitmq_service()
        await rabbitmq_service.close()
        logger.info("RabbitMQ connection closed")
    except Exception as e:
        logger.error(f"Error closing RabbitMQ connection: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Chat Service API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "chat"}

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, chat_id: str):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
        self.active_connections[chat_id].append(websocket)

    def disconnect(self, websocket: WebSocket, chat_id: str):
        if chat_id in self.active_connections:
            if websocket in self.active_connections[chat_id]:
                self.active_connections[chat_id].remove(websocket)
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]

    async def send_message(self, message: str, chat_id: str):
        if chat_id in self.active_connections:
            for connection in self.active_connections[chat_id]:
                await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    await manager.connect(websocket, chat_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_message(f"{data}", chat_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True) 