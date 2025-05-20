import React, { useState, useEffect } from 'react';
import {
  Card,
  Typography,
  Descriptions,
  Divider,
  Button,
  Space,
  Modal,
  Input,
  message,
  Spin,
  Tabs
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  QuestionCircleOutlined,
  SyncOutlined,
  HistoryOutlined
} from '@ant-design/icons';
import { 
  Transaction, 
  TransactionStatus,
  TransactionActionResponse 
} from '../../types/transaction';
import TransactionStatusBadge from './TransactionStatusBadge';
import TransactionHistoryTimeline from './TransactionHistoryTimeline';
import * as transactionApi from '../../api/transaction';
import formatDate from '../../utils/formatDate';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { TabPane } = Tabs;

interface TransactionDetailProps {
  transactionId: number;
}

const TransactionDetail: React.FC<TransactionDetailProps> = ({ transactionId }) => {
  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const [actions, setActions] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [isModalVisible, setIsModalVisible] = useState<boolean>(false);
  const [modalAction, setModalAction] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [inFavorOfSeller, setInFavorOfSeller] = useState<boolean>(true);

  // Загрузка данных транзакции
  useEffect(() => {
    const fetchTransactionData = async () => {
      try {
        setLoading(true);
        const transactionData = await transactionApi.getTransaction(transactionId);
        setTransaction(transactionData);
        
        const availableActions = await transactionApi.getTransactionActions(transactionId);
        setActions(availableActions.actions);
      } catch (error) {
        console.error('Ошибка загрузки данных транзакции:', error);
        message.error('Не удалось загрузить данные транзакции');
      } finally {
        setLoading(false);
      }
    };

    fetchTransactionData();
  }, [transactionId]);

  // Перезагрузка данных
  const refreshData = async () => {
    setLoading(true);
    try {
      const transactionData = await transactionApi.getTransaction(transactionId);
      setTransaction(transactionData);
      
      const availableActions = await transactionApi.getTransactionActions(transactionId);
      setActions(availableActions.actions);
    } catch (error) {
      console.error('Ошибка обновления данных транзакции:', error);
      message.error('Не удалось обновить данные транзакции');
    } finally {
      setLoading(false);
    }
  };

  // Обработка нажатия на кнопку действия
  const handleAction = (action: string) => {
    setModalAction(action);
    setReason('');
    setIsModalVisible(true);
  };

  // Выполнение действия
  const executeAction = async () => {
    setActionLoading(true);
    try {
      switch (modalAction) {
        case 'escrow':
          await transactionApi.processEscrowPayment(transactionId);
          message.success('Средства успешно переведены в Escrow');
          break;
          
        case 'complete':
          await transactionApi.completeTransaction(transactionId);
          message.success('Транзакция успешно завершена');
          break;
          
        case 'refund':
          await transactionApi.refundTransaction(transactionId, reason);
          message.success('Средства успешно возвращены покупателю');
          break;
          
        case 'dispute':
          if (!reason.trim()) {
            message.error('Необходимо указать причину спора');
            setActionLoading(false);
            return;
          }
          await transactionApi.disputeTransaction(transactionId, reason);
          message.success('Спор успешно открыт');
          break;
          
        case 'resolve':
          await transactionApi.resolveDispute(transactionId, inFavorOfSeller, reason);
          message.success('Спор успешно разрешен');
          break;
          
        case 'cancel':
          await transactionApi.cancelTransaction(transactionId, reason);
          message.success('Транзакция отменена');
          break;
          
        default:
          message.error('Неизвестное действие');
      }
      
      setIsModalVisible(false);
      refreshData();
    } catch (error) {
      console.error('Ошибка выполнения действия:', error);
      message.error('Не удалось выполнить действие');
    } finally {
      setActionLoading(false);
    }
  };

  // Получение кнопки для действия
  const getActionButton = (action: string) => {
    let icon = null;
    let text;
    let type: "primary" | "default" | "dashed" | "link" | "text" | undefined = "default";
    
    switch (action) {
      case 'escrow':
        icon = <SyncOutlined />;
        text = 'Перевести в Escrow';
        type = 'primary';
        break;
      case 'complete':
        icon = <CheckCircleOutlined />;
        text = 'Завершить';
        type = 'primary';
        break;
      case 'refund':
        icon = <CloseCircleOutlined />;
        text = 'Вернуть средства';
        break;
      case 'dispute':
        icon = <ExclamationCircleOutlined />;
        text = 'Открыть спор';
        type = 'dashed';
        break;
      case 'resolve':
        icon = <QuestionCircleOutlined />;
        text = 'Разрешить спор';
        type = 'dashed';
        break;
      case 'cancel':
        icon = <CloseCircleOutlined />;
        text = 'Отменить';
        break;
      default:
        icon = null;
        text = action;
    }
    
    return (
      <Button 
        key={action} 
        type={type} 
        icon={icon} 
        onClick={() => handleAction(action)}
      >
        {text}
      </Button>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[200px]">
        <Spin tip="Загрузка данных транзакции..." />
      </div>
    );
  }

  if (!transaction) {
    return <div>Транзакция не найдена</div>;
  }

  return (
    <div className="transaction-detail">
      <Tabs defaultActiveKey="info" className="mb-4">
        <TabPane 
          tab={
            <span>
              <span className="mr-2">Информация о транзакции</span>
            </span>
          } 
          key="info"
        >
          <Card>
            <div className="flex justify-between items-center mb-4">
              <Title level={4}>Транзакция #{transaction.id}</Title>
              <TransactionStatusBadge status={transaction.status} />
            </div>
            
            <Descriptions bordered column={{ xxl: 3, xl: 3, lg: 2, md: 2, sm: 1, xs: 1 }}>
              <Descriptions.Item label="Тип">
                {transaction.type}
              </Descriptions.Item>
              <Descriptions.Item label="Сумма">
                {transaction.amount.toFixed(2)}
              </Descriptions.Item>
              <Descriptions.Item label="Комиссия">
                {transaction.fee?.toFixed(2) || '0.00'}
              </Descriptions.Item>
              <Descriptions.Item label="Покупатель">
                ID: {transaction.buyerId}
              </Descriptions.Item>
              <Descriptions.Item label="Продавец">
                ID: {transaction.sellerId}
              </Descriptions.Item>
              <Descriptions.Item label="ID товара">
                {transaction.listingId}
              </Descriptions.Item>
              <Descriptions.Item label="Дата создания">
                {formatDate(transaction.createdAt)}
              </Descriptions.Item>
              <Descriptions.Item label="Дата обновления">
                {formatDate(transaction.updatedAt)}
              </Descriptions.Item>
              {transaction.expirationDate && (
                <Descriptions.Item label="Срок действия до">
                  {formatDate(transaction.expirationDate)}
                </Descriptions.Item>
              )}
              {transaction.description && (
                <Descriptions.Item label="Описание" span={3}>
                  {transaction.description}
                </Descriptions.Item>
              )}
              {transaction.disputeReason && (
                <Descriptions.Item label="Причина спора" span={3}>
                  {transaction.disputeReason}
                </Descriptions.Item>
              )}
              {transaction.disputeResolution && (
                <Descriptions.Item label="Решение по спору" span={3}>
                  {transaction.disputeResolution}
                </Descriptions.Item>
              )}
            </Descriptions>
            
            <Divider />
            
            <div className="flex justify-between items-center">
              <Button icon={<SyncOutlined />} onClick={refreshData}>
                Обновить
              </Button>
              
              <Space>
                {actions.map(action => getActionButton(action))}
              </Space>
            </div>
          </Card>
        </TabPane>
        
        <TabPane 
          tab={
            <span>
              <HistoryOutlined />
              <span className="ml-2">История изменений</span>
            </span>
          } 
          key="history"
        >
          <TransactionHistoryTimeline transactionId={transactionId} />
        </TabPane>
      </Tabs>
      
      {/* Модальное окно подтверждения действия */}
      <Modal
        title={
          modalAction === 'escrow' ? 'Перевести в Escrow' :
          modalAction === 'complete' ? 'Завершить транзакцию' :
          modalAction === 'refund' ? 'Вернуть средства' :
          modalAction === 'dispute' ? 'Открыть спор' :
          modalAction === 'resolve' ? 'Разрешить спор' :
          modalAction === 'cancel' ? 'Отменить транзакцию' :
          'Подтверждение действия'
        }
        open={isModalVisible}
        onOk={executeAction}
        onCancel={() => setIsModalVisible(false)}
        confirmLoading={actionLoading}
      >
        <Space direction="vertical" className="w-full">
          <Paragraph>
            {
              modalAction === 'escrow' ? 'Вы уверены, что хотите перевести средства в Escrow?' :
              modalAction === 'complete' ? 'Вы уверены, что хотите завершить транзакцию и перевести средства продавцу?' :
              modalAction === 'refund' ? 'Вы уверены, что хотите вернуть средства покупателю?' :
              modalAction === 'dispute' ? 'Вы хотите открыть спор по этой транзакции?' :
              modalAction === 'resolve' ? 'Выберите, в чью пользу вы хотите разрешить спор:' :
              modalAction === 'cancel' ? 'Вы уверены, что хотите отменить эту транзакцию?' :
              'Подтвердите выполнение операции'
            }
          </Paragraph>
          
          {/* Дополнительные поля для определенных действий */}
          {['refund', 'dispute', 'resolve', 'cancel'].includes(modalAction) && (
            <TextArea
              placeholder="Укажите причину"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={4}
              required={modalAction === 'dispute'}
            />
          )}
          
          {modalAction === 'resolve' && (
            <Space direction="vertical" className="w-full">
              <Button 
                type={inFavorOfSeller ? "primary" : "default"} 
                block
                onClick={() => setInFavorOfSeller(true)}
              >
                В пользу продавца
              </Button>
              <Button 
                type={!inFavorOfSeller ? "primary" : "default"}
                block
                onClick={() => setInFavorOfSeller(false)}
              >
                В пользу покупателя
              </Button>
            </Space>
          )}
        </Space>
      </Modal>
    </div>
  );
};

export default TransactionDetail; 