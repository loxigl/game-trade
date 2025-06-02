export enum ChatType {
  LISTING = 'listing',
  COMPLETION = 'completion',
  SUPPORT = 'support',
  DISPUTE = 'dispute'
}

export enum ChatStatus {
  ACTIVE = 'active',
  ARCHIVED = 'archived',
  DISPUTED = 'disputed',
  RESOLVED = 'resolved'
}

export enum MessageType {
  TEXT = 'text',
  IMAGE = 'image',
  FILE = 'file',
  SYSTEM = 'system'
}

export interface ChatParticipant {
  id: number;
  user_id: number;
  role: string;
  is_muted: boolean;
  joined_at: string;
  last_read_at?: string;
}

export interface ChatModerator {
  id: number;
  moderator_id: number;
  assigned_by: number;
  reason?: string;
  is_active: boolean;
  resolved_at?: string;
  resolution_notes?: string;
  created_at: string;
}

export interface Chat {
  id: number;
  type: ChatType;
  status: ChatStatus;
  title?: string;
  listing_id?: number;
  transaction_id?: number;
  chat_metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
  participants: ChatParticipant[];
  moderators: ChatModerator[];
  unread_count?: number;
  last_message?: string;
}

export interface Message {
  id: number;
  chat_id: number;
  sender_id?: number;
  type: MessageType;
  content: string;
  attachments?: Array<Record<string, any>>;
  message_metadata?: Record<string, any>;
  is_edited: boolean;
  edited_at?: string;
  is_deleted: boolean;
  created_at: string;
}

export interface ChatCreateRequest {
  type?: ChatType;
  title?: string;
  listing_id?: number;
  transaction_id?: number;
  participant_ids: number[];
  chat_metadata?: Record<string, any>;
}

export interface MessageCreateRequest {
  content: string;
  type?: MessageType;
  attachments?: Array<Record<string, any>>;
  message_metadata?: Record<string, any>;
}

export interface MessageUpdateRequest {
  content: string;
}

export interface ChatListResponse {
  chats: Chat[];
  total: number;
  page: number;
  pages: number;
}

export interface MessageListResponse {
  messages: Message[];
  total: number;
  page: number;
  pages: number;
}

// WebSocket типы
export interface WebSocketMessage {
  type: string;
  data: Record<string, any>;
}

export interface TypingNotification {
  user_id: number;
  chat_id: number;
  is_typing: boolean;
}

// Типы для WebSocket сообщений
export enum WSMessageType {
  // Аутентификация
  AUTH = 'auth',
  
  // Управление чатами
  JOIN_CHAT = 'join_chat',
  LEAVE_CHAT = 'leave_chat',
  
  // Сообщения
  NEW_MESSAGE = 'new_message',
  MESSAGE_UPDATED = 'message_updated',
  MESSAGE_DELETED = 'message_deleted',
  
  // Уведомления
  TYPING = 'typing',
  USER_JOINED = 'user_joined',
  USER_LEFT = 'user_left',
  
  // Служебные
  PING = 'ping',
  PONG = 'pong',
  ERROR = 'error'
}

export interface WSAuthMessage {
  type: WSMessageType.AUTH;
  data: {
    token: string;
  };
}

export interface WSJoinChatMessage {
  type: WSMessageType.JOIN_CHAT;
  data: {
    chat_id: number;
  };
}

export interface WSLeaveChatMessage {
  type: WSMessageType.LEAVE_CHAT;
  data: {
    chat_id: number;
  };
}

export interface WSNewMessageMessage {
  type: WSMessageType.NEW_MESSAGE;
  data: Message;
}

export interface WSTypingMessage {
  type: WSMessageType.TYPING;
  data: {
    chat_id: number;
    is_typing: boolean;
  };
}

export interface WSPingMessage {
  type: WSMessageType.PING;
  data: {
    timestamp?: number;
  };
}

export interface WSErrorMessage {
  type: WSMessageType.ERROR;
  data: {
    message: string;
  };
}

export type WSIncomingMessage = 
  | WSNewMessageMessage
  | WSTypingMessage
  | { type: WSMessageType.PONG; data: { timestamp?: number } }
  | { type: WSMessageType.USER_JOINED; data: { user_id: number; chat_id: number } }
  | { type: WSMessageType.USER_LEFT; data: { user_id: number; chat_id: number } }
  | { type: WSMessageType.MESSAGE_UPDATED; data: Message }
  | { type: WSMessageType.MESSAGE_DELETED; data: { message_id: number; chat_id: number } }
  | WSErrorMessage;

export type WSOutgoingMessage = 
  | WSAuthMessage
  | WSJoinChatMessage
  | WSLeaveChatMessage
  | WSTypingMessage
  | WSPingMessage; 