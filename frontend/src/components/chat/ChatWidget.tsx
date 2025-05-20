import { useEffect, useState } from 'react';
import { Input, Button, List, Avatar, Spin, Alert } from 'antd';
import { SendOutlined, UserOutlined } from '@ant-design/icons';

interface Message {
  id: number;
  sender_id: number;
  content: string;
  created_at: string;
  sender_name?: string;
}

interface ChatWidgetProps {
  chatId: number;
}

export default function ChatWidget({ chatId }: ChatWidgetProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);

  const fetchMessages = async () => {
    setLoading(true);
    try {
      // Здесь был бы запрос к API
      // const response = await fetch(`/api/chats/${chatId}/messages`);
      // const data = await response.json();
      
      // Заглушка для демонстрации
      const demoMessages: Message[] = [
        {
          id: 1,
          sender_id: 1,
          content: 'Здравствуйте! Когда будет доставлен товар?',
          created_at: new Date(Date.now() - 86400000).toISOString(),
          sender_name: 'Покупатель'
        },
        {
          id: 2,
          sender_id: 2,
          content: 'Добрый день! Отправим товар завтра, доставка займет 2-3 дня.',
          created_at: new Date(Date.now() - 43200000).toISOString(),
          sender_name: 'Продавец'
        }
      ];
      
      setMessages(demoMessages);
      setError(null);
    } catch (err) {
      setError('Не удалось загрузить сообщения чата');
      console.error('Error fetching messages:', err);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim()) return;
    
    setSending(true);
    try {
      // Здесь был бы запрос к API
      // const response = await fetch(`/api/chats/${chatId}/messages`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ content: newMessage }),
      // });
      // const data = await response.json();
      
      // Заглушка для демонстрации
      const demoMessage: Message = {
        id: messages.length + 1,
        sender_id: 1, // Предполагаем, что это текущий пользователь
        content: newMessage,
        created_at: new Date().toISOString(),
        sender_name: 'Вы'
      };
      
      setMessages([...messages, demoMessage]);
      setNewMessage('');
      setError(null);
    } catch (err) {
      setError('Не удалось отправить сообщение');
      console.error('Error sending message:', err);
    } finally {
      setSending(false);
    }
  };

  useEffect(() => {
    if (chatId) {
      fetchMessages();
    }
  }, [chatId]);

  if (loading && messages.length === 0) {
    return (
      <div className="flex justify-center items-center p-6">
        <Spin tip="Загрузка сообщений..." />
      </div>
    );
  }

  return (
    <div className="chat-widget">
      {error && (
        <Alert 
          message="Ошибка" 
          description={error}
          type="error" 
          showIcon 
          className="mb-4"
          closable
          onClose={() => setError(null)}
        />
      )}
      
      <List
        className="message-list"
        itemLayout="horizontal"
        dataSource={messages}
        renderItem={(message) => (
          <List.Item>
            <List.Item.Meta
              avatar={<Avatar icon={<UserOutlined />} />}
              title={`${message.sender_name || `Пользователь ${message.sender_id}`} - ${new Date(message.created_at).toLocaleString()}`}
              description={message.content}
            />
          </List.Item>
        )}
      />
      
      <div className="message-input flex mt-4">
        <Input.TextArea
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          placeholder="Введите сообщение..."
          autoSize={{ minRows: 1, maxRows: 3 }}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault();
              sendMessage();
            }
          }}
          className="flex-grow"
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={sendMessage}
          loading={sending}
          className="ml-2"
        >
          Отправить
        </Button>
      </div>
    </div>
  );
} 