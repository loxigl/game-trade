export interface SuccessResponse<T> {
  success: boolean;
  data: T;
  meta?: any;
}

export interface PaginationParams {
  page: number;
  limit: number;
}

export interface PaginationResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
