'use client';

import { Suspense } from 'react';
import ListingFormStepper from '../../../components/ListingFormStepper';

export default function EditListingPage({ params }: { params: { id: string } }) {
  const listingId = parseInt(params.id, 10);
  
  if (isNaN(listingId)) {
    return <div className="container mx-auto py-8">Неверный ID объявления</div>;
  }
  
  return (
    <Suspense fallback={<div className="flex justify-center py-10">Загрузка...</div>}>
      <ListingFormStepper listingId={listingId} isEdit={true} />
    </Suspense>
  );
}