# Marketplace Frontend

Фронтенд-часть маркетплейса, написанная с использованием Next.js, TypeScript и Ant Design.

## Модули

### Транзакции и Escrow-система

Система транзакций предоставляет пользователям безопасный способ совершения сделок через механизм Escrow, который временно удерживает средства до завершения сделки и выполнения условий поставки.

#### Компоненты транзакций

- **TransactionCard** - Карточка транзакции для отображения в списке
- **TransactionDetail** - Подробная информация о транзакции с возможностью выполнения действий
- **TransactionList** - Список транзакций с пагинацией и фильтрацией
- **TransactionStatusBadge** - Визуальное отображение статуса транзакции
- **TransactionInitiator** - Форма для создания новой транзакции

#### Страницы транзакций

- `/transactions` - Список транзакций пользователя с разделением на "Мои покупки" и "Мои продажи"
- `/transactions/[id]` - Детальная информация о транзакции с действиями

#### Жизненный цикл транзакции

1. **Создание** (PENDING) - Покупатель создает транзакцию, но средства еще не переведены
2. **Escrow** (ESCROW_HELD) - Средства заблокированы в Escrow
3. **Завершение** (COMPLETED) - Сделка успешно завершена, средства переведены продавцу
4. **Возврат** (REFUNDED) - Средства возвращены покупателю
5. **Спор** (DISPUTED) - Открыт спор между покупателем и продавцом
6. **Разрешение спора** (RESOLVED) - Спор разрешен администрацией
7. **Отмена** (CANCELED) - Транзакция отменена

#### API-взаимодействие

Модуль использует следующие API-вызовы:
- Создание транзакции (`createTransaction`)
- Получение транзакции (`getTransaction`)
- Получение списка транзакций (`getUserTransactions`)
- Получение доступных действий (`getTransactionActions`)
- Действия с транзакцией:
  - Перевод в Escrow (`processEscrowPayment`)
  - Завершение (`completeTransaction`)
  - Возврат средств (`refundTransaction`)
  - Открытие спора (`disputeTransaction`) 
  - Разрешение спора (`resolveDispute`)
  - Отмена (`cancelTransaction`)

#### Идемпотентность операций

Все мутирующие операции с транзакциями используют заголовок `X-Idempotency-Key` для предотвращения дублирования операций при повторных запросах.

## Запуск проекта

```bash
# Установка зависимостей
npm install

# Запуск в режиме разработки
npm run dev

# Сборка проекта
npm run build

# Запуск в production режиме
npm start
```

## Использование в других модулях

Компоненты транзакций могут быть легко интегрированы в другие части приложения:

```tsx
// Пример инициации транзакции из карточки товара
import { TransactionInitiator } from '../app/transactions/components/TransactionInitiator';

// В компоненте карточки товара
<TransactionInitiator
  buyerId={currentUserId}
  sellerId={product.userId}
  listingId={product.id}
  listingTitle={product.title}
  suggestedAmount={product.price}
  onSuccess={(transactionId) => {
    // Обработка успешного создания транзакции
  }}
/>
```

## Структура проекта

```
frontend/
├── src/
│   ├── api/              # API-клиенты
│   │   ├── client.ts     # Базовый API-клиент
│   │   └── transaction.ts # API для транзакций
│   ├── app/              # Основные компоненты приложения
│   │   ├── transactions/ # Модуль транзакций
│   │   │   ├── components/ # Компоненты транзакций
│   │   │   ├── [id]/      # Страница деталей транзакции
│   │   │   └── page.tsx   # Страница списка транзакций
│   │   └── ...
│   ├── components/       # Общие компоненты
│   └── types/            # TypeScript типы
│       └── transaction.ts # Типы для транзакций
└── ...
```

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
