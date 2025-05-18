'use client';

import { Suspense } from 'react';
import ListingDetail from '../../components/ListingDetail';

interface ListingPageProps {
  params: {
    id: string;
  };
}

function ListingPageContent({ params }: ListingPageProps) {
  const listingId = parseInt(params.id, 10);
  
  if (isNaN(listingId)) {
    return (
      <div className="container mx-auto py-8">
        <div className="bg-red-100 text-red-700 p-4 rounded-md">
          Неверный идентификатор объявления
        </div>
      </div>
    );
  }
  
  return <ListingDetail listingId={listingId} />;
}

export default function ListingPage(props: ListingPageProps) {
  return (
    <Suspense fallback={<div className="flex justify-center py-10">Загрузка...</div>}>
      <ListingPageContent {...props} />
    </Suspense>
  );
} 