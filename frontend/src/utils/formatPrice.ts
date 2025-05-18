/**
 * Форматирует цену с символом валюты
 * 
 * @param price - Значение цены
 * @param currency - Код валюты (USD, EUR, RUB и т.д.)
 * @returns Отформатированная цена с символом валюты
 */
export default function formatPrice(price?: number, currency: string = 'USD'): string {
  if (price === undefined || price === null) {
    return 'Цена не указана';
  }
  
  const formatter = new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });
  
  return formatter.format(price);
} 