'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';

interface ListingCardProps {
  id: number;
  title: string;
  price: number;
  currency: string;
  imageUrl?: string;
  createdAt: string;
  sellerName?: string;
  gameName?: string;
  categoryName?: string;
  onClick?: () => void;
}

export default function ListingCard({
  id,
  title,
  price,
  currency,
  imageUrl,
  createdAt,
  sellerName,
  gameName,
  categoryName,
  onClick
}: ListingCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  
  // Форматируем дату (например, "2 дня назад")
  const formattedDate = formatDistanceToNow(new Date(createdAt), {
    addSuffix: true,
    locale: ru
  });
  
  // Формируем URL для страницы объявления
  const listingUrl = `/marketplace/listings/${id}`;
  
  return (
    <Link 
      href={listingUrl}
      className="block"
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div 
        className={`rounded-lg overflow-hidden shadow-sm transition-all duration-200 bg-white h-full
          ${isHovered ? 'shadow-md translate-y-[-2px]' : 'shadow-sm'}`}
      >
        {/* Изображение объявления */}
        <div className="relative h-44 bg-gray-100">
          {imageUrl ? (
            <Image
              src={imageUrl}
              alt={title}
              fill
              className="object-cover"
              sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
            />
          ) : (
            <div className="flex items-center justify-center h-full bg-gray-200">
              <span className="text-gray-400">Нет изображения</span>
            </div>
          )}
          
          {/* Бейдж с названием игры */}
          {gameName && (
            <div className="absolute top-2 left-2 bg-black bg-opacity-70 text-white text-xs px-2 py-1 rounded">
              {gameName}
            </div>
          )}
        </div>
        
        {/* Информация об объявлении */}
        <div className="p-4">
          <div className="flex justify-between mb-2">
            <div className="text-lg font-bold text-gray-900 truncate">
              {title}
            </div>
          </div>
          
          <div className="flex justify-between items-end">
            <div>
              <div className="font-bold text-xl">{price} {currency}</div>
              {categoryName && (
                <div className="text-xs text-gray-500 mt-1">{categoryName}</div>
              )}
            </div>
            
            <div className="flex flex-col items-end">
              {sellerName && (
                <div className="text-xs text-gray-500">{sellerName}</div>
              )}
              <div className="text-xs text-gray-400">{formattedDate}</div>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
} 