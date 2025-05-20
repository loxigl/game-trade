'use client';

import React from 'react';
import { Card, Button, Space } from 'antd';
import { ArrowLeftOutlined, FileTextOutlined } from '@ant-design/icons';
import TransactionDetail from '../components/TransactionDetail';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

interface TransactionDetailPageProps {
  params: {
    id: string;
  };
}

export default function TransactionDetailPage({ params }: TransactionDetailPageProps) {
  const router = useRouter();
  const transactionId = parseInt(params.id, 10);
  
  if (isNaN(transactionId)) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <h1 className="text-2xl font-bold mb-4">Некорректный ID транзакции</h1>
          <Button 
            type="primary" 
            icon={<ArrowLeftOutlined />} 
            onClick={() => router.push('/transactions')}
          >
            К списку транзакций
          </Button>
        </Card>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-4">
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={() => router.push('/transactions')}
        >
          К списку транзакций
        </Button>
        
        <Space>
          <Link href={`/transactions/reports?transactionId=${transactionId}`}>
            <Button icon={<FileTextOutlined />}>
              Экспорт истории
            </Button>
          </Link>
        </Space>
      </div>
      
      <TransactionDetail transactionId={transactionId} />
    </div>
  );
} 