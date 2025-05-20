import React, { useState } from 'react';
import { 
  Form, 
  Input, 
  Button, 
  InputNumber, 
  Card, 
  Typography, 
  message, 
  DatePicker, 
  Space, 
  Divider, 
  Alert
} from 'antd';
import { ShoppingCartOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { TransactionCreate } from '../../types/transaction';
import * as transactionApi from '../../api/transaction';
import { useRouter } from 'next/navigation';

const { Title, Text } = Typography;

interface TransactionInitiatorProps {
  buyerId: number;
  sellerId: number;
  listingId: number;
  listingTitle: string;
  suggestedAmount?: number;
  onSuccess?: (transactionId: number) => void;
  onCancel?: () => void;
}

const TransactionInitiator: React.FC<TransactionInitiatorProps> = ({
  buyerId,
  sellerId,
  listingId,
  listingTitle,
  suggestedAmount,
  onSuccess,
  onCancel
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState<boolean>(false);
  const router = useRouter();

  // Обработчик отправки формы
  const handleSubmit = async (values: any) => {
    setLoading(true);
    
    try {
      const transactionData: TransactionCreate = {
        buyerId,
        sellerId,
        listingId,
        amount: values.amount,
        description: values.description,
        expirationDate: values.expirationDate ? values.expirationDate.toISOString() : undefined
      };
      
      const transaction = await transactionApi.createTransaction(transactionData);
      
      message.success('Транзакция успешно создана');
      
      if (onSuccess) {
        onSuccess(transaction.id);
      } else {
        // Перенаправляем на страницу деталей транзакции
        router.push(`/transactions/${transaction.id}`);
      }
    } catch (error) {
      console.error('Ошибка создания транзакции:', error);
      message.error('Не удалось создать транзакцию');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="transaction-initiator">
      <div className="mb-6">
        <Title level={4}>Создание транзакции</Title>
        <Text type="secondary">
          Заполните детали для инициирования безопасной сделки через Escrow
        </Text>
      </div>
      
      <Alert
        message="Безопасная сделка с Escrow"
        description="Ваши средства будут заблокированы до момента успешного завершения сделки. В случае возникновения проблем, вы сможете открыть спор и получить возврат."
        type="info"
        showIcon
        className="mb-6"
      />
      
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          amount: suggestedAmount,
          description: `Покупка: ${listingTitle}`
        }}
      >
        <Form.Item
          name="amount"
          label="Сумма транзакции"
          rules={[
            { required: true, message: 'Введите сумму транзакции' },
            { type: 'number', min: 1, message: 'Сумма должна быть больше нуля' }
          ]}
        >
          <InputNumber 
            style={{ width: '100%' }} 
            placeholder="Введите сумму" 
            prefix="₽" 
            precision={2}
          />
        </Form.Item>
        
        <Form.Item
          name="description"
          label="Описание транзакции"
          rules={[
            { required: true, message: 'Введите описание транзакции' },
            { max: 255, message: 'Максимальная длина описания 255 символов' }
          ]}
        >
          <Input.TextArea 
            placeholder="Введите описание транзакции" 
            rows={3}
          />
        </Form.Item>
        
        <Form.Item
          name="expirationDate"
          label="Дата истечения срока"
          help="Если транзакция не будет завершена до этой даты, средства автоматически вернутся на ваш счет"
        >
          <DatePicker 
            style={{ width: '100%' }} 
            placeholder="Выберите дату истечения"
            showTime
            format="DD.MM.YYYY HH:mm"
          />
        </Form.Item>
        
        <Divider />
        
        <div className="flex justify-between">
          <Space>
            <Text strong>Продавец ID:</Text>
            <Text>{sellerId}</Text>
          </Space>
          
          <Space>
            <Text strong>Товар ID:</Text>
            <Text>{listingId}</Text>
          </Space>
        </div>
        
        <Divider />
        
        <div className="flex justify-end mt-4">
          <Space>
            <Button onClick={onCancel}>
              Отмена
            </Button>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              icon={<ShoppingCartOutlined />}
            >
              Создать транзакцию
            </Button>
          </Space>
        </div>
      </Form>
    </Card>
  );
};

export default TransactionInitiator; 