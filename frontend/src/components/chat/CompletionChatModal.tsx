'use client';

import { useState, useEffect } from 'react';
import { Modal, Button, Input, Typography, Rate, Space, Divider, message } from 'antd';
import { SendOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import Chat from '../../app/components/Chat';
import { useAuth } from '../../app/hooks/auth';

const { TextArea } = Input;
const { Title, Text, Paragraph } = Typography;

interface CompletionChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  saleId: number;
  sellerId: number;
  transactionId: number;
  onCompletionConfirmed?: () => void;
}

export default function CompletionChatModal({
  isOpen,
  onClose,
  saleId,
  sellerId,
  transactionId,
  onCompletionConfirmed
}: CompletionChatModalProps) {
  const { user } = useAuth();
  const [feedbackText, setFeedbackText] = useState('');
  const [rating, setRating] = useState(5);
  const [submitting, setSubmitting] = useState(false);
  const [displayMode, setDisplayMode] = useState<'chat' | 'feedback'>('chat');
  
  // Создаем ID чата на основе ID продажи
  const chatId = `completion_${saleId}`;

  useEffect(() => {
    // Сбрасываем состояние при открытии модального окна
    if (isOpen) {
      setDisplayMode('chat');
      setFeedbackText('');
      setRating(5);
    }
  }, [isOpen]);

  const handleCompleteTransaction = async () => {
    if (!user) return;
    
    setSubmitting(true);
    try {
      // Отправляем запрос на завершение транзакции
      const response = await fetch(`/api/payment/sales/${saleId}/complete-delivery?transaction_id=${transactionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ comment: feedbackText })
      });
      
      if (!response.ok) {
        throw new Error('Не удалось завершить транзакцию');
      }
      
      const data = await response.json();
      
      // Показываем подтверждение
      message.success('Транзакция успешно завершена! Спасибо за покупку.');
      
      // Вызываем callback, если он предоставлен
      if (onCompletionConfirmed) {
        onCompletionConfirmed();
      }
      
      // Закрываем модальное окно
      onClose();
      
    } catch (error) {
      console.error('Ошибка при завершении транзакции:', error);
      message.error('Произошла ошибка при завершении транзакции');
    } finally {
      setSubmitting(false);
    }
  };

  // Обработчик переключения на экран отзыва
  const handleSwitchToFeedback = () => {
    setDisplayMode('feedback');
  };

  return (
    <Modal
      title="Подтверждение завершения заказа"
      open={isOpen}
      onCancel={onClose}
      footer={null}
      width={800}
    >
      {displayMode === 'chat' ? (
        <>
          <Paragraph>
            Пожалуйста, обсудите с продавцом детали доставки и подтвердите получение товара. 
            После подтверждения, деньги будут переведены продавцу.
          </Paragraph>
          
          <div style={{ height: 400, marginBottom: 16 }}>
            <Chat chatId={chatId} />
          </div>
          
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Button icon={<CloseCircleOutlined />} onClick={onClose}>
              Закрыть
            </Button>
            <Button 
              type="primary" 
              icon={<CheckCircleOutlined />} 
              onClick={handleSwitchToFeedback}
            >
              Подтвердить получение
            </Button>
          </div>
        </>
      ) : (
        <>
          <Title level={4}>Оставьте отзыв о продавце</Title>
          <Paragraph>
            Поделитесь своим опытом взаимодействия с продавцом. Ваш отзыв поможет другим покупателям.
          </Paragraph>
          
          <div style={{ marginBottom: 16 }}>
            <Text strong>Оценка:</Text>
            <Rate value={rating} onChange={setRating} />
          </div>
          
          <div style={{ marginBottom: 16 }}>
            <Text strong>Комментарий:</Text>
            <TextArea
              rows={4}
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              placeholder="Расскажите о своем опыте покупки..."
              maxLength={500}
              showCount
            />
          </div>
          
          <Divider />
          
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Button onClick={() => setDisplayMode('chat')}>
              Вернуться к чату
            </Button>
            <Button 
              type="primary" 
              onClick={handleCompleteTransaction}
              loading={submitting}
            >
              Завершить заказ
            </Button>
          </div>
        </>
      )}
    </Modal>
  );
} 