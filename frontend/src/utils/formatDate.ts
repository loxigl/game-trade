/**
 * Форматирует дату в локализованный формат
 * 
 * @param dateString - Строка с датой или объект Date
 * @param locale - Локаль для форматирования (по умолчанию ru-RU)
 * @returns Отформатированная дата в виде строки
 */
export function formatDate(dateString: string | Date, locale: string = 'ru-RU'): string {
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
  
  const options: Intl.DateTimeFormatOptions = {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  };
  
  return date.toLocaleDateString(locale, options);
}

/**
 * Форматирует дату в относительное время (например, "3 часа назад", "2 дня назад")
 * 
 * @param dateString - Строка с датой или объект Date
 * @returns Относительное время в виде строки
 */
export function formatRelativeTime(dateString: string | Date): string {
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  
  // Преобразуем разницу в миллисекундах в минуты, часы, дни и т.д.
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);
  const diffMonths = Math.floor(diffDays / 30);
  const diffYears = Math.floor(diffDays / 365);
  
  // Возвращаем соответствующую строку в зависимости от разницы во времени
  if (diffSeconds < 60) {
    return 'только что';
  } else if (diffMinutes < 60) {
    return `${diffMinutes} ${pluralize(diffMinutes, 'минуту', 'минуты', 'минут')} назад`;
  } else if (diffHours < 24) {
    return `${diffHours} ${pluralize(diffHours, 'час', 'часа', 'часов')} назад`;
  } else if (diffDays < 30) {
    return `${diffDays} ${pluralize(diffDays, 'день', 'дня', 'дней')} назад`;
  } else if (diffMonths < 12) {
    return `${diffMonths} ${pluralize(diffMonths, 'месяц', 'месяца', 'месяцев')} назад`;
  } else {
    return `${diffYears} ${pluralize(diffYears, 'год', 'года', 'лет')} назад`;
  }
}

/**
 * Функция для правильного склонения слов в зависимости от числа
 * 
 * @param count - Число
 * @param one - Форма слова для 1 (например, "минута")
 * @param few - Форма слова для 2-4 (например, "минуты")
 * @param many - Форма слова для 5+ (например, "минут")
 * @returns Правильно склоненное слово
 */
function pluralize(count: number, one: string, few: string, many: string): string {
  if (count % 10 === 1 && count % 100 !== 11) {
    return one;
  } else if ([2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100)) {
    return few;
  } else {
    return many;
  }
} 