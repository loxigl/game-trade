'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { useAuth } from '../../hooks/auth';
import { useMarketplace } from '../../hooks/marketplace';
import { useImageUpload, ImageType } from '../../hooks/image-upload';

interface ListingFormStepperProps {
  listingId?: number;
  isEdit?: boolean;
}

// Интерфейс для изображения
interface UploadedImage {
  id: number | string;
  url: string;
  is_main: boolean;
  order_index: number;
  original_filename?: string;
  content_type?: string;
}

// Шаги формы создания/редактирования объявления
enum FormStep {
  GAME_SELECTION = 0,
  CATEGORY_SELECTION = 1,
  TEMPLATE_SELECTION = 2,
  ITEM_DETAILS = 3,
  ATTRIBUTES = 4,
  IMAGES_UPLOAD = 5,
  PREVIEW = 6
}

// Обновляем интерфейс Category для поддержки иерархии
interface Category {
  id: number;
  name: string;
  icon_url?: string;
  game_id: number;
  parent_id?: number | null;
  subcategories?: Category[];
  description?: string;
}

// Типы атрибутов
enum AttributeType {
  STRING = 'string',
  NUMBER = 'number',
  BOOLEAN = 'boolean',
  ENUM = 'enum',
  DATE = 'date',
  URL = 'url',
  COLOR = 'color'
}

// Общий базовый интерфейс для атрибутов
interface BaseAttribute {
  id?: number;
  name?: string;
  attribute_name?: string;
  description?: string;
  attribute_type: string;
  is_required?: boolean;
  is_filterable?: boolean;
  default_value?: string;
  options?: string | string[];
  attribute_source?: string;
  attribute_id?: number;
  template_attribute_id?: number;
  value_string?: string;
  value_number?: number;
  value_boolean?: boolean;
}

// Интерфейс для атрибута категории
interface CategoryAttribute extends BaseAttribute {
  id: number;
  category_id: number;
  name: string;
}

// Интерфейс для атрибута шаблона
interface TemplateAttribute extends BaseAttribute {
  template_attribute_id: number;
  template_id?: number;
  attribute_name: string;
}

// Интерфейс для значения атрибута в API
interface AttributeValue {
  attribute_id?: number;
  template_attribute_id?: number;
  value_string?: string;
  value_number?: number;
  value_boolean?: boolean;
}

export default function ListingFormStepper({
  listingId,
  isEdit = false,
}: {
  listingId?: number;
  isEdit?: boolean;
}) {
  // ------------------------------------------------- hooks / helpers
  const { isAuthenticated, user } = useAuth();
  const router = useRouter();
  const {
    getGames,
    getCategoriesByGame,
    getTemplatesByCategory,
    getListingById,
    createListing,
    updateListing,
    getAttributesByCategory,
    getTemplateAttributes
  } = useMarketplace();
  const imageUpload = useImageUpload();

  // ------------------------------------------------- local state
  enum FormStep {
    GAME_SELECTION,
    CATEGORY_SELECTION,
    TEMPLATE_SELECTION,
    ITEM_DETAILS,
    ATTRIBUTES,
    IMAGES_UPLOAD,
    PREVIEW,
  }

  const [currentStep, setCurrentStep] = useState<FormStep>(FormStep.GAME_SELECTION);
  const [gameId, setGameId] = useState<number | null>(null);
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [templateId, setTemplateId] = useState<number | null>(null);
  const [games, setGames] = useState<any[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [uploadedImages, setUploadedImages] = useState<UploadedImage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    price: 0,
    currency: 'USD',
    item_template_id: 0,
  });
  const [categoryAttributes, setCategoryAttributes] = useState<any[]>([]);
  const [templateAttributes, setTemplateAttributes] = useState<any[]>([]);
  const [allAttributes, setAllAttributes] = useState<any[]>([]);
  const [attributeValues, setAttributeValues] = useState<Record<string, any>>({});
  
  // Сохраняем предыдущие значения для проверки
  const prevStateRef = useRef({
    categoryId: null as number | null,
    templateId: null as number | null,
    isEdit: false,
    listingId: undefined as number | undefined,
    imagesLoaded: false,
  });

  // ------------------------------------------------- helpers
  const nextStep = () => setCurrentStep((s) => (s + 1) as FormStep);
  const prevStep = () => setCurrentStep((s) => (s - 1) as FormStep);

  // ------------------------------------------------- load listing when editing
  useEffect(() => {
    if (!isEdit || !listingId) return;
    
    // Предотвращаем повторную загрузку с теми же параметрами
    const prevState = prevStateRef.current;
    if (prevState.isEdit === isEdit && prevState.listingId === listingId) return;
    
    // Обновляем ref
    prevStateRef.current.isEdit = isEdit;
    prevStateRef.current.listingId = listingId;
    
    // Добавляем флаг, чтобы избежать гонки состояний
    let isMounted = true;
    
    (async () => {
      setIsLoading(true);
      try {
        console.log(`Загрузка данных объявления для редактирования: ${listingId}`);
        const listing = await getListingById(listingId);
        
        // Проверяем, что компонент все еще монтирован
        if (!isMounted) return;
        
        if (!listing) {
          console.error(`Объявление с ID ${listingId} не найдено`);
          return;
        }
        
        // Устанавливаем данные формы из объявления
        setFormData({
          title: listing.title,
          description: listing.description || '',
          price: listing.price,
          currency: listing.currency,
          item_template_id: listing.item_template_id,
        });
        
        // Проверяем наличие данных о категории и шаблоне
        const hasTemplate = listing.item_template !== undefined && listing.item_template !== null;
        const hasCategory = hasTemplate && listing.item_template?.category !== undefined && listing.item_template?.category !== null;
        
        if (hasTemplate) {
          setTemplateId(listing.item_template_id);
          console.log(`Установлен шаблон: ${listing.item_template?.name} (ID: ${listing.item_template_id})`);
          
          if (hasCategory && listing.item_template?.category) {
            const category = listing.item_template.category;
            setCategoryId(category.id);
            console.log(`Установлена категория: ${category.name} (ID: ${category.id})`);
            
            if (category.game_id) {
              setGameId(category.game_id);
              console.log(`Установлена игра: ID ${category.game_id}`);
            }
          }
        }
        
        // Сразу переходим к редактированию деталей объявления
        setCurrentStep(FormStep.ITEM_DETAILS);
      } catch (err) {
        if (isMounted) {
          setError('Ошибка при загрузке данных объявления');
          console.error(err);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    })();
    
    // Функция очистки для предотвращения обновления состояния размонтированного компонента
    return () => {
      isMounted = false;
    };
  }, [isEdit, listingId, getListingById]);

  // ------------------------------------------------- load games once
  useEffect(() => {
    (async () => {
      setIsLoading(true);
      try {
        setGames(await getGames());
      } catch (err) {
        setError('Ошибка при загрузке списка игр');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [getGames]);

  // ------------------------------------------------- load categories when gameId changes
  useEffect(() => {
    if (!gameId) return;
    (async () => {
      setIsLoading(true);
      try {
        const categoriesData = await getCategoriesByGame(gameId);
        setCategories(categoriesData);
      } catch (err) {
        setError('Ошибка при загрузке списка категорий');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [gameId, getCategoriesByGame]);

  // ------------------------------------------------- load templates when categoryId changes
  useEffect(() => {
    if (!categoryId) return;
    (async () => {
      setIsLoading(true);
      try {
        const templatesData = await getTemplatesByCategory(categoryId);
        setTemplates(templatesData);
        
        // Удаляем автоматический переход к шагу выбора шаблона
        // Теперь переход будет осуществляться только через кнопку "Далее"
      } catch (err) {
        setError('Ошибка при загрузке списка шаблонов');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [categoryId, getTemplatesByCategory]);

  // ------------------------------------------------- load images when editing
  useEffect(() => {
    if (!isEdit || !listingId) return;
    
    // Используем ref для отслеживания была ли уже выполнена загрузка
    const prevState = prevStateRef.current;
    if (prevState.isEdit === isEdit && prevState.listingId === listingId && prevState.imagesLoaded) {
      // Если изображения уже были загружены для этого листинга, не загружаем их повторно
      return;
    }
    
    // Флаг для предотвращения обновления размонтированного компонента
    let isMounted = true;
    
    (async () => {
      try {
        console.log(`Загрузка изображений для объявления ${listingId}`);
        const images = await imageUpload.getEntityImages(listingId, ImageType.LISTING);
        
        if (isMounted) {
          setUploadedImages(images);
          // Помечаем, что изображения для этого листинга загружены
          prevStateRef.current.imagesLoaded = true;
        }
      } catch (err) {
        console.error('Error fetching listing images', err);
      }
    })();
    
    return () => {
      isMounted = false;
    };
  }, [isEdit, listingId, imageUpload]);

  // ------------------------------------------------- load attributes when category or template changes
  useEffect(() => {
    if (!categoryId && !templateId) return;
    
    const loadAttributes = async () => {
      setIsLoading(true);
      try {
        const combinedAttributes = [];
        
        // Загружаем атрибуты для категории, если она выбрана
        if (categoryId) {
          console.log(`Загрузка атрибутов для категории ID=${categoryId}`);
          const categoryAttrs = await getAttributesByCategory(categoryId);
          setCategoryAttributes(categoryAttrs);
        
          // Преобразуем атрибуты категории для отображения
          const formattedCategoryAttrs = categoryAttrs.map(attr => ({
            ...attr,
            attribute_source: 'category'
          }));
          
          combinedAttributes.push(...formattedCategoryAttrs);
        }
        
        // Загружаем атрибуты для шаблона, если он выбран
        if (templateId) {
          console.log(`Загрузка атрибутов для шаблона ID=${templateId}`);
          const templateAttrsData = await getTemplateAttributes(templateId);
          
          // Проверяем, что мы получили массив данных
          if (Array.isArray(templateAttrsData)) {
            // Фильтруем атрибуты шаблона, чтобы избежать дублирования с атрибутами категории
            const templateAttrsOnly = templateAttrsData.filter(attr => 
              attr.attribute_source === 'template' || 
              (attr.template_attribute_id !== null && 
               !categoryAttributes.some(catAttr => catAttr.id === attr.attribute_id))
            );
            
            setTemplateAttributes(templateAttrsOnly);
            
            // Добавляем атрибуты шаблона к общему списку
            combinedAttributes.push(...templateAttrsOnly);
          } else {
            console.error('Получены некорректные данные атрибутов шаблона:', templateAttrsData);
          }
        }
        
        // Устанавливаем все атрибуты для отображения
        setAllAttributes(combinedAttributes);
        
        // Инициализируем значения атрибутов, если они еще не установлены
        const newValues = { ...attributeValues };
        
        combinedAttributes.forEach(attr => {
          const attrId = attr.attribute_id || attr.template_attribute_id || attr.id;
          if (!newValues[attrId]) {
            // Устанавливаем значение по умолчанию в зависимости от типа атрибута
            if (attr.attribute_type === 'number') {
              newValues[attrId] = attr.value_number !== null ? attr.value_number : 0;
            } else if (attr.attribute_type === 'boolean') {
              newValues[attrId] = attr.value_boolean !== null ? attr.value_boolean : false;
            } else {
              newValues[attrId] = attr.value_string || '';
            }
          }
        });
          
        setAttributeValues(newValues);
      } catch (err) {
        setError('Ошибка при загрузке атрибутов');
        console.error('Ошибка при загрузке атрибутов:', err);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadAttributes();
  }, [categoryId, templateId, getAttributesByCategory, getTemplateAttributes]);

  // ------------------------------------------------- redirect to /login if not auth
  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push('/login');
  }, [isLoading, isAuthenticated, router]);

  // ------------------------------------------------- handlers
  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'price' ? parseFloat(value) : value,
    }));
  };

  const handleImageUpload = async (files: FileList) => {
    setIsLoading(true);
    try {
      const uploaded: UploadedImage[] = [];
      for (const file of Array.from(files)) {
        const img = await imageUpload.uploadImage(file, ImageType.LISTING, listingId);
        if (img) uploaded.push(img);
      }
      setUploadedImages((prev) => [...prev, ...uploaded]);
      setSuccessMessage('Изображения успешно загружены');
    } catch {
      setError('Ошибка при загрузке изображений');
    } finally {
      setIsLoading(false);
    }
  };

  const handleImageDelete = async (id: number | string) => {
    setIsLoading(true);
    try {
      // Преобразуем id в number, если это строка
      const numericId = typeof id === 'string' ? parseInt(id) : id;
      const ok = await imageUpload.deleteImage(numericId);
      if (ok) setUploadedImages((prev) => prev.filter((img) => img.id !== id));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSetMainImage = async (id: number | string) => {
    if (!listingId) return;
    setIsLoading(true);
    try {
      // Преобразуем id в number, если это строка
      const numericId = typeof id === 'string' ? parseInt(id) : id;
      const ok = await imageUpload.setMainImage(numericId, listingId, ImageType.LISTING);
      if (ok) setUploadedImages((prev) => prev.map((img) => ({ ...img, is_main: img.id === id })));
    } finally {
      setIsLoading(false);
    }
  };

  const handleAttributeChange = (attributeId: number, value: any, type: string, source: string) => {
    // Обработка значения в зависимости от типа перед сохранением
    let processedValue: any = value;
    
    // Преобразуем значение в соответствии с типом
    if (type === 'number') {
      // Для числовых полей преобразуем в число
      processedValue = value === '' ? null : typeof value === 'string' ? parseFloat(value) : value;
    } else if (type === 'boolean') {
      // Преобразуем в булев тип
      processedValue = !!value;
    } else if (type === 'string' || type === 'enum') {
      // Для строк и перечислений убираем лишние пробелы
      processedValue = typeof value === 'string' ? value.trim() : String(value);
    }
    
    // Обновляем значение в состоянии
    setAttributeValues(prev => ({
      ...prev,
      [attributeId]: processedValue,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    // Объявляем payload за пределами блока try, чтобы иметь доступ к нему в блоке catch
    let payload: any = {
      ...formData,
    };

    try {
      // Если нет выбранного шаблона, но есть категория - добавляем категорию в запрос
      if ((!templateId || formData.item_template_id === 0) && categoryId) {
        console.log(`Создание объявления без шаблона для категории ID=${categoryId}`);
        payload = {
          ...payload,
          category_id: categoryId,
        };
        // Удаляем пустой item_template_id
        delete payload.item_template_id;
      } else if (templateId) {
        console.log(`Создание объявления с шаблоном ID=${templateId}`);
        payload.item_template_id = templateId;
      } else {
        setError('Не выбрана категория или шаблон для объявления');
        setIsLoading(false);
        return;
      }

      // Добавляем значения атрибутов, правильно форматируя их для API
      if (Object.keys(attributeValues).length > 0) {
        // Фильтруем невалидные атрибуты и добавляем значения в нужном формате
        const validAttributes = Object.keys(attributeValues)
          .filter(key => {
            // Отфильтровываем атрибуты с пустыми значениями
            const attrId = parseInt(key);
            if (isNaN(attrId) || attrId <= 0) return false;
            
            const value = attributeValues[key];
            // Проверяем, что значение не null и не undefined
            if (value === null || value === undefined) return false;
            
            // Для строковых атрибутов проверяем, что строка не пустая
            if (typeof value === 'string' && value.trim() === '') return false;
            
            // Дополнительно проверяем, что атрибут существует в списке атрибутов категории или шаблона
            const isCategoryAttr = categoryAttributes.some(attr => attr.id === attrId);
            const isTemplateAttr = templateAttributes.some(attr => attr.template_attribute_id === attrId);
            
            return isCategoryAttr || isTemplateAttr;
          })
          .map(key => {
            const attrId = parseInt(key);
            const value = attributeValues[key];
            
            // Находим тип атрибута в списке всех атрибутов
            let attrType = 'string'; // По умолчанию считаем строкой
            
            // Поиск атрибута в категории или шаблоне
            const categoryAttr = categoryAttributes.find(attr => attr.id === attrId);
            const templateAttr = templateAttributes.find(attr => attr.template_attribute_id === attrId);
            
            // Определяем тип атрибута
            if (categoryAttr) {
              attrType = categoryAttr.attribute_type;
            } else if (templateAttr) {
              attrType = templateAttr.attribute_type;
            }
            
            // Формируем значение в зависимости от типа атрибута и его принадлежности
            const attributeValue: any = {};
            
            // Определяем, к какому типу относится атрибут (категории или шаблону)
            if (categoryAttr) {
              attributeValue.attribute_id = attrId;
            } else if (templateAttr) {
              attributeValue.template_attribute_id = attrId;
            } else {
              attributeValue.attribute_id = attrId; // Для обратной совместимости
            }
            
            // Устанавливаем значение атрибута в зависимости от его типа
            if (attrType === 'number') {
              // Для числовых значений преобразуем строку в число и проверяем, что не NaN
              const numValue = typeof value === 'string' ? parseFloat(value) : value;
              if (!isNaN(numValue)) {
                attributeValue.value_number = numValue;
              }
            } else if (attrType === 'boolean') {
              // Для булевых значений преобразуем в true/false
              attributeValue.value_boolean = !!value;
            } else {
              // string, enum и другие строковые типы
              attributeValue.value_string = String(value);
            }
            
            return attributeValue;
          });

        // Убедимся, что в JSON атрибуты отправляются как массив объектов, а не как объект
        if (validAttributes.length > 0) {
          payload.attribute_values = validAttributes;
          console.log('Значения атрибутов для отправки:', payload.attribute_values);
        } else {
          // Если нет валидных атрибутов, удаляем поле из запроса
          delete payload.attribute_values;
        }
      }

      console.log('Отправка данных объявления:', payload);

      let result: any;
      if (isEdit && listingId) {
        result = await updateListing(listingId, payload);

        // Обновляем изображения, если есть
        if (uploadedImages.length > 0) {
          const listingImages = uploadedImages.filter(img => !img.id.toString().startsWith('temp_'));
          if (listingImages.length > 0) {
            // Обновляем порядок и главное изображение
            // ...
          }
        }

        setSuccessMessage('Объявление успешно обновлено!');
      } else {
        result = await createListing(payload);
        
        // Если были загружены изображения, привязываем их к созданному объявлению
        if (result?.id && uploadedImages.length > 0) {
          console.log('Привязка изображений к объявлению:', result.id);
          
          try {
            // Обрабатываем изображения последовательно, чтобы избежать гонки данных
            for (let index = 0; index < uploadedImages.length; index++) {
              const img = uploadedImages[index];
              // Получаем ID из разных форматов
              let imageId: number;
              
              if (typeof img.id === 'number') {
                imageId = img.id;
              } else if (typeof img.id === 'string') {
                // Удаляем префикс 'temp_' если он есть
                const idString = img.id.replace('temp_', '');
                imageId = parseInt(idString);
                
                if (isNaN(imageId)) {
                  console.error(`Неверный формат ID изображения: ${img.id}`);
                  continue; // Пропускаем это изображение и переходим к следующему
                }
              } else {
                console.error(`Неподдерживаемый тип ID изображения:`, img.id);
                continue;
              }
              
              // Устанавливаем первое изображение как главное
              const isMain = index === 0 || img.is_main;
              
              console.log(`Привязка изображения ${imageId} к объявлению ${result.id}, isMain: ${isMain}`);
              const linkResult = await imageUpload.linkImage(imageId, result.id, ImageType.LISTING, isMain);
              
              if (!linkResult) {
                console.error(`Ошибка при привязке изображения ${imageId} к объявлению ${result.id}`);
              }
            }
          } catch (imgError) {
            console.error('Ошибка при привязке изображений:', imgError);
          }
        }
        
        setSuccessMessage('Объявление успешно создано!');
      }

      // Переходим на страницу объявления
      if (result?.id) {
        setTimeout(() => {
          router.push(`/marketplace/listings/${result.id}`);
        }, 1500);
      }
    } catch (err) {
      console.error('Ошибка при создании/обновлении объявления:', err);
      console.error('Отправленные данные:', payload);
      
      let errorMessage = 'Произошла ошибка при сохранении объявления';
      
      // Проверяем, является ли ошибка ответом от API
      if (err instanceof Response || (err as any)?.status) {
        const status = (err as any)?.status || (err as Response).status;
        
        try {
          const errorData = await (err as Response).json();
          console.error(`Ошибка API ${status}:`, errorData);
          
          if (errorData?.detail) {
            if (typeof errorData.detail === 'string') {
              errorMessage = `Ошибка: ${errorData.detail}`;
            } else if (Array.isArray(errorData.detail)) {
              // Обработка ошибок валидации, которые часто возвращаются как массив
              const details = errorData.detail.map((e: any) => 
                e.loc && e.msg ? `${e.loc.join('.')}: ${e.msg}` : JSON.stringify(e)
              ).join('; ');
              errorMessage = `Ошибки валидации: ${details}`;
            } else {
              errorMessage = `Ошибка: ${JSON.stringify(errorData.detail)}`;
            }
          } else if (status === 422) {
            errorMessage = `Ошибка валидации данных (422): ${JSON.stringify(errorData)}`;
          }
        } catch (jsonErr) {
          console.error('Не удалось распарсить ответ ошибки:', jsonErr);
          errorMessage = `Ошибка ${status}: Не удалось получить детали ошибки`;
        }
      } else if (err instanceof Error) {
        errorMessage = err.message || 'Произошла ошибка при сохранении объявления';
      }
      
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Переход к следующему шагу
  const handleNextStep = () => {
    setCurrentStep(prev => prev + 1 as FormStep);
  };

  // Переход к предыдущему шагу
  const handlePrevStep = () => {
    setCurrentStep(prev => prev - 1 as FormStep);
  };

  // Выбор игры
  const handleGameSelect = (id: number) => {
    setGameId(id);
    setCategoryId(null);
    setTemplateId(null);
    handleNextStep();
  };

  // Модифицируем существующий handleCategorySelect для работы с иерархией
  const handleCategorySelect = (id: number) => {
    // Находим выбранную категорию
    const selectedCategory = categories.find(c => c.id === id);
    
    if (selectedCategory) {
      // Устанавливаем выбранную категорию
      setCategoryId(id);
      setTemplateId(null);
      
      console.log(`Выбрана категория: ${selectedCategory.name}`);
    } else {
      // Если категория не найдена, это ошибка
      console.error(`Категория с id=${id} не найдена`);
    }
  };

  // Выбор шаблона
  const handleTemplateSelect = (id: number) => {
    setTemplateId(id);
    setFormData(prev => ({
      ...prev,
      item_template_id: id,
    }));
    handleNextStep();
  };

  // Отображение текущего шага
  const renderStep = () => {
    switch (currentStep) {
      case FormStep.GAME_SELECTION:
        return (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Выберите игру</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {games.map(game => (
                <div
                  key={game.id}
                  onClick={() => handleGameSelect(game.id)}
                  className={`p-4 border rounded-md cursor-pointer hover:bg-gray-50 transition ${
                    gameId === game.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-center">
                    {game.logo_url && (
                      <div className="w-12 h-12 relative mr-3">
                        <Image
                          src={game.logo_url}
                          alt={game.name}
                          fill
                          className="object-contain"
                        />
                      </div>
                    )}
                    <div>
                      <h3 className="font-medium">{game.name}</h3>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      case FormStep.CATEGORY_SELECTION:
        return renderCategorySelection();

      case FormStep.TEMPLATE_SELECTION:
        return renderTemplateSelection();

      case FormStep.ITEM_DETAILS:
        return (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Информация о предмете</h2>
            <div className="space-y-4">
              <div>
                <label htmlFor="title" className="block text-sm font-medium text-gray-700">
                  Название объявления
                </label>
                <input
                  type="text"
                  id="title"
                  name="title"
                  value={formData.title}
                  onChange={handleFormChange}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                  Описание
                </label>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleFormChange}
                  rows={4}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="price" className="block text-sm font-medium text-gray-700">
                    Цена
                  </label>
                  <input
                    type="number"
                    id="price"
                    name="price"
                    value={formData.price}
                    onChange={handleFormChange}
                    min="0"
                    step="0.01"
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>

                <div>
                  <label htmlFor="currency" className="block text-sm font-medium text-gray-700">
                    Валюта
                  </label>
                  <select
                    id="currency"
                    name="currency"
                    value={formData.currency}
                    onChange={handleFormChange}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="RUB">RUB</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        );

      case FormStep.ATTRIBUTES:
        return (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Атрибуты предмета</h2>
            
            {allAttributes.length === 0 ? (
              <div className="text-center py-6 bg-gray-50 rounded-md">
                <p className="text-gray-500">У данного шаблона нет атрибутов</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Атрибуты категории */}
                {categoryAttributes.length > 0 && (
              <div className="space-y-4">
                    <h3 className="text-lg font-medium">Атрибуты категории</h3>
                    
                    {categoryAttributes.map((attr: any) => (
                      <div key={`category-${attr.id}`} className="border rounded-md p-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {attr.name} {attr.is_required && <span className="text-red-500">*</span>}
                    </label>
                    
                    {attr.description && (
                      <p className="text-xs text-gray-500 mb-2">{attr.description}</p>
                    )}
                    
                    {attr.attribute_type === 'string' && (
                      <input
                        type="text"
                        value={attributeValues[attr.id] || ''}
                            onChange={(e) => handleAttributeChange(attr.id, e.target.value, 'string', 'category')}
                        className="block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        required={attr.is_required}
                      />
                    )}
                    
                    {attr.attribute_type === 'number' && (
                      <input
                        type="number"
                        value={attributeValues[attr.id] || 0}
                            onChange={(e) => handleAttributeChange(attr.id, e.target.value, 'number', 'category')}
                        className="block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        required={attr.is_required}
                      />
                    )}
                    
                    {attr.attribute_type === 'boolean' && (
                      <div className="flex items-center">
                        <input
                          type="checkbox"
                          id={`attr-${attr.id}`}
                          checked={attributeValues[attr.id] || false}
                              onChange={(e) => handleAttributeChange(attr.id, e.target.checked, 'boolean', 'category')}
                          className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        <label htmlFor={`attr-${attr.id}`} className="ml-2 text-sm text-gray-700">
                          {attributeValues[attr.id] ? 'Да' : 'Нет'}
                        </label>
                      </div>
                    )}
                    
                    {attr.attribute_type === 'enum' && attr.options && (
                      <select
                        value={attributeValues[attr.id] || ''}
                            onChange={(e) => handleAttributeChange(attr.id, e.target.value, 'enum', 'category')}
                        className="block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        required={attr.is_required}
                      >
                        <option value="">Выберите значение</option>
                        {typeof attr.options === 'string' 
                          ? JSON.parse(attr.options).map((option: string, index: number) => (
                            <option key={index} value={option}>
                              {option}
                            </option>
                          ))
                          : Array.isArray(attr.options) && attr.options.map((option: string, index: number) => (
                            <option key={index} value={option}>
                              {option}
                            </option>
                          ))
                        }
                      </select>
                    )}
                  </div>
                ))}
                  </div>
                )}
                
                {/* Атрибуты шаблона */}
                {templateAttributes.length > 0 && (
                  <div className="space-y-4">
                    <h3 className="text-lg font-medium">Атрибуты шаблона</h3>
                    
                    {templateAttributes.map((attr: any) => {
                      const attrId = attr.template_attribute_id;
                      
                      return (
                        <div key={`template-${attrId}`} className="border border-blue-200 bg-blue-50 rounded-md p-4">
                          <label className="block text-sm font-medium text-gray-800 mb-1">
                            {attr.attribute_name} {attr.is_required && <span className="text-red-500">*</span>}
                          </label>
                          
                          {attr.description && (
                            <p className="text-xs text-gray-600 mb-2">{attr.description}</p>
                          )}
                          
                          {attr.attribute_type === 'string' && (
                            <input
                              type="text"
                              value={attributeValues[attrId] || ''}
                              onChange={(e) => handleAttributeChange(attrId, e.target.value, 'string', 'template')}
                              className="block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                              required={attr.is_required}
                            />
                          )}
                          
                          {attr.attribute_type === 'number' && (
                            <input
                              type="number"
                              value={attributeValues[attrId] || 0}
                              onChange={(e) => handleAttributeChange(attrId, e.target.value, 'number', 'template')}
                              className="block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                              required={attr.is_required}
                            />
                          )}
                          
                          {attr.attribute_type === 'boolean' && (
                            <div className="flex items-center">
                              <input
                                type="checkbox"
                                id={`attr-${attrId}`}
                                checked={attributeValues[attrId] || false}
                                onChange={(e) => handleAttributeChange(attrId, e.target.checked, 'boolean', 'template')}
                                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                              />
                              <label htmlFor={`attr-${attrId}`} className="ml-2 text-sm text-gray-700">
                                {attributeValues[attrId] ? 'Да' : 'Нет'}
                              </label>
                            </div>
                          )}
                          
                          {attr.attribute_type === 'enum' && attr.options && (
                            <select
                              value={attributeValues[attrId] || ''}
                              onChange={(e) => handleAttributeChange(attrId, e.target.value, 'enum', 'template')}
                              className="block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                              required={attr.is_required}
                            >
                              <option value="">Выберите значение</option>
                              {typeof attr.options === 'string' 
                                ? JSON.parse(attr.options).map((option: string, index: number) => (
                                  <option key={index} value={option}>
                                    {option}
                                  </option>
                                ))
                                : Array.isArray(attr.options) && attr.options.map((option: string, index: number) => (
                                  <option key={index} value={option}>
                                    {option}
                                  </option>
                                ))
                              }
                            </select>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        );

      case FormStep.IMAGES_UPLOAD:
        return (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold">Загрузка изображений</h2>

            <div className="border-2 border-dashed border-gray-300 rounded-md p-6 text-center">
              <input
                type="file"
                id="image-upload"
                multiple
                accept="image/*"
                className="hidden"
                onChange={(e) => e.target.files && handleImageUpload(e.target.files)}
              />
              <label
                htmlFor="image-upload"
                className="cursor-pointer flex flex-col items-center justify-center"
              >
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  stroke="currentColor"
                  fill="none"
                  viewBox="0 0 48 48"
                  aria-hidden="true"
                >
                  <path
                    d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <p className="mt-1 text-sm text-gray-600">
                  Перетащите файлы сюда или нажмите, чтобы выбрать файлы
                </p>
                <p className="mt-1 text-xs text-gray-500">PNG, JPG, GIF до 5MB</p>
              </label>
            </div>

            {uploadedImages.length > 0 && (
              <div className="mt-4">
                <h3 className="text-lg font-medium mb-2">Загруженные изображения</h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                  {uploadedImages.map(image => (
                    <div
                      key={image.id}
                      className={`relative border rounded-md overflow-hidden ${
                        image.is_main ? 'ring-2 ring-blue-500' : ''
                      }`}
                    >
                      <div className="w-full h-32 relative">
                        <Image
                          src={image.url || imageUpload.getImageUrl(image.id)}
                          alt=""
                          fill
                          className="object-cover"
                        />
                      </div>
                      <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-50 transition flex items-center justify-center opacity-0 hover:opacity-100">
                        <button
                          onClick={() => handleSetMainImage(image.id)}
                          className="bg-blue-500 text-white p-1 rounded-full mx-1"
                          title="Сделать главным изображением"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleImageDelete(image.id)}
                          className="bg-red-500 text-white p-1 rounded-full mx-1"
                          title="Удалить изображение"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                          </svg>
                        </button>
                      </div>
                      {image.is_main && (
                        <div className="absolute top-1 left-1 bg-blue-500 text-white text-xs px-1 rounded">
                          Главное
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      case FormStep.PREVIEW:
        return (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold">Предварительный просмотр</h2>

            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              {uploadedImages.length > 0 ? (
                <div className="aspect-w-16 aspect-h-9 bg-gray-200 relative h-64">
                  <Image
                    src={uploadedImages.find(img => img.is_main)?.url ||
                      imageUpload.getImageUrl(uploadedImages[0].id)}
                    alt=""
                    fill
                    className="object-contain"
                  />
                </div>
              ) : (
                <div className="aspect-w-16 aspect-h-9 bg-gray-200 flex items-center justify-center h-64">
                  <span className="text-gray-400">Нет изображений</span>
                </div>
              )}

              <div className="p-4">
                <h3 className="text-lg font-bold">{formData.title}</h3>
                <p className="text-2xl font-semibold mt-2">
                  {formData.price} {formData.currency}
                </p>
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-700">Описание:</h4>
                  <p className="mt-1 text-gray-600">{formData.description || 'Нет описания'}</p>
                </div>
                
                {/* Отображение атрибутов в предварительном просмотре */}
                {allAttributes.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-gray-700">Атрибуты:</h4>
                    <div className="mt-1 grid grid-cols-2 gap-2">
                      {allAttributes.map(attr => {
                        const value = attributeValues[attr.attribute_id || attr.template_attribute_id];
                        if (value === undefined || value === '') return null;
                        
                        let displayValue = value;
                        if (attr.attribute_type === 'boolean') {
                          displayValue = value ? 'Да' : 'Нет';
                        }
                        
                        return (
                          <div key={attr.attribute_id || attr.template_attribute_id} className="flex items-start">
                            <span className="text-gray-500 text-sm">{attr.name}:</span>
                            <span className="text-gray-900 text-sm ml-1">{displayValue}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  // Обновляем отображение шаблонов с возможностью пропуска
  const renderTemplateSelection = () => {
    return (
      <div className="py-6">
        <h3 className="text-xl font-bold mb-4">Выберите шаблон предмета</h3>
        
        {templates.length === 0 ? (
          <div className="mb-6">
            <div className="p-6 bg-yellow-50 border border-yellow-200 rounded-md text-center">
              <div className="flex items-center justify-center mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h4 className="text-lg font-medium text-yellow-800 mb-2">Шаблоны отсутствуют</h4>
              <p className="text-yellow-700 mb-4">
                Для выбранной категории {categories.find(c => c.id === categoryId)?.name ? `"${categories.find(c => c.id === categoryId)?.name}"` : ""} нет шаблонов предметов.
                Вы можете продолжить без шаблона и добавить все необходимые атрибуты вручную.
              </p>
              
              <button
                type="button"
                onClick={() => {
                  // Сбрасываем template_id в формдате
                  setFormData(prev => ({
                    ...prev,
                    item_template_id: 0,
                  }));
                  // Переходим к деталям предмета
                  setCurrentStep(FormStep.ITEM_DETAILS);
                }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium"
              >
                Продолжить без шаблона
              </button>
            </div>
          </div>
        ) : (
          <div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 mb-6">
              {templates.map((template) => (
                <div
                  key={template.id}
                  className={`p-4 border rounded cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-colors ${
                    templateId === template.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                  }`}
                  onClick={() => handleTemplateSelect(template.id)}
                >
                  <h4 className="font-medium">{template.name}</h4>
                  {template.description && (
                    <p className="mt-1 text-sm text-gray-500">{template.description}</p>
                  )}
                </div>
              ))}
            </div>
            
            <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-md">
              <div className="flex items-center">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-gray-600">
                  Также вы можете <button 
                    onClick={() => {
                      // Сбрасываем template_id в формдате
                      setFormData(prev => ({
                        ...prev,
                        item_template_id: 0,
                      }));
                      // Переходим к деталям предмета
                      setCurrentStep(FormStep.ITEM_DETAILS);
                    }} 
                    className="text-blue-500 hover:underline font-medium"
                  >
                    продолжить без шаблона
                  </button> и заполнить все атрибуты вручную.
                </p>
              </div>
            </div>
          </div>
        )}
        
        <div className="mt-8 flex justify-between">
          <button
            type="button"
            onClick={prevStep}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded"
          >
            Назад
          </button>
          
          {templateId && (
            <button
              type="button"
              onClick={() => setCurrentStep(FormStep.ITEM_DETAILS)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
            >
              Далее
            </button>
          )}
        </div>
      </div>
    );
  };

  // Обновляем отображение шаблонов с возможностью пропуска
  const renderCategorySelection = () => {
    // Определяем текущую категорию и путь к ней
    const currentCategory = categoryId ? categories.find(c => c.id === categoryId) : null;
    
    // Создаем путь категорий (для breadcrumbs)
    const buildCategoryPath = (startCategory: Category | null): Category[] => {
      if (!startCategory) return [];
      
      const findParent = (cat: Category): Category | null => {
        return categories.find(c => c.id === cat.parent_id) || null;
      };
      
      const path: Category[] = [startCategory];
      let current = startCategory;
      
      // Строим путь от текущей категории до корня
      while (current.parent_id) {
        const parent = findParent(current);
        if (parent) {
          path.unshift(parent);
          current = parent;
        } else {
          break;
        }
      }
      
      return path;
    };
    
    const categoryPath = currentCategory ? buildCategoryPath(currentCategory) : [];
    
    // Определяем, какие категории отображать
    let displayedCategories: Category[] = [];
    
    if (categoryId) {
      // Если выбрана категория, показываем ее подкатегории
      const selectedCategory = categories.find(c => c.id === categoryId);
      if (selectedCategory?.subcategories && selectedCategory.subcategories.length > 0) {
        displayedCategories = selectedCategory.subcategories;
      } else {
        // Если у выбранной категории нет подкатегорий, показываем соседние категории
        // (категории с тем же родителем)
        if (selectedCategory?.parent_id) {
          const parentCategory = categories.find(c => c.id === selectedCategory.parent_id);
          if (parentCategory?.subcategories) {
            displayedCategories = parentCategory.subcategories;
          } else {
            displayedCategories = categories.filter(c => c.parent_id === selectedCategory.parent_id);
          }
        } else {
          // Если у категории нет родителя (корневая), но и нет подкатегорий,
          // показываем все корневые категории
          displayedCategories = categories.filter(c => !c.parent_id);
        }
      }
    } else {
      // Если категория не выбрана, показываем корневые категории
      displayedCategories = categories.filter(c => !c.parent_id);
    }
    
    return (
      <div className="py-6">
        <h3 className="text-xl font-bold mb-4">
          {categoryId 
            ? (displayedCategories.length > 0 ? 'Выберите подкатегорию' : 'Выбранная категория') 
            : 'Выберите категорию'}
        </h3>
        
        {/* Путь категорий (хлебные крошки) */}
        {categoryPath.length > 0 && (
          <div className="flex flex-wrap items-center mb-4 bg-gray-50 p-2 rounded">
            <button 
              onClick={() => {
                // Возвращаемся к корневым категориям
                setCategoryId(null);
              }}
              className="text-blue-600 hover:underline mr-2"
            >
              Все категории
            </button>
            
            {categoryPath.map((cat, index) => (
              <div key={cat.id} className="flex items-center">
                <span className="mx-1 text-gray-400">/</span>
                {index === categoryPath.length - 1 ? (
                  <span className="font-medium text-gray-700">{cat.name}</span>
                ) : (
                  <button
                    onClick={() => setCategoryId(cat.id)}
                    className="text-blue-600 hover:underline"
                  >
                    {cat.name}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
        
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {displayedCategories.length > 0 ? (
            displayedCategories.map((category) => (
              <div
                key={category.id}
                className={`p-4 border rounded cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-colors ${
                  categoryId === category.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                }`}
                onClick={() => handleCategorySelect(category.id)}
              >
                <div className="flex items-center">
                  {category.icon_url && (
                    <div className="flex-shrink-0 mr-3">
                      <Image
                        src={category.icon_url}
                        alt={category.name}
                        width={40}
                        height={40}
                        className="object-contain"
                      />
                    </div>
                  )}
                  <div>
                    <h4 className="font-medium">{category.name}</h4>
                    {category.description && (
                      <p className="text-sm text-gray-500">{category.description}</p>
                    )}
                    {category.subcategories && category.subcategories.length > 0 && (
                      <div className="mt-1 text-xs text-blue-600">
                        {category.subcategories.length} подкатегорий
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-full text-center py-10 bg-gray-50 rounded">
              <p className="text-gray-500">В этой категории нет подкатегорий.</p>
              <button
                className="mt-2 text-blue-600 hover:underline"
                onClick={() => setCurrentStep(FormStep.TEMPLATE_SELECTION)}
              >
                Продолжить с выбранной категорией
              </button>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-6">
          {isEdit ? 'Редактирование объявления' : 'Создание нового объявления'}
        </h1>

        {/* Индикатор прогресса */}
        <div className="relative pt-1">
          <div className="flex mb-2 items-center justify-between">
            <div>
              <span className="text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full text-blue-600 bg-blue-200">
                Шаг {currentStep + 1} из {Object.keys(FormStep).length / 2}
              </span>
            </div>
            <div className="text-right">
              <span className="text-xs font-semibold inline-block text-blue-600">
                {Math.round(((currentStep + 1) / (Object.keys(FormStep).length / 2)) * 100)}%
              </span>
            </div>
          </div>
          <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-blue-200">
            <div
              style={{ width: `${((currentStep + 1) / (Object.keys(FormStep).length / 2)) * 100}%` }}
              className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-blue-500"
            ></div>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      {successMessage && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative mb-4" role="alert">
          <span className="block sm:inline">{successMessage}</span>
        </div>
      )}

      <div className="bg-white shadow-md rounded-lg p-6 mb-6">
        {renderStep()}

        <div className="mt-8 flex justify-between">
          {currentStep > 0 && (
            <button
              type="button"
              onClick={handlePrevStep}
              className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300"
              disabled={isLoading}
            >
              Назад
            </button>
          )}

          {currentStep < FormStep.PREVIEW ? (
            <button
              type="button"
              onClick={handleNextStep}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 ml-auto"
              disabled={
                isLoading ||
                (currentStep === FormStep.GAME_SELECTION && !gameId) ||
                (currentStep === FormStep.CATEGORY_SELECTION && !categoryId) ||
                (currentStep === FormStep.TEMPLATE_SELECTION && !templateId && templates.length > 0) ||
                (currentStep === FormStep.ITEM_DETAILS && (!formData.title || formData.price <= 0))
              }
            >
              {isLoading ? 'Загрузка...' : 'Далее'}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit}
              className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 ml-auto"
              disabled={isLoading}
            >
              {isLoading ? 'Сохранение...' : isEdit ? 'Сохранить изменения' : 'Опубликовать объявление'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
