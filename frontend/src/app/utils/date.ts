import { format, formatDistanceToNow, parseISO, isToday as isTodayFns, formatISO } from 'date-fns';
import { ru } from 'date-fns/locale';

/**
 * Преобразует строку ISO в объект Date, правильно обрабатывая UTC время
 * @param timestamp - строка с датой в формате ISO
 * @returns объект Date с корректной временной зоной
 */
export const parseUTCDate = (timestamp: string | null | undefined): Date => {
  if (!timestamp) return new Date();
  
  try {
    // Проверяем, содержит ли строка указание временной зоны (Z или +/-)
    const hasTimezone = timestamp.endsWith('Z') || 
                        /[+-]\d{2}:\d{2}$/.test(timestamp) ||
                        /[+-]\d{4}$/.test(timestamp);
    
    if (hasTimezone) {
      // Если временная зона указана, просто используем parseISO
      return parseISO(timestamp);
    } else {
      // Если временная зона не указана, считаем, что это UTC и добавляем Z
      // Но сначала проверяем, содержит ли строка миллисекунды
      const timestampWithZ = timestamp.includes('.') ? 
        timestamp.replace(/(\.\d+)$/, '$1Z') : 
        timestamp + 'Z';
      
      return parseISO(timestampWithZ);
    }
  } catch (error) {
    console.warn(`Ошибка при парсинге даты: ${timestamp}`, error);
    return new Date();
  }
};

/**
 * Форматирует дату и время для отображения в чате
 * @param timestamp - строка с датой в формате ISO
 * @returns отформатированное время (для сегодняшних сообщений) или дата и время (для более старых)
 */
export const formatChatTime = (timestamp: string | null | undefined): string => {
  if (!timestamp) return '';
  
  try {
    const date = parseUTCDate(timestamp);
    
    if (isTodayFns(date)) {
      return format(date, 'HH:mm', { locale: ru });
    } else {
      return format(date, 'dd.MM.yyyy HH:mm', { locale: ru });
    }
  } catch (error) {
    console.warn(`Ошибка форматирования времени сообщения: ${timestamp}`, error);
    return '';
  }
};

/**
 * Форматирует относительную дату (например, "5 минут назад", "вчера")
 * @param timestamp - строка с датой в формате ISO
 * @returns отформатированная относительная дата
 */
export const formatRelativeDate = (timestamp: string | null | undefined): string => {
  if (!timestamp) return '';
  
  try {
    const date = parseUTCDate(timestamp);
    
    return formatDistanceToNow(date, { 
      addSuffix: true,
      locale: ru 
    });
  } catch (error) {
    console.warn(`Ошибка форматирования относительной даты: ${timestamp}`, error);
    return '';
  }
};

/**
 * Форматирует дату в заданный формат
 * @param timestamp - строка с датой в формате ISO или объект Date
 * @param formatStr - строка формата (по умолчанию "dd.MM.yyyy")
 * @returns отформатированная дата
 */
export const formatDate = (
  timestamp: string | Date | null | undefined,
  formatStr: string = 'dd.MM.yyyy'
): string => {
  if (!timestamp) return '';
  
  try {
    const date = typeof timestamp === 'string' ? parseUTCDate(timestamp) : timestamp;
    
    // Проверка на некорректную дату
    if (isNaN(date.getTime())) {
      console.warn(`Некорректная дата: ${timestamp}`);
      return '';
    }
    
    return format(date, formatStr, { locale: ru });
  } catch (error) {
    console.warn(`Ошибка форматирования даты: ${timestamp}`, error);
    return '';
  }
};

/**
 * Проверяет, является ли дата сегодняшней
 * @param timestamp - строка с датой в формате ISO или объект Date
 * @returns true, если дата сегодняшняя
 */
export const isToday = (timestamp: string | Date | null | undefined): boolean => {
  if (!timestamp) return false;
  
  try {
    const date = typeof timestamp === 'string' ? parseUTCDate(timestamp) : timestamp;
    
    return isTodayFns(date);
  } catch (error) {
    console.warn(`Ошибка проверки даты на сегодня: ${timestamp}`, error);
    return false;
  }
};

/**
 * Форматирует дату и время транзакции
 * @param timestamp - строка с датой в формате ISO
 * @returns отформатированная дата и время транзакции
 */
export const formatTransactionTime = (timestamp: string | null | undefined): string => {
  if (!timestamp) return '';
  
  try {
    const date = parseUTCDate(timestamp);
    
    return format(date, 'dd.MM.yyyy HH:mm:ss', { locale: ru });
  } catch (error) {
    console.warn(`Ошибка форматирования времени транзакции: ${timestamp}`, error);
    return '';
  }
};

/**
 * Получает разницу между двумя датами в минутах
 * @param date1 - первая дата
 * @param date2 - вторая дата (по умолчанию - текущее время)
 * @returns разница в минутах
 */
export const getMinutesDiff = (date1: Date | string | null | undefined, date2: Date = new Date()): number => {
  if (!date1) return 0;
  
  try {
    const d1 = typeof date1 === 'string' ? parseUTCDate(date1) : date1;
    return Math.floor((date2.getTime() - d1.getTime()) / (1000 * 60));
  } catch (error) {
    console.warn(`Ошибка расчета разницы в минутах: ${date1}`, error);
    return 0;
  }
};

/**
 * Конвертирует дату в формат ISO с временной зоной
 * @param date - объект Date или строка с датой
 * @returns строка в формате ISO с временной зоной
 */
export const toISOWithTimezone = (date: Date | string | null | undefined): string => {
  if (!date) return '';
  
  try {
    const d = typeof date === 'string' ? parseUTCDate(date) : date;
    return formatISO(d);
  } catch (error) {
    console.warn(`Ошибка конвертации даты в ISO с временной зоной: ${date}`, error);
    return '';
  }
};

/**
 * Проверяет, старше ли дата указанного количества дней
 * @param date - проверяемая дата
 * @param days - количество дней
 * @returns true, если дата старше указанного количества дней
 */
export const isOlderThan = (date: Date | string | null | undefined, days: number): boolean => {
  if (!date) return false;
  
  try {
    const d = typeof date === 'string' ? parseUTCDate(date) : date;
    const now = new Date();
    const diffTime = now.getTime() - d.getTime();
    const diffDays = diffTime / (1000 * 3600 * 24);
    return diffDays > days;
  } catch (error) {
    console.warn(`Ошибка проверки, старше ли дата ${days} дней: ${date}`, error);
    return false;
  }
};

/**
 * Форматирует дату регистрации пользователя
 * Корректно обрабатывает null/undefined и обеспечивает правильное отображение UTC времени
 * @param timestamp - строка с датой в формате ISO или объект Date
 * @returns отформатированная дата в формате "dd MMMM yyyy"
 */
export const formatRegistrationDate = (
  timestamp: string | Date | null | undefined
): string => {
  if (!timestamp) return '';
  
  try {
    const date = typeof timestamp === 'string' ? parseUTCDate(timestamp) : timestamp;
    
    // Проверка на некорректную дату
    if (isNaN(date.getTime())) {
      console.warn(`Некорректная дата регистрации: ${timestamp}`);
      return '';
    }
    
    return format(date, 'dd MMMM yyyy', { locale: ru });
  } catch (error) {
    console.warn(`Ошибка форматирования даты регистрации: ${timestamp}`, error);
    return '';
  }
}; 