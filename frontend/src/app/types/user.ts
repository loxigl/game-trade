export interface User {
  id: number;
  username: string;
  email: string;
  is_active?: boolean;
  created_at: string;
  updated_at?: string;
}

export interface Profile {
  id: number;
  user_id: number;
  avatar_url?: string;
  bio?: string;
  reputation_score?: number;
  is_verified_seller?: boolean;
  total_sales?: number;
  created_at: string;
  updated_at?: string;
}

export interface UserResponse extends User {
  profile?: Profile;
}

export interface ProfileResponse extends Profile {
  user?: User;
}

export interface UserListResponse {
  items: UserResponse[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface UsersQueryParams {
  ids?: number[];
  page?: number;
  page_size?: number;
} 