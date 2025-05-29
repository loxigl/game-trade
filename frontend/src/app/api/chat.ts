import { apiClient } from './client';
import { 
  Chat, 
  Message, 
  ChatCreateRequest, 
  MessageCreateRequest, 
  MessageUpdateRequest,
  ChatListResponse,
  MessageListResponse
} from '../types/chat';

const CHAT_API_BASE = '/chat';

// HTTP API функции для чатов
export const chatApi = {
  // Создание чата
  async createChat(data: ChatCreateRequest): Promise<Chat> {
    const response = await apiClient.post(`${CHAT_API_BASE}/chats`, data);
    return response.data;
  },

  // Получение списка чатов пользователя
  async getChats(params?: {
    page?: number;
    page_size?: number;
    status?: string;
  }): Promise<ChatListResponse> {
    const response = await apiClient.get(`${CHAT_API_BASE}/chats`, { params });
    return response.data;
  },

  // Получение чата по ID
  async getChat(chatId: number): Promise<Chat> {
    const response = await apiClient.get(`${CHAT_API_BASE}/chats/${chatId}`);
    return response.data;
  },

  // Получение сообщений чата
  async getMessages(chatId: number, params?: {
    page?: number;
    page_size?: number;
  }): Promise<MessageListResponse> {
    const response = await apiClient.get(`${CHAT_API_BASE}/chats/${chatId}/messages`, { params });
    return response.data;
  },

  // Отправка сообщения
  async sendMessage(chatId: number, data: MessageCreateRequest): Promise<Message> {
    const response = await apiClient.post(`${CHAT_API_BASE}/chats/${chatId}/messages`, data);
    return response.data;
  },

  // Обновление сообщения
  async updateMessage(chatId: number, messageId: number, data: MessageUpdateRequest): Promise<Message> {
    const response = await apiClient.patch(`${CHAT_API_BASE}/chats/${chatId}/messages/${messageId}`, data);
    return response.data;
  },

  // Удаление сообщения
  async deleteMessage(chatId: number, messageId: number): Promise<void> {
    await apiClient.delete(`${CHAT_API_BASE}/chats/${chatId}/messages/${messageId}`);
  },

  // Отметка сообщений как прочитанных
  async markAsRead(chatId: number): Promise<void> {
    await apiClient.post(`${CHAT_API_BASE}/chats/${chatId}/read`);
  },

  // Создание чата для объявления (удобная функция)
  async createListingChat(listingId: number, sellerId: number): Promise<Chat> {
    return this.createChat({
      type: 'listing' as any,
      title: `Чат по объявлению #${listingId}`,
      listing_id: listingId,
      participant_ids: [sellerId] // Покупатель добавится автоматически
    });
  },

  // Создание чата для транзакции (удобная функция)
  async createTransactionChat(transactionId: number, sellerId: number, buyerId: number): Promise<Chat> {
    return this.createChat({
      type: 'completion' as any,
      title: `Чат по транзакции #${transactionId}`,
      transaction_id: transactionId,
      participant_ids: [sellerId, buyerId]
    });
  },

  // Поиск существующего чата для объявления
  async findListingChat(listingId: number): Promise<Chat | null> {
    try {
      const response = await this.getChats({ page_size: 100 });
      return response.chats.find(chat => 
        chat.type === 'listing' && chat.listing_id === listingId
      ) || null;
    } catch (error) {
      console.error('Ошибка поиска чата для объявления:', error);
      return null;
    }
  },

  // Поиск существующего чата для транзакции
  async findTransactionChat(transactionId: number): Promise<Chat | null> {
    try {
      const response = await this.getChats({ page_size: 100 });
      return response.chats.find(chat => 
        chat.type === 'completion' && chat.transaction_id === transactionId
      ) || null;
    } catch (error) {
      console.error('Ошибка поиска чата для транзакции:', error);
      return null;
    }
  }
};

// WebSocket класс для работы с чатами
export class ChatWebSocket {
  private ws: WebSocket | null = null;
  private token: string | null = null;
  private isConnected = false;
  private messageHandlers: Map<string, (data: any) => void> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 1000;

  constructor(token: string) {
    this.token = token;
  }

  // Подключение к WebSocket
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.isConnected) {
        resolve();
        return;
      }

      // Проверяем, что токен есть
      if (!this.token) {
        reject(new Error('Токен не установлен для WebSocket подключения'));
        return;
      }

      // Определяем WebSocket URL
      let wsUrl: string;
      if (process.env.NEXT_PUBLIC_WS_URL) {
        wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws?token=${encodeURIComponent(this.token)}`;
      } else {
        // Fallback для разработки - используем nginx proxy
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        wsUrl = `${protocol}//${host}/ws?token=${encodeURIComponent(this.token)}`;
      }
      
      
      try {
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {

          this.isConnected = true;
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            console.log('Получено WebSocket сообщение:', message);
            this.handleMessage(message);
          } catch (error) {
            console.error('Ошибка парсинга WebSocket сообщения:', error);
          }
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket отключен', event.code, event.reason);
          this.isConnected = false;
          
          // Автоматическое переподключение
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            setTimeout(() => {
              this.reconnectAttempts++;
              this.connect();
            }, this.reconnectInterval * this.reconnectAttempts);
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket ошибка:', error);
          reject(error);
        };

      } catch (error) {
        console.error('Ошибка создания WebSocket:', error);
        reject(error);
      }
    });
  }

  // Отключение от WebSocket
  disconnect(): void {
    if (this.ws) {
      this.isConnected = false;
      this.ws.close();
      this.ws = null;
    }
  }

  // Отправка сообщения
  send(message: any): void {
    if (this.ws && this.isConnected) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket не подключен');
    }
  }

  // Подписка на чат
  joinChat(chatId: number): void {
    this.send({
      type: 'join_chat',
      data: { chat_id: chatId }
    });
  }

  // Отписка от чата
  leaveChat(chatId: number): void {
    this.send({
      type: 'leave_chat',
      data: { chat_id: chatId }
    });
  }

  // Уведомление о печатании
  sendTyping(chatId: number, isTyping: boolean): void {
    this.send({
      type: 'typing',
      data: { chat_id: chatId, is_typing: isTyping }
    });
  }

  // Пинг для поддержания соединения
  ping(): void {
    this.send({
      type: 'ping',
      data: { timestamp: Date.now() }
    });
  }

  // Обработка входящих сообщений
  private handleMessage(message: any): void {
    const handler = this.messageHandlers.get(message.type);
    if (handler) {
      handler(message.data);
    }
  }

  // Подписка на события
  on(eventType: string, handler: (data: any) => void): void {
    this.messageHandlers.set(eventType, handler);
  }

  // Отписка от событий
  off(eventType: string): void {
    this.messageHandlers.delete(eventType);
  }

  // Проверка состояния подключения
  get connected(): boolean {
    return this.isConnected && this.ws?.readyState === WebSocket.OPEN;
  }
}

// Утилитарная функция для создания или получения чата для объявления
export async function getOrCreateListingChat(listingId: number, sellerId: number): Promise<Chat> {
  // Сначала ищем существующий чат
  let chat = await chatApi.findListingChat(listingId);
  
  if (!chat) {
    // Если чат не найден, создаем новый
    chat = await chatApi.createListingChat(listingId, sellerId);
  }
  
  return chat;
}

// Утилитарная функция для создания или получения чата для транзакции
export async function getOrCreateTransactionChat(transactionId: number, sellerId: number, buyerId: number): Promise<Chat> {
  // Сначала ищем существующий чат
  let chat = await chatApi.findTransactionChat(transactionId);
  
  if (!chat) {
    // Если чат не найден, создаем новый
    chat = await chatApi.createTransactionChat(transactionId, sellerId, buyerId);
  }
  
  return chat;
} 