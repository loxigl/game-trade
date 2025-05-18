'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Suspense } from 'react';
import ListingCard from '../components/ListingCard';
import { useMarketplace } from '../../hooks/marketplace';

// Добавляем функцию debounce
function useDebounce(value: any, delay: number) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

function ListingsContent() {
  const searchParamsHook = useSearchParams();
  const router = useRouter();
  const {
    getGames: marketplaceGetGames,
    getCategoriesByGame: marketplaceGetCategoriesByGame,
    searchListings: marketplaceSearchListings,
    getAttributesByCategory: marketplaceGetAttributesByCategory,
    isLoading: marketplaceIsLoading,
    error: marketplaceError,
  } = useMarketplace();
  
  // Рефы для отслеживания состояния
  const prevUrlRef = useRef<string>('');
  const isFirstLoadRef = useRef(true);
  const skipFirstRenderRef = useRef(true);
  
  const [listings, setListings] = useState<any[]>([]);
  const [games, setGames] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [categoryAttributes, setCategoryAttributes] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedGameIds, setSelectedGameIds] = useState<number[]>([]);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<number[]>([]);
  const [selectedAttributes, setSelectedAttributes] = useState<Record<string, any>>({});
  const [minPrice, setMinPrice] = useState<string>('');
  const [maxPrice, setMaxPrice] = useState<string>('');
  const [selectedCurrency, setSelectedCurrency] = useState<string>('USD');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const observer = useRef<IntersectionObserver | null>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const isLoadingMoreRef = useRef(false); // Добавляем реф для отслеживания состояния загрузки
  
  // Сохраняем предыдущие значения для сравнения
  const prevFiltersRef = useRef({
    searchQuery: '',
    selectedGameIds: [] as number[],
    selectedCategoryIds: [] as number[],
    selectedAttributes: {} as Record<string, any>,
    minPrice: '',
    maxPrice: '',
    selectedCurrency: 'USD',
    currentPage: 0
  });
  
  // Меняем обработку debounce фильтров
  const debouncedFilters = useDebounce({
    currentPage,
    selectedGameIds,
    selectedCategoryIds,
    searchQuery,
    minPrice,
    maxPrice,
    selectedCurrency,
    selectedAttributes
  }, 500);
  
  const fetchGames = useCallback(async () => {
    try {
      const gamesData = await marketplaceGetGames();
      setGames(gamesData);
    } catch (error) {
      console.error('Error fetching games:', error);
    }
  }, [marketplaceGetGames]);
  
  const fetchCategories = useCallback(async (gameId: number) => {
    try {
      const categoriesData = await marketplaceGetCategoriesByGame(gameId);
      return categoriesData;
    } catch (error) {
      console.error('Error fetching categories:', error);
      return [];
    }
  }, [marketplaceGetCategoriesByGame]);
  
  const fetchCategoryAttributes = useCallback(async (categoryId: number) => {
    try {
      const attributes = await marketplaceGetAttributesByCategory(categoryId);
      setCategoryAttributes(prev => {
        const existingAttrIds = new Set(prev.map(attr => attr.id));
        const newAttributes = attributes.filter(attr => !existingAttrIds.has(attr.id));
        return [...prev, ...newAttributes];
      });
    } catch (error) {
      console.error('Error fetching category attributes:', error);
    }
  }, [marketplaceGetAttributesByCategory]);
  
  // Оптимизируем fetchListings, уменьшаем зависимости
  const fetchListings = useCallback(async (isLoadMore = false) => {
    // Предотвращаем повторную загрузку при уже выполняющемся запросе
    if (isLoadingMoreRef.current) {
      console.log('Пропуск запроса, так как предыдущий еще выполняется');
      return;
    }
    
    // Если запрашиваем "загрузить еще", но нет больше страниц - выходим
    if (isLoadMore && !hasMore) {
      console.log('Пропуск запроса, так как больше нет страниц для загрузки');
      return;
    }
    
    // Устанавливаем состояние загрузки
    console.log(`Начинаем загрузку ${isLoadMore ? 'следующей страницы' : 'первой страницы'}`);
    setIsLoading(true);
    isLoadingMoreRef.current = true;
    setError(null);
    
    try {
      // Определяем номер страницы для запроса
      const page = isLoadMore ? currentPage + 1 : 1;
      
      // Формируем фильтры по атрибутам
      const attributeFilters = Object.entries(selectedAttributes)
        .filter(([_, value]) => value !== null && value !== undefined && value !== '')
        .map(([attrId, value]) => {
          const attr = categoryAttributes.find(a => a.id === parseInt(attrId));
          if (!attr) return null;
          
          if (attr.attribute_type === 'number') {
            return { 
              attribute_id: parseInt(attrId), 
              value_number: parseFloat(value as string) 
            };
          } else if (attr.attribute_type === 'boolean') {
            return { 
              attribute_id: parseInt(attrId), 
              value_boolean: value === 'true' || value === true 
            };
          } else {
            return { 
              attribute_id: parseInt(attrId), 
              value_string: value as string 
            };
          }
        })
        .filter(Boolean);
      
      // Параметры поиска
      const searchParamsData = {
        query: searchQuery,
        game_ids: selectedGameIds.length > 0 ? selectedGameIds : undefined,
        category_ids: selectedCategoryIds.length > 0 ? selectedCategoryIds : undefined,
        attribute_filters: attributeFilters.length > 0 ? attributeFilters : undefined,
      };
      
      // Параметры фильтрации
      const filterParamsData = {
        min_price: minPrice ? parseFloat(minPrice) : undefined,
        max_price: maxPrice ? parseFloat(maxPrice) : undefined,
        currency: selectedCurrency,
      };
      
      // Параметры пагинации
      const paginationParamsData = {
        page,
        limit: 12, // Количество элементов на странице
      };
      
      // Выполняем поиск через API
      const result = await marketplaceSearchListings(
        searchParamsData,
        filterParamsData,
        paginationParamsData,
        'created_at',
        'desc'
      );
      
      // Обновляем состояние в зависимости от типа загрузки
      if (isLoadMore) {
        setListings(prev => {
          // Создаем новый массив с уникальным ID для каждого элемента - page_id
          const itemsWithUniqueIds = result.items.map(item => ({
            ...item,
            // Добавляем уникальный идентификатор, включающий страницу и оригинальный ID
            page_id: `${page}_${item.id}`
          }));
          
          console.log(`Загружено ${result.items.length} объявлений со страницы ${page}`);
          
          // Возвращаем комбинированный массив
          return [...prev, ...itemsWithUniqueIds];
        });
      } else {
        // Для первой загрузки тоже добавляем уникальные идентификаторы
        const itemsWithUniqueIds = result.items.map(item => ({
          ...item,
          page_id: `${page}_${item.id}`
        }));
        setListings(itemsWithUniqueIds);
      }
      
      // Обновляем состояние пагинации
      // Поддерживаем оба формата: API может возвращать либо meta.total_pages, либо meta.pages
      const totalPages = result.meta.total_pages || result.meta.pages || 1;
      setCurrentPage(page);
      setTotalPages(totalPages);
      
      // Устанавливаем hasMore на основе сравнения текущей страницы с общим количеством
      const hasMorePages = page < totalPages;
      console.log(`Устанавливаем hasMore=${hasMorePages}, страница ${page} из ${totalPages}`);
      setHasMore(hasMorePages);
      
      // Обновляем предыдущие фильтры
      prevFiltersRef.current = {
        searchQuery,
        selectedGameIds: [...selectedGameIds],
        selectedCategoryIds: [...selectedCategoryIds],
        selectedAttributes: {...selectedAttributes},
        minPrice,
        maxPrice,
        selectedCurrency,
        currentPage: page
      };
      
      // Выводим в консоль информацию о пагинации для отладки
      console.log(`Загружена страница ${page}/${totalPages}, элементов: ${result.items.length}, hasMore: ${hasMorePages}`);
      console.log('Полученная мета информация:', result.meta);
      
    } catch (err) {
      console.error('Error fetching listings:', err);
      setError(err instanceof Error ? err.message : 'Произошла ошибка при загрузке объявлений');
    } finally {
      setIsLoading(false);
      isLoadingMoreRef.current = false; // Сбрасываем флаг загрузки
    }
  }, [
    marketplaceSearchListings,
    currentPage,
    selectedGameIds,
    selectedCategoryIds,
    selectedAttributes, 
    minPrice,
    maxPrice,
    selectedCurrency,
    searchQuery,
    categoryAttributes,
    hasMore
  ]);
  
  // Настройка IntersectionObserver для бесконечной прокрутки
  useEffect(() => {
    // Сначала проверяем, созданы ли уже объявления и есть ли еще страницы
    if (listings.length === 0) {
      console.log('Пропускаем создание IntersectionObserver, так как еще нет объявлений');
      return;
    }
    
    if (!hasMore) {
      console.log('IntersectionObserver не создан, так как нет больше страниц');
      return;
    }
    
    // Устанавливаем таймаут, чтобы быть уверенными, что DOM-элемент загружен
    const timer = setTimeout(() => {
      console.log('Настраиваем IntersectionObserver для бесконечной прокрутки');
      
      const options = {
        root: null,
        rootMargin: '200px', // Увеличиваем расстояние для более раннего срабатывания
        threshold: 0.1,
      };
      
      // Создаем наблюдателя
      observer.current = new IntersectionObserver((entries) => {
        const [entry] = entries;
        console.log('IntersectionObserver callback вызван:', 
          'isIntersecting:', entry.isIntersecting, 
          'hasMore:', hasMore, 
          'isLoading:', isLoading, 
          'isLoadingMoreRef:', isLoadingMoreRef.current
        );
        
        if (entry.isIntersecting && hasMore && !isLoading && !isLoadingMoreRef.current) {
          console.log('Пересечение обнаружено, загружаем еще объявления...');
          fetchListings(true);
        }
      }, options);
      
      const currentObserver = observer.current;
      const currentLoadMoreRef = loadMoreRef.current;
      
      // Наблюдаем за элементом загрузки, если он существует
      if (currentLoadMoreRef) {
        console.log('Начинаем наблюдение за элементом загрузки');
        currentObserver.observe(currentLoadMoreRef);
      } else {
        console.log('Элемент loadMoreRef не найден - DOM не готов');
      }
    }, 500); // Немного задержки, чтобы DOM успел обновиться
    
    // Отписываемся при размонтировании компонента
    return () => {
      clearTimeout(timer);
      if (observer.current) {
        console.log('Прекращаем наблюдение за элементом загрузки');
        observer.current.disconnect();
      }
    };
  }, [hasMore, isLoading, fetchListings, listings.length]);
  
  // Фиксим загрузку категорий - ключевой источник проблем
  useEffect(() => {
    // Предотвращаем повторные запросы
    if (selectedGameIds.length === 0) {
      setCategories([]);
      return;
    }
    
    // Просто отфильтруем категории по выбранным играм - это безопасная операция
    setCategories(prev => prev.filter(cat => selectedGameIds.includes(cat.game_id)));
    
    // Создаем Set для отслеживания уже загруженных игр
    const loadedGameIds = new Set(categories.map(cat => cat.game_id));
    
    // Загружаем только те игры, для которых нет категорий
    const gamesToLoad = selectedGameIds.filter(gameId => !loadedGameIds.has(gameId));
    
    // Если нет игр для загрузки, то выходим
    if (gamesToLoad.length === 0) return;
    
    // Для каждой игры, которую нужно загрузить, делаем отдельный запрос
    gamesToLoad.forEach(gameId => {
      // Используем Promise вместо обновления состояния внутри колбэка
      fetchCategories(gameId)
        .then(newCategories => {
          if (!newCategories || newCategories.length === 0) return;
          
          setCategories(current => {
            // Создаем Set с идентификаторами существующих категорий для быстрого поиска
            const existingIds = new Set(current.map(c => c.id));
            // Добавляем только те категории, которые еще не существуют
            return [...current, ...newCategories.filter(c => !existingIds.has(c.id))];
          });
        })
        .catch(err => console.error(`Error loading categories for game ${gameId}:`, err));
    });
    
    // Важно: не добавляем categories в массив зависимостей
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedGameIds, fetchCategories]);
  
  // Первоначальная загрузка объявлений
  useEffect(() => {
    if (isFirstLoadRef.current) {
      isFirstLoadRef.current = false;
      fetchListings();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  
  // Загрузка игр при монтировании
  useEffect(() => {
    fetchGames();
  }, [fetchGames]);
  
  // Обрабатываем параметры URL
  useEffect(() => {
    if (!searchParamsHook) return;
    
    const page = searchParamsHook.get('page');
    const gameIds = searchParamsHook.get('game_ids');
    const categoryIds = searchParamsHook.get('category_ids');
    const query = searchParamsHook.get('query');
    const min = searchParamsHook.get('min_price');
    const max = searchParamsHook.get('max_price');
    const currency = searchParamsHook.get('currency');
    
    const attrParamNames = Array.from(searchParamsHook.keys())
      .filter(key => key.startsWith('attr_'));
    
    const attributesFromParams: Record<string, any> = {};
    attrParamNames.forEach(paramName => {
      const attrId = paramName.replace('attr_', '');
      const value = searchParamsHook.get(paramName);
      if (value) {
        attributesFromParams[attrId] = value;
      }
    });
    
    if (page) setCurrentPage(parseInt(page, 10));
    if (gameIds) setSelectedGameIds(gameIds.split(',').map(id => parseInt(id, 10)));
    if (categoryIds) setSelectedCategoryIds(categoryIds.split(',').map(id => parseInt(id, 10)));
    if (query) setSearchQuery(query);
    if (min) setMinPrice(min);
    if (max) setMaxPrice(max);
    if (currency) setSelectedCurrency(currency);
    if (Object.keys(attributesFromParams).length > 0) {
      setSelectedAttributes(attributesFromParams);
    }
  }, [searchParamsHook]);
  
  // Загрузка атрибутов при изменении выбранных категорий
  useEffect(() => {
    if (selectedCategoryIds.length > 0) {
      selectedCategoryIds.forEach(categoryId => {
        fetchCategoryAttributes(categoryId);
      });
    } else {
      setCategoryAttributes([]);
    }
  }, [selectedCategoryIds, fetchCategoryAttributes]);
  
  // Обновление URL в ответ на изменения фильтров
  useEffect(() => {
    // Пропускаем начальный рендер
    if (skipFirstRenderRef.current) {
      skipFirstRenderRef.current = false;
      return;
    }
    
    const params = new URLSearchParams();
    if (currentPage > 1) params.set('page', currentPage.toString());
    if (selectedGameIds.length > 0) params.set('game_ids', selectedGameIds.join(','));
    if (selectedCategoryIds.length > 0) params.set('category_ids', selectedCategoryIds.join(','));
    if (searchQuery) params.set('query', searchQuery);
    if (minPrice) params.set('min_price', minPrice);
    if (maxPrice) params.set('max_price', maxPrice);
    if (selectedCurrency !== 'USD') params.set('currency', selectedCurrency);
    
    Object.entries(selectedAttributes).forEach(([attrId, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        params.set(`attr_${attrId}`, value.toString());
      }
    });
    
    const newUrl = `/marketplace/listings?${params.toString()}`;
    
    // Предотвращаем обновление URL, если он не изменился
    if (newUrl !== prevUrlRef.current) {
      prevUrlRef.current = newUrl;
      router.push(newUrl, { scroll: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedFilters]);

  const handleGameSelect = (gameId: number) => {
    const newSelectedGameIds = selectedGameIds.includes(gameId)
      ? selectedGameIds.filter(id => id !== gameId)
      : [...selectedGameIds, gameId];
    setSelectedGameIds(newSelectedGameIds);

    if (!newSelectedGameIds.includes(gameId)) {
      setCategories(prev => prev.filter(cat => cat.game_id !== gameId));
      setSelectedCategoryIds(prev => prev.filter(catId => 
        !categories.filter(c => c.game_id === gameId).map(c => c.id).includes(catId)
      ));
    }

    setCurrentPage(1);
  };
  
  const handleCategorySelect = (categoryId: number) => {
    setSelectedCategoryIds(prev => 
      prev.includes(categoryId)
        ? prev.filter(id => id !== categoryId)
        : [...prev, categoryId]
    );
    
    if (selectedCategoryIds.includes(categoryId)) {
      const categoryAttributeIds = categoryAttributes
        .filter(attr => attr.category_id === categoryId)
        .map(attr => attr.id.toString());
      
      const newSelectedAttributes = { ...selectedAttributes };
      categoryAttributeIds.forEach(attrId => {
        delete newSelectedAttributes[attrId];
      });
      
      setSelectedAttributes(newSelectedAttributes);
    }
    
    setCurrentPage(1);
  };
  
  const handleAttributeChange = (attributeId: string, value: any) => {
    setSelectedAttributes(prev => ({
      ...prev,
      [attributeId]: value
    }));
  };
  
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };
  
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    setListings([]); // Очищаем результаты перед новым поиском
    fetchListings();
  };
  
  // Обработчик изменения фильтров
  const applyFilters = () => {
    setCurrentPage(1);
    setListings([]); // Очищаем результаты перед новым поиском
    fetchListings();
  };
  
  const clearFilters = () => {
    setSelectedGameIds([]);
    setSelectedCategoryIds([]);
    setSelectedAttributes({});
    setMinPrice('');
    setMaxPrice('');
    setSelectedCurrency('USD');
    setSearchQuery('');
    setCurrentPage(1);
    setListings([]); // Очищаем результаты перед новым поиском
    fetchListings();
  };
  
  const attributesByCategory = categoryAttributes
    .filter(attr => selectedCategoryIds.includes(attr.category_id) && attr.is_filterable)
    .reduce((acc, attr) => {
      const categoryId = attr.category_id;
      if (!acc[categoryId]) {
        acc[categoryId] = [];
      }
      acc[categoryId].push(attr);
      return acc;
    }, {} as Record<number, any[]>);
    
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">Объявления</h1>
        <div className="flex justify-between items-center">
          <p className="text-gray-600">Найдите нужные игровые предметы или выставите свои на продажу</p>
          <Link href="/marketplace/listings/create" className="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition">
            Создать объявление
          </Link>
        </div>
      </div>
      
      <form onSubmit={handleSearchSubmit} className="mb-6">
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={handleSearchChange}
            placeholder="Поиск предметов..."
            className="flex-1 border border-gray-300 rounded-md p-2"
          />
          <button type="submit" className="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition">
            Поиск
          </button>
        </div>
      </form>
      
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow p-4">
            <h2 className="text-lg font-semibold mb-4">Фильтры</h2>
            
            <div className="mb-6">
              <h3 className="font-medium text-sm text-gray-700 mb-2">Игры</h3>
              <div className="space-y-2 max-h-48 overflow-y-auto pr-2">
                {games.map(game => (
                  <div key={game.id} className="flex items-center">
                    <input
                      type="checkbox"
                      id={`game-${game.id}`}
                      checked={selectedGameIds.includes(game.id)}
                      onChange={() => handleGameSelect(game.id)}
                      className="rounded text-blue-600"
                    />
                    <label htmlFor={`game-${game.id}`} className="ml-2 text-sm text-gray-700">
                      {game.name}
                    </label>
                  </div>
                ))}
              </div>
            </div>
            
            {categories.filter(cat => selectedGameIds.includes(cat.game_id)).length > 0 && (
              <div className="mb-6">
                <h3 className="font-medium text-sm text-gray-700 mb-2">Категории</h3>
                <div className="space-y-2 max-h-48 overflow-y-auto pr-2">
                  {categories
                    .filter(cat => selectedGameIds.includes(cat.game_id))
                    .map(category => (
                      <div key={category.id} className="flex items-center">
                        <input
                          type="checkbox"
                          id={`category-${category.id}`}
                          checked={selectedCategoryIds.includes(category.id)}
                          onChange={() => handleCategorySelect(category.id)}
                          className="rounded text-blue-600"
                        />
                        <label htmlFor={`category-${category.id}`} className="ml-2 text-sm text-gray-700">
                          {category.name}
                        </label>
                      </div>
                    ))}
                </div>
              </div>
            )}
            
            {Object.entries(attributesByCategory).length > 0 && (
              <div className="mb-6">
                <h3 className="font-medium text-sm text-gray-700 mb-2">Атрибуты</h3>
                <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
                  {Object.entries(attributesByCategory).map(([categoryId, attributes]) => {
                    const category = categories.find(c => c.id === parseInt(categoryId));
                    
                    return (
                      <div key={categoryId} className="border-t pt-2">
                        {category && (
                          <p className="text-xs font-medium text-gray-500 mb-2">{category.name}:</p>
                        )}
                        
                        {Array.isArray(attributes) && attributes.map((attr: any) => (
                          <div key={attr.id} className="mb-2">
                            <label className="block text-sm text-gray-700 mb-1">
                              {attr.name}
                            </label>
                            
                            {attr.attribute_type === 'string' && (
                              <input
                                type="text"
                                value={selectedAttributes[attr.id] || ''}
                                onChange={(e) => handleAttributeChange(attr.id.toString(), e.target.value)}
                                className="w-full border border-gray-300 rounded-md py-1 px-2 text-sm"
                                placeholder={`Фильтр по ${attr.name}`}
                              />
                            )}
                            
                            {attr.attribute_type === 'number' && (
                              <div className="grid grid-cols-2 gap-2">
                                <input
                                  type="number"
                                  value={selectedAttributes[`${attr.id}_min`] || ''}
                                  onChange={(e) => handleAttributeChange(`${attr.id}_min`, e.target.value)}
                                  className="w-full border border-gray-300 rounded-md py-1 px-2 text-sm"
                                  placeholder="От"
                                />
                                <input
                                  type="number"
                                  value={selectedAttributes[`${attr.id}_max`] || ''}
                                  onChange={(e) => handleAttributeChange(`${attr.id}_max`, e.target.value)}
                                  className="w-full border border-gray-300 rounded-md py-1 px-2 text-sm"
                                  placeholder="До"
                                />
                              </div>
                            )}
                            
                            {attr.attribute_type === 'boolean' && (
                              <select
                                value={selectedAttributes[attr.id] || ''}
                                onChange={(e) => handleAttributeChange(attr.id.toString(), e.target.value)}
                                className="w-full border border-gray-300 rounded-md py-1 px-2 text-sm"
                              >
                                <option value="">Все</option>
                                <option value="true">Да</option>
                                <option value="false">Нет</option>
                              </select>
                            )}
                            
                            {attr.attribute_type === 'enum' && attr.options && (
                              <select
                                value={selectedAttributes[attr.id] || ''}
                                onChange={(e) => handleAttributeChange(attr.id.toString(), e.target.value)}
                                className="w-full border border-gray-300 rounded-md py-1 px-2 text-sm"
                              >
                                <option value="">Все</option>
                                {typeof attr.options === 'string' 
                                  ? JSON.parse(attr.options).map((option: string, i: number) => (
                                    <option key={`${attr.id}-${i}`} value={option}>
                                      {option}
                                    </option>
                                  ))
                                  : Array.isArray(attr.options) && attr.options.map((option: string, i: number) => (
                                    <option key={`${attr.id}-${i}`} value={option}>
                                      {option}
                                    </option>
                                  ))
                                }
                              </select>
                            )}
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            
            <div className="mb-6">
              <h3 className="font-medium text-sm text-gray-700 mb-2">Цена</h3>
              <div className="grid grid-cols-2 gap-2 mb-2">
                <div>
                  <input
                    type="number"
                    value={minPrice}
                    onChange={(e) => setMinPrice(e.target.value)}
                    placeholder="От"
                    className="w-full border border-gray-300 rounded-md p-2 text-sm"
                  />
                </div>
                <div>
                  <input
                    type="number"
                    value={maxPrice}
                    onChange={(e) => setMaxPrice(e.target.value)}
                    placeholder="До"
                    className="w-full border border-gray-300 rounded-md p-2 text-sm"
                  />
                </div>
              </div>
              <select
                value={selectedCurrency}
                onChange={(e) => setSelectedCurrency(e.target.value)}
                className="w-full border border-gray-300 rounded-md p-2 text-sm"
              >
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="RUB">RUB</option>
              </select>
            </div>
            
            <div className="flex space-x-2">
              <button
                onClick={applyFilters}
                className="flex-1 bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition"
              >
                Применить
              </button>
              <button
                onClick={clearFilters}
                className="flex-1 bg-gray-200 text-gray-700 py-2 px-4 rounded hover:bg-gray-300 transition"
              >
                Сбросить
              </button>
            </div>
          </div>
        </div>
        
        <div className="lg:col-span-3">
          {isLoading && listings.length === 0 && (
            <div className="flex justify-center items-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          )}
          
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}
          
          {!isLoading && listings.length === 0 && (
            <div className="bg-gray-100 p-8 rounded-lg text-center">
              <h3 className="text-lg font-semibold mb-2">Объявления не найдены</h3>
              <p className="text-gray-600">
                Попробуйте изменить параметры поиска или сбросить фильтры
              </p>
            </div>
          )}
          
          {listings.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {listings.map((listing) => (
                <ListingCard
                  key={listing.page_id || `${listing.id}-${Math.random()}`}
                  id={listing.id}
                  title={listing.title}
                  price={listing.price}
                  currency={listing.currency}
                  imageUrl={listing.images?.find((img: any) => img.is_main)?.url}
                  createdAt={listing.created_at}
                  sellerName={listing.seller?.username}
                  gameName={listing.item_template?.category?.game_name}
                  categoryName={listing.item_template?.category?.name}
                />
              ))}
            </div>
          )}
          
          {/* Индикатор загрузки дополнительных элементов при прокрутке */}
          {listings.length > 0 && (
            <div 
              ref={loadMoreRef} 
              className="flex justify-center items-center py-8 mt-4 mb-8 bg-gray-50 rounded-lg"
              style={{ minHeight: '150px' }} // Увеличиваем минимальную высоту
            >
              {(isLoading || isLoadingMoreRef.current) && (
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
              )}
              {!isLoading && !isLoadingMoreRef.current && hasMore && (
                <div className="text-center">
                  <p className="text-gray-500 mb-2">Страница {currentPage} из {totalPages}</p>
                  <button 
                    onClick={() => fetchListings(true)} 
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                  >
                    Загрузить еще
                  </button>
                </div>
              )}
              {!isLoading && !isLoadingMoreRef.current && !hasMore && listings.length > 0 && (
                <p className="text-gray-500">Вы дошли до конца списка объявлений</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ListingsPage() {
  return (
    <Suspense fallback={<div className="flex justify-center py-10">Загрузка...</div>}>
      <ListingsContent />
    </Suspense>
  );
} 