"""
HTTP клиент для взаимодействия с chat-service
"""
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from ..config.settings import get_settings

logger = logging.getLogger(__name__)

class ChatClient:
    """
    HTTP клиент для взаимодействия с chat-service
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.CHAT_SERVICE_URL or "http://chat-svc:8000"
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def create_chat(
        self,
        title: str,
        participant_ids: List[int],
        chat_type: str = "listing",
        listing_id: Optional[int] = None,
        transaction_id: Optional[int] = None,
        system_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Создать чат через системный эндпоинт
        
        Args:
            title: Заголовок чата
            participant_ids: Список ID участников
            chat_type: Тип чата (listing, completion, support, dispute)
            listing_id: ID объявления (для чатов по объявлениям)
            transaction_id: ID транзакции (для чатов по транзакциям)
            system_token: Системный токен для авторизации
            
        Returns:
            Данные созданного чата или None при ошибке
        """
        # Используем системный эндпоинт для создания чатов
        url = f"{self.base_url}/chats/system/create"
        
        data = {
            "title": title,
            "participant_ids": participant_ids,
            "type": chat_type
        }
        
        if listing_id:
            data["listing_id"] = listing_id
        if transaction_id:
            data["transaction_id"] = transaction_id
        
        # Системный токен передается как параметр запроса
        params = {}
        if system_token:
            params["system_token"] = system_token
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                logger.info(f"Creating chat via system endpoint: {data}")
                async with session.post(url, json=data, params=params) as response:
                    if response.status == 201:
                        result = await response.json()
                        logger.info(f"Chat created successfully: {result}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to create chat. Status: {response.status}, Error: {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error creating chat: {str(e)}")
            return None
    
    async def get_chat(self, chat_id: int, user_token: str) -> Optional[Dict[str, Any]]:
        """
        Получить чат по ID
        
        Args:
            chat_id: ID чата
            user_token: Токен пользователя для авторизации
            
        Returns:
            Данные чата или None при ошибке
        """
        url = f"{self.base_url}/chats/{chat_id}"
        headers = {"Authorization": f"Bearer {user_token}"}
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to get chat {chat_id}. Status: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting chat {chat_id}: {str(e)}")
            return None
    
    async def find_listing_chat(
        self, 
        listing_id: int, 
        buyer_id: int, 
        seller_id: int,
        user_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Найти существующий чат по объявлению между покупателем и продавцом
        
        Args:
            listing_id: ID объявления
            buyer_id: ID покупателя
            seller_id: ID продавца
            user_token: Токен пользователя для авторизации
            
        Returns:
            Данные чата или None если не найден
        """
        url = f"{self.base_url}/chats"
        headers = {"Authorization": f"Bearer {user_token}"}
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        chats = data.get("chats", [])
                        
                        # Ищем чат типа "listing" с нужным listing_id и участниками
                        for chat in chats:
                            if (chat.get("type") == "listing" and 
                                chat.get("listing_id") == listing_id):
                                
                                participant_ids = [p.get("user_id") for p in chat.get("participants", [])]
                                if buyer_id in participant_ids and seller_id in participant_ids:
                                    return chat
                        
                        return None
                    else:
                        logger.error(f"Failed to get chats. Status: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error finding listing chat: {str(e)}")
            return None
    
    async def get_or_create_listing_chat(
        self,
        listing_id: int,
        buyer_id: int,
        seller_id: int,
        listing_title: str,
        user_token: Optional[str] = None,
        system_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Получить существующий чат по объявлению или создать новый
        
        Args:
            listing_id: ID объявления
            buyer_id: ID покупателя
            seller_id: ID продавца
            listing_title: Заголовок объявления
            user_token: Токен пользователя для поиска чата
            system_token: Системный токен для создания чата
            
        Returns:
            Данные чата
        """
        # Сначала пытаемся найти существующий чат
        if user_token:
            existing_chat = await self.find_listing_chat(listing_id, buyer_id, seller_id, user_token)
            if existing_chat:
                logger.info(f"Found existing chat for listing {listing_id}: {existing_chat.get('id')}")
                return existing_chat
        
        # Если не найден, создаем новый
        chat_title = f"Чат по объявлению: {listing_title}"
        
        return await self.create_chat(
            title=chat_title,
            participant_ids=[buyer_id, seller_id],
            chat_type="listing",
            listing_id=listing_id,
            system_token=system_token
        )
    
    async def update_chat(self,chat_id:int,transaction_id:int,listing_id:int,user_token:str):
        """
        Обновляет чат, обновляя transaction_id или listing_id
        """
        url = f"{self.base_url}/chats/{chat_id}"
        data = {
            "transaction_id": transaction_id,
            "listing_id": listing_id
        }
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.put(url, json=data) as response:
                return await response.json()


def get_chat_client() -> ChatClient:
    """
    Получить экземпляр ChatClient
    
    Returns:
        Экземпляр ChatClient
    """
    return ChatClient()
