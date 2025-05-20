import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Form, 
  Button, 
  DatePicker, 
  Input, 
  Select, 
  Divider, 
  Typography, 
  message, 
  Space,
  Alert
} from 'antd';
import { 
  DownloadOutlined, 
  FileExcelOutlined, 
  FileTextOutlined, 
  SearchOutlined 
} from '@ant-design/icons';
import { TransactionStatus } from '../../types/transaction';
import * as transactionApi from '../../api/transaction';
import { useSearchParams } from 'next/navigation';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

const TransactionReportsPage: React.FC = () => {
  const searchParams = useSearchParams();
  const transactionIdParam = searchParams.get('transactionId');
  
  const [form] = Form.useForm();
  const [loading, setLoading] = useState<boolean>(false);
  const [reportType, setReportType] = useState<'single' | 'all'>(transactionIdParam ? 'single' : 'all');

  // Устанавливаем значение параметра transactionId из URL
  useEffect(() => {
    if (transactionIdParam) {
      setReportType('single');
      form.setFieldsValue({ transactionId: transactionIdParam });
    }
  }, [transactionIdParam, form]);

  // Обработка формы для отчета по одной транзакции
  const handleSingleTransactionReport = async (values: any) => {
    try {
      setLoading(true);
      const { transactionId, format } = values;
      
      if (!transactionId) {
        message.error('Необходимо указать ID транзакции');
        return;
      }
      
      const blob = await transactionApi.exportTransactionHistory(
        parseInt(transactionId),
        format
      );
      
      // Создаем ссылку для скачивания
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `transaction_${transactionId}_history.${format}`;
      link.click();
      
      message.success('Отчет успешно сгенерирован');
    } catch (error) {
      console.error('Ошибка генерации отчета:', error);
      message.error('Не удалось сгенерировать отчет');
    } finally {
      setLoading(false);
    }
  };

  // Обработка формы для общего отчета
  const handleGeneralReport = async (values: any) => {
    try {
      setLoading(true);
      const { userId, status, dateRange, format } = values;
      
      let startDate: Date | undefined;
      let endDate: Date | undefined;
      
      if (dateRange && dateRange.length === 2) {
        startDate = dateRange[0].toDate();
        endDate = dateRange[1].toDate();
      }
      
      const blob = await transactionApi.generateTransactionsReport(
        userId ? parseInt(userId) : undefined,
        status,
        startDate,
        endDate,
        format
      );
      
      // Создаем ссылку для скачивания
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Формируем название файла
      const datePart = dateRange 
        ? `${startDate?.toISOString().slice(0, 10)}_to_${endDate?.toISOString().slice(0, 10)}` 
        : 'all_time';
      
      link.download = `transaction_report_${datePart}.${format}`;
      link.click();
      
      message.success('Отчет успешно сгенерирован');
    } catch (error) {
      console.error('Ошибка генерации отчета:', error);
      message.error('Не удалось сгенерировать отчет');
    } finally {
      setLoading(false);
    }
  };

  const renderSingleTransactionForm = () => (
    <Form
      layout="vertical"
      form={form}
      onFinish={handleSingleTransactionReport}
      initialValues={{ format: 'csv' }}
    >
      <Form.Item
        name="transactionId"
        label="ID транзакции"
        rules={[{ required: true, message: 'Пожалуйста, введите ID транзакции' }]}
      >
        <Input placeholder="Введите ID транзакции" />
      </Form.Item>
      
      <Form.Item
        name="format"
        label="Формат отчета"
      >
        <Select>
          <Option value="csv">CSV</Option>
          <Option value="json">JSON</Option>
        </Select>
      </Form.Item>
      
      <Form.Item>
        <Button 
          type="primary" 
          htmlType="submit" 
          icon={<DownloadOutlined />} 
          loading={loading}
        >
          Скачать отчет
        </Button>
      </Form.Item>
    </Form>
  );

  const renderGeneralReportForm = () => (
    <Form
      layout="vertical"
      form={form}
      onFinish={handleGeneralReport}
      initialValues={{ format: 'csv' }}
    >
      <Form.Item
        name="userId"
        label="ID пользователя (опционально)"
      >
        <Input placeholder="Фильтровать по пользователю" />
      </Form.Item>
      
      <Form.Item
        name="status"
        label="Статус транзакции (опционально)"
      >
        <Select allowClear placeholder="Выберите статус">
          {Object.values(TransactionStatus).map(status => (
            <Option key={status} value={status}>{status}</Option>
          ))}
        </Select>
      </Form.Item>
      
      <Form.Item
        name="dateRange"
        label="Период (опционально)"
      >
        <RangePicker style={{ width: '100%' }} />
      </Form.Item>
      
      <Form.Item
        name="format"
        label="Формат отчета"
      >
        <Select>
          <Option value="csv">CSV</Option>
          <Option value="json">JSON</Option>
        </Select>
      </Form.Item>
      
      <Form.Item>
        <Button 
          type="primary" 
          htmlType="submit" 
          icon={<DownloadOutlined />} 
          loading={loading}
        >
          Сгенерировать отчет
        </Button>
      </Form.Item>
    </Form>
  );

  return (
    <div className="transaction-reports-page">
      <Card>
        <Title level={3}>Отчеты по транзакциям</Title>
        
        <Alert 
          message="Отчеты по истории транзакций" 
          description="Здесь вы можете сгенерировать отчеты по истории транзакций в различных форматах. Отчеты содержат информацию об изменениях статуса транзакций, инициаторах изменений и причинах."
          type="info" 
          showIcon 
          className="mb-4"
        />
        
        <Space direction="vertical" className="w-full">
          <div className="flex mb-4">
            <Button 
              type={reportType === 'single' ? 'primary' : 'default'} 
              onClick={() => setReportType('single')}
              icon={<FileTextOutlined />}
              className="mr-2"
            >
              Отчет по одной транзакции
            </Button>
            <Button 
              type={reportType === 'all' ? 'primary' : 'default'} 
              onClick={() => setReportType('all')}
              icon={<FileExcelOutlined />}
            >
              Общий отчет
            </Button>
          </div>
          
          <div className="p-4 bg-gray-50 rounded-md">
            {reportType === 'single' ? (
              <>
                <Text strong>Отчет по истории конкретной транзакции</Text>
                <Divider className="my-2" />
                {renderSingleTransactionForm()}
              </>
            ) : (
              <>
                <Text strong>Общий отчет по истории транзакций</Text>
                <Divider className="my-2" />
                {renderGeneralReportForm()}
              </>
            )}
          </div>
        </Space>
      </Card>
    </div>
  );
};

export default TransactionReportsPage; 