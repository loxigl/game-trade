'use client';

import { useState, useEffect } from 'react';
import ListingFormStepper from '../../../components/ListingFormStepper';
import { RoleBasedContent } from '../../../../components/RoleBasedContent';

interface EditListingClientProps {
  id: string;
}

export default function EditListingClient({ id }: EditListingClientProps) {
  const listingId = parseInt(id, 10);

  if (isNaN(listingId)) {
    return (
      <div className="container mx-auto py-8 text-center">
        <h1 className="text-2xl font-bold text-red-500">Неверный идентификатор объявления</h1>
      </div>
    );
  }

  return (
    <RoleBasedContent roles={['seller', 'admin']}>
      <div className="container mx-auto py-8">
        <ListingFormStepper listingId={listingId} isEdit={true} />
      </div>
    </RoleBasedContent>
  );
} 