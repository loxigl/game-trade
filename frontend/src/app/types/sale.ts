export enum SaleStatus {
  PENDING = "pending",
  PAYMENT_PROCESSING = "payment_processing",
  DELIVERY_PENDING = "delivery_pending",
  COMPLETED = "completed",
  CANCELED = "canceled",
  REFUNDED = "refunded",
  DISPUTED = "disputed"
}

export interface Sale {
  id: number;
  listing_id: number;
  listing_title: string | null;
  buyer_id: number;
  buyer_name: string | null;
  seller_id: number;
  seller_name: string | null;
  item_id: number;
  price: number;
  currency: string;
  status: SaleStatus;
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;
  chat_id: number | null;
  transaction_id: number | null;
  description: string | null;
  extra_data: Record<string, any> | null;
}

export interface SaleListResponse {
  items: Sale[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface SaleStatusUpdate {
  status: SaleStatus;
  reason?: string;
} 