export enum TransactionStatus {
  PENDING = 'PENDING',
  ESCROW_HELD = 'ESCROW_HELD',
  COMPLETED = 'COMPLETED',
  REFUNDED = 'REFUNDED',
  DISPUTED = 'DISPUTED',
  RESOLVED = 'RESOLVED',
  CANCELED = 'CANCELED'
}

export enum TransactionType {
  PURCHASE = 'PURCHASE',
  WITHDRAWAL = 'WITHDRAWAL',
  DEPOSIT = 'DEPOSIT',
  REFUND = 'REFUND',
  FEE = 'FEE'
}

export interface Transaction {
  id: number;
  buyerId: number;
  sellerId: number;
  listingId: number;
  amount: number;
  fee?: number;
  status: TransactionStatus;
  type: TransactionType;
  createdAt: string;
  updatedAt: string;
  description?: string;
  expirationDate?: string;
  disputeReason?: string;
  disputeResolution?: string;
}

export interface TransactionCreate {
  buyerId: number;
  sellerId: number;
  listingId: number;
  amount: number;
  description?: string;
  expirationDate?: string;
}

export interface TransactionUpdate {
  status?: TransactionStatus;
  disputeReason?: string;
  disputeResolution?: string;
}

export interface TransactionAction {
  action: 'complete' | 'refund' | 'dispute' | 'resolve' | 'cancel' | 'escrow';
  reason?: string;
  inFavorOfSeller?: boolean;
}

export interface TransactionHistoryItem {
  id: number;
  transactionId: number;
  previousStatus: TransactionStatus;
  newStatus: TransactionStatus;
  timestamp: string;
  initiatorId?: number;
  initiatorType?: string;
  reason?: string;
  metadata?: Record<string, any>;
}

export interface TransactionHistoryListResponse {
  items: TransactionHistoryItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface TransactionActionResponse {
  actions: string[];
}

export interface MonthlySale {
  month: string;
  sales: number;
  revenue: number;
}

export interface GameDistribution {
  game: string;
  sales: number;
  percentage: number;
}

export interface SellerStatistics {
  totalSales: number;
  totalRevenue: number;
  averagePrice: number;
  popularGame: string;
  completionRate: number;
  returnRate: number;
  pendingTransactions: number;
  monthlySales: MonthlySale[];
  gameDistribution: GameDistribution[];
}

export interface TransactionSummary {
  key: string;
  count: number;
  amount: number;
  percentage: number;
} 