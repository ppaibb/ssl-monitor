import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export interface User {
  id: number
  email: string
  is_admin: boolean
  auth_method: string
  created_at: string
}

export interface DomainItem {
  id: number
  name: string
  domain: string
  port: number
  note: string | null
  tags?: string[]
  added_at: string
}

export interface CertResult {
  domain: string
  port: number
  days_left: number | null
  not_after: string | null
  issuer_cn: string | null
  issuer_org: string | null
  subject_cn: string | null
  san: string[] | null
  is_expired: boolean
  is_expiring_soon: boolean
  error: string | null
  checked_at: string
}

export interface Webhook {
  id: number
  name: string
  type: string
  url: string
  enabled: boolean
  threshold_days: number
  created_at: string
}

export interface DomainWebhookBinding {
  id: number
  webhook_id: number
  webhook_name: string
  webhook_type: string
  threshold_days: number | null
  effective_threshold: number
  enabled: boolean
}

export interface PublicStatusItem {
  name: string
  masked_domain: string
  port: number
  days_left: number | null
  is_expired: boolean
  is_expiring_soon: boolean
  error: string | null
  checked_at: string
  tags: string[]
}

export const api = {
  register: (email: string, password: string) =>
    http.post<{ token: string; user: User }>('/auth/register', { email, password }),

  login: (email: string, password: string) =>
    http.post<{ token: string; user: User }>('/auth/login', { email, password }),

  logout: () => http.post('/auth/logout'),

  me: () => http.get<User>('/auth/me'),

  changePassword: (old_password: string, new_password: string) =>
    http.post('/auth/change-password', { old_password, new_password }),

  getDomains: () => http.get<DomainItem[]>('/domains'),

  addDomain: (name: string, domain: string, port = 443, note?: string, tags: string[] = []) =>
    http.post<DomainItem>('/domains', { name, domain, port, note, tags }),

  updateDomain: (id: number, data: { name?: string; domain?: string; port?: number; note?: string; tags?: string[] }) =>
    http.put<DomainItem>(`/domains/${id}`, data),

  deleteDomain: (domain: string, port = 443) =>
    http.delete('/domains', { params: { domain, port } }),

  deleteBatch: (domain_ids: number[]) =>
    http.delete('/domains/batch', { data: { domain_ids } }),

  getResults: () => http.get<CertResult[]>('/domains/results'),

  checkNow: () => http.get<CertResult[]>('/domains/check'),

  checkBatch: (domain_ids: number[]) =>
    http.post<CertResult[]>('/domains/check-batch', { domain_ids }),

  checkOne: (domain: string, port = 443) =>
    http.get<CertResult>('/domains/check-one', { params: { domain, port } }),

  getHistory: () =>
    http.get<Record<string, Array<{ checked_at: string; days_left: number | null; is_expired: boolean; is_expiring_soon: boolean; error: string | null }>>>('/domains/history'),

  batchImport: (lines: string) =>
    http.post<{ added: number; skipped: number; failed: number; details: string[] }>('/domains/batch', { lines }),

  getDomainWebhooks: (domainId: number) =>
    http.get<DomainWebhookBinding[]>(`/domains/${domainId}/webhooks`),

  setDomainWebhooks: (domainId: number, body: { webhook_id: number; threshold_days?: number | null; enabled: boolean }[]) =>
    http.put(`/domains/${domainId}/webhooks`, body),

  setBatchDomainWebhooks: (domain_ids: number[], webhooks: { webhook_id: number; threshold_days?: number | null; enabled: boolean }[]) =>
    http.put('/domains/batch/webhooks', { domain_ids, webhooks }),

  getPublicStatus: () => http.get<PublicStatusItem[]>('/public/status'),

  adminUsers: () => http.get('/admin/users'),
  adminDomains: () => http.get('/admin/domains'),
  adminCheckAll: () => http.post('/admin/check-all'),

  getWebhooks: () => http.get<Webhook[]>('/webhooks'),
  createWebhook: (data: Omit<Webhook, 'id' | 'created_at'>) =>
    http.post<Webhook>('/webhooks', data),
  updateWebhook: (id: number, data: Omit<Webhook, 'id' | 'created_at'>) =>
    http.patch<Webhook>(`/webhooks/${id}`, data),
  deleteWebhook: (id: number) => http.delete(`/webhooks/${id}`),
  testWebhook: (id: number) => http.post<{ ok: boolean; error: string | null }>(`/webhooks/${id}/test`),
}
