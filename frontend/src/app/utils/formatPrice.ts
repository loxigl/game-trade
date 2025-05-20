/**
 * Форматирует цену с учетом валюты
 * @param price Сумма 
 * @param currency Валюта (USD, EUR, RUB, и т.д.)
 * @returns Форматированная строка с ценой и символом валюты
 */
export default function formatPrice(price: number, currency: string): string {
  const formatOptions: Intl.NumberFormatOptions = {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  };

  try {
    // Пытаемся использовать Intl.NumberFormat для форматирования
    return new Intl.NumberFormat('ru-RU', formatOptions).format(price);
  } catch (error) {
    // Если не удалось форматировать с использованием Intl (например, неизвестная валюта),
    // используем простой формат с символом валюты
    let symbol;
    switch (currency) {
      case 'USD': symbol = '$'; break;
      case 'EUR': symbol = '€'; break;
      case 'RUB': symbol = '₽'; break;
      case 'GBP': symbol = '£'; break;
      case 'JPY': symbol = '¥'; break;
      default: symbol = currency;
    }
    //если цена существует, то форматируем, иначе возвращаем 0
    if (price) {
      return `${price.toFixed(2)} ${symbol}`;
    } else {
      return '0';
    }
  }
} 