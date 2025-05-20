import { UUID } from 'crypto';

export enum Currency {
  USD = 'USD',
  EUR = 'EUR',
  GBP = 'GBP',
  RUB = 'RUB',
  JPY = 'JPY',
  CNY = 'CNY',
}

export enum WalletStatus {
  ACTIVE = 'active',
  BLOCKED = 'blocked',
  PENDING = 'pending',
  CLOSED = 'closed',
}

export enum TransactionStatus {
  PENDING = 'pending',
  COMPLETED = 'completed',
  FAILED = 'failed',
  REFUNDED = 'refunded',
  CANCELED = 'canceled',
  ESCROW_HELD = 'escrow_held'
}

// Типы из бэкенда для кошельков
export interface WalletType {
  id: number;
  user_id: number;
  balances: Record<Currency, number>;
  status: WalletStatus;
  created_at: string;
  updated_at: string;
  is_default: boolean;
  notes?: string;
  limits?: Record<Currency, number>;
  extra_data?: Record<string, any>;
}

// Интерфейс для транзакций кошелька
export interface WalletTransactionType {
  id: number;
  wallet_id: number;
  transaction_type: string;
  amount: number;
  currency: Currency;
  status: TransactionStatus;
  created_at: string;
  metadata?: Record<string, any>;
  reference_id?: string;
}

// Запрос на создание кошелька
export interface WalletCreateRequest {
  user_id: number;
  is_default?: boolean;
  notes?: string;
  initial_balances?: Record<Currency, number>;
}

// Запрос на обновление кошелька
export interface WalletUpdateRequest {
  is_default?: boolean;
  notes?: string;
  status?: WalletStatus;
}

// Запрос на конвертацию валюты
export interface CurrencyConversionRequest {
  wallet_id: number;
  from_currency: Currency;
  to_currency: Currency;
  amount: number;
}

// Ответ по конвертации валюты
export interface CurrencyConversionResponse {
  wallet_id: number;
  from_currency: Currency;
  to_currency: Currency;
  from_amount: number;
  to_amount: number;
  exchange_rate: number;
  fee_amount: number;
  fee_currency: Currency;
  transaction_id: number;
  timestamp: string;
}

// Ответ с текущими курсами валют
export interface ExchangeRatesResponse {
  base_currency: Currency;
  rates: Record<Currency, number>;
  timestamp: string;
}

// Запрос на депозит
export interface DepositRequest {
  wallet_id: number;
  amount: number;
  currency: Currency;
  payment_method: string;
}

// Ответ для депозита
export interface DepositResponse {
  transaction_id: number;
  wallet_id: number;
  client_secret?: string;
  redirect_url?: string;
  status: TransactionStatus;
  amount: number;
  currency: Currency;
  payment_method: string;
  created_at: string;
}

// Запрос на вывод средств
export interface WithdrawalRequest {
  wallet_id: number;
  amount: number;
  currency: Currency;
  withdrawal_method: string;
  account_details: Record<string, any>;
}

// Запрос на верификацию вывода средств
export interface WithdrawalVerificationRequest {
  withdrawal_id: number;
  verification_code: string;
}

// Ответ для вывода средств
export interface WithdrawalResponse {
  id: number;
  wallet_id: number;
  amount: number;
  currency: Currency;
  status: TransactionStatus;
  created_at: string;
  withdrawal_method: string;
  verification_required: boolean;
  verification_expires_at?: string;
}

// Информация о балансе кошелька
export interface WalletBalanceResponse {
  wallet_id: number;
  balances: Record<Currency, number>;
  limits?: Record<Currency, number>;
  status: WalletStatus;
  updated_at: string;
}

// Ответ API с пагинацией для списка кошельков
export interface WalletListResponse {
  total: number;
  items: WalletType[];
  page: number;
  size: number;
  pages: number;
} 