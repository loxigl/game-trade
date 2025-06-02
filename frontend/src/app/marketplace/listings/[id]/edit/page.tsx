'use client';

import { Suspense } from 'react';
import EditListingForm from '../../../components/EditListingForm';
import { RoleBasedContent } from '../../../../components/RoleBasedContent';

export default function EditListingPage({ params }: { params: { id: string } }) {
  const listingId = parseInt(params.id, 10);
  
  if (isNaN(listingId)) {
    return (
      <div className="container mx-auto py-8 text-center">
        <h1 className="text-2xl font-bold text-red-500">Неверный ID объявления</h1>
        <p className="mt-2 text-gray-600">Проверьте правильность ссылки</p>
      </div>
    );
  }
  
  return (
    <RoleBasedContent roles={['seller', 'admin']}>
      <Suspense fallback={
        <div className="container mx-auto py-8">
          <div className="flex justify-center items-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-lg">Загрузка...</span>
          </div>
        </div>
      }>
        <EditListingForm listingId={listingId} />
      </Suspense>
    </RoleBasedContent>
  );
}