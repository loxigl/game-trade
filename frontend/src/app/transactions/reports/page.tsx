'use client';

import React, { Suspense } from 'react';
import TransactionReportsPage from '../pages/TransactionReportsPage';

// Компонент-заглушка для загрузки
const Loading = () => (
  <div className="text-center py-8">
    <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]"></div>
    <p className="mt-2 text-gray-600 ">Загрузка...</p>
  </div>
);

export default function ReportsPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Отчеты по транзакциям</h1>
      <Suspense fallback={<Loading />}>
        <TransactionReportsPage />
      </Suspense>
    </div>
  );
} 