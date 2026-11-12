import { api } from './client';
import type { LoginResponse, Role, User } from '../types/models';

export interface RoleCatalogItem {
  role: Role;
  label: string;
  permissions: string[];
}

export const authApi = {
  login: (email: string, password: string) =>
    api.post<LoginResponse>('/api/auth/login', { email, password }),
  me: () => api.get<User>('/api/auth/me'),
  users: () => api.get<{ items: User[] }>('/api/auth/users'),
  roles: () => api.get<{ items: RoleCatalogItem[] }>('/api/auth/roles'),
};
