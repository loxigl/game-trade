import asyncio
from src.database.connection import Base, async_engine
from src.database.seed import seed_all

async def reset_database():
    print("❗ Удаление всех таблиц...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("✅ Все таблицы удалены.")

        await conn.run_sync(Base.metadata.create_all)
        print("✅ Все таблицы пересозданы.")

    print("🌱 Начинаем сидирование данных...")
    await seed_all()
    print("🎉 База данных успешно пересоздана и заполнена.")

if __name__ == "__main__":
    asyncio.run(reset_database())
