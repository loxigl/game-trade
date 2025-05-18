'use client';

import { Suspense } from 'react';
import ListingFormStepper from '../../components/ListingFormStepper';

export default function CreateListingPage() {
  return (
    <Suspense fallback={<div className="flex justify-center py-10">Загрузка...</div>}>
      <ListingFormStepper />
    </Suspense>
  );
} 