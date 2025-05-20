'use client';

import React, { useState, useEffect } from 'react';
import { Modal, Form, Select, Button, Alert, Spin, message } from 'antd';
import { useWallet } from '../hooks/wallet';
import { releaseFunds } from '../api/sale';
import { Sale } from '../types/sale';
import { formatPrice } from '../utils/formatPrice';

interface FundsReleaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  sale: Sale | null;
  transactionId: number | null;
  onSuccess?: () => void;
}

const FundsReleaseModal: React.FC<FundsReleaseModalProps> = ({ 
  isOpen, 
  onClose, 
  sale, 
  transactionId,
  onSuccess
}) => {
  const [form] = Form.useForm();
  const { wallets, loading: walletsLoading, error: walletsError } = useWallet();
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  // Сброс формы при открытии модального окна
  useEffect(() => {
    if (isOpen) {
      form.resetFields();
      setError(null);
    }
  }, [isOpen, form]);
  
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (!sale || !transactionId) {
        setError('Информация о продаже отсутствует');
        return;
      }
      
      setIsSubmitting(true);
      setError(null);
      
      const result = await releaseFunds(
        sale.id,
        transactionId,
        values.wallet_id
      );
      
      message.success('Средства успешно зачислены на баланс кошелька');
      onClose();
      
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      console.error('Ошибка при запросе вывода средств:', err);
      setError(err instanceof Error ? err.message : 'Произошла ошибка при запросе вывода средств');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Расчет суммы к выводу
  const getFinalAmount = () => {
    if (!sale) return 0;
    
    const feePercentage = sale.extra_data?.fee_percentage || 0;
    const totalAmount = sale.price;
    const feeAmount = totalAmount * (feePercentage / 100);
    
    return totalAmount - feeAmount;
  };
  
  return (
    <Modal
      title="Вывод средств за завершенную продажу"
      open={isOpen}
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>
          Отмена
        </Button>,
        <Button 
          key="submit" 
          type="primary" 
          onClick={handleSubmit}
          loading={isSubmitting}
          disabled={!sale || !transactionId || walletsLoading || wallets.length === 0}
        >
          Вывести средства
        </Button>
      ]}
    >
      {walletsLoading ? (
        <div className="flex justify-center items-center py-6">
          <Spin size="large" />
        </div>
      ) : walletsError ? (
        <Alert
          type="error"
          message="Ошибка при загрузке кошельков"
          description={walletsError}
          className="mb-4"
        />
      ) : wallets.length === 0 ? (
        <Alert
          type="warning"
          message="У вас нет активных кошельков"
          description="Для вывода средств необходимо создать кошелек"
          className="mb-4"
        />
      ) : (
        <Form
          form={form}
          layout="vertical"
          initialValues={{ wallet_id: wallets[0]?.id }}
        >
          {error && (
            <Alert
              type="error"
              message="Ошибка"
              description={error}
              className="mb-4"
            />
          )}
          
          <div className="mb-4">
            <p className="text-lg font-semibold">Информация о продаже</p>
            {sale && (
              <>
                <p className="mb-1">
                  <span className="text-gray-500">ID продажи:</span> {sale.id}
                </p>
                <p className="mb-1">
                  <span className="text-gray-500">Название товара:</span> {sale.listing_title || 'Не указано'}
                </p>
                <p className="mb-1">
                  <span className="text-gray-500">Сумма продажи:</span> {formatPrice(sale.price, sale.currency)}
                </p>
                <p className="mb-1">
                  <span className="text-gray-500">Сумма к выводу:</span> {formatPrice(getFinalAmount(), sale.currency)}
                </p>
              </>
            )}
          </div>
          
          <Form.Item
            name="wallet_id"
            label="Выберите кошелек для зачисления средств"
            rules={[{ required: true, message: 'Пожалуйста, выберите кошелек' }]}
          >
            <Select>
              {wallets.map((wallet) => (
                <Select.Option key={wallet.id} value={wallet.id}>
                  Кошелек #{wallet.id} - {wallet.is_default ? 'Основной' : 'Дополнительный'}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          
          <Alert
            type="info"
            message="Важно!"
            description="После подтверждения средства будут зачислены на выбранный кошелек. Вы сможете вывести их в любое время."
            className="mb-4"
          />
        </Form>
      )}
    </Modal>
  );
};

export default FundsReleaseModal; 