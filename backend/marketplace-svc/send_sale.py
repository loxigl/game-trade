import asyncio
from src.services.rabbitmq_service import get_rabbitmq_service
from src.config.settings import get_settings
from src.database.connection import get_db
from src.models.core import Sale

async def send_sale_message():
    settings = get_settings()
    rabbitmq = get_rabbitmq_service()
    db = next(get_db())
    
    # Получаем продажу по ID
    sale = db.query(Sale).filter(Sale.id == 45).first()
    if not sale:
        print(f"Продажа с ID 45 не найдена")
        return
    
    # Формируем сообщение
    message = {
        "sale_id": sale.id,
        "listing_id": sale.listing_id,
        "buyer_id": sale.buyer_id,
        "seller_id": sale.seller_id,
        "price": float(sale.price),
        "currency": sale.currency,
        "status": sale.status,
        "created_at": sale.created_at.isoformat(),
        "wallet_id": None
    }
    
    # Подключаемся к RabbitMQ и отправляем сообщение
    await rabbitmq.connect()
    await rabbitmq.publish(
        settings.RABBITMQ_EXCHANGE,
        settings.RABBITMQ_SALES_ROUTING_KEY,
        message
    )
    print(f"Отправлено сообщение о продаже: {message}")

if __name__ == "__main__":
    asyncio.run(send_sale_message()) 