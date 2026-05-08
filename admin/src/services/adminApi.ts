import axios from 'axios';

const api = axios.create({
  baseURL: '/admin',
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('admin_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  },
);

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface LoginPayload {
  username: string;
  password: string;
}
export interface LoginResponse {
  token: string;
  expires_at: string;
}
export const login = (payload: LoginPayload) =>
  api.post<LoginResponse>('/auth/login', payload).then((r) => r.data);

// ── Clients ───────────────────────────────────────────────────────────────────

export type PlanTier = 'starter' | 'growth' | 'scale' | 'enterprise';

export interface Client {
  client_id: string;
  org_name: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  api_key_prefix: string;
  plan_tier: PlanTier;
  credit_balance: number;
  credit_alert_threshold: number;
  is_active: boolean;
  rate_limit_per_minute: number;
  rate_limit_per_day: number;
  whatsapp_number: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClientCreatePayload {
  org_name: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  plan_tier: PlanTier;
  rate_limit_per_minute: number;
  rate_limit_per_day: number;
  credit_alert_threshold: number;
  whatsapp_number: string;
  notes?: string;
}

export interface ClientUpdatePayload {
  contact_name?: string;
  contact_phone?: string;
  contact_email?: string;
  plan_tier?: PlanTier;
  rate_limit_per_minute?: number;
  rate_limit_per_day?: number;
  credit_alert_threshold?: number;
  whatsapp_number?: string;
  notes?: string;
}

export type FeatureKey =
  | 'chat_simple'
  | 'chat_medium'
  | 'chat_complex'
  | 'chat_image'
  | 'qpg'
  | 'dpp'
  | 'embedding';

export interface FeatureStats {
  credits: number;
  tokens_input: number;
  tokens_output: number;
  count: number;
}

export interface UsageSummary {
  by_feature: Partial<Record<FeatureKey, FeatureStats>>;
  total_credits: number;
  total_tokens: number;
  daily_avg: number;
  forecast_eom: number;
}

export interface LedgerEntry {
  ledger_id: string;
  client_id: string;
  type: 'topup' | 'consumption' | 'adjustment' | 'refund';
  credits: number;
  balance_after: number;
  amount_inr: number | null;
  payment_ref: string | null;
  note: string | null;
  feature: FeatureKey | null;
  tokens_input: number | null;
  tokens_output: number | null;
  request_id: string | null;
  created_by: string;
  created_at: string;
}

export interface ClientDetailResponse {
  client: Client;
  ledger: LedgerEntry[];
  usage_summary: UsageSummary;
}

export const listClients = (active_only?: boolean) =>
  api
    .get<Client[]>('/clients', { params: active_only !== undefined ? { active_only } : {} })
    .then((r) => r.data);

export const getClient = (clientId: string) =>
  api.get<ClientDetailResponse>(`/clients/${clientId}`).then((r) => r.data);

export const createClient = (payload: ClientCreatePayload) =>
  api
    .post<{ client: Client; raw_api_key: string }>('/clients', payload)
    .then((r) => r.data);

export const updateClient = (clientId: string, payload: ClientUpdatePayload) =>
  api.put<Client>(`/clients/${clientId}`, payload).then((r) => r.data);

export const rotateKey = (clientId: string) =>
  api
    .post<{ client_id: string; new_raw_api_key: string; new_key_prefix: string }>(
      `/clients/${clientId}/rotate-key`,
    )
    .then((r) => r.data);

export const suspendClient = (clientId: string) =>
  api.post<{ client_id: string; is_active: boolean }>(`/clients/${clientId}/suspend`).then((r) => r.data);

export const reactivateClient = (clientId: string) =>
  api
    .post<{ client_id: string; is_active: boolean; credit_balance: number }>(
      `/clients/${clientId}/reactivate`,
    )
    .then((r) => r.data);

// ── Credits ───────────────────────────────────────────────────────────────────

export interface TopupPayload {
  credits: number;
  amount_inr: number;
  payment_ref: string;
  note?: string;
}
export interface TopupResponse {
  client_id: string;
  credits_added: number;
  new_balance: number;
  payment_ref: string;
}

export const topupCredits = (clientId: string, payload: TopupPayload) =>
  api.post<TopupResponse>(`/clients/${clientId}/topup`, payload).then((r) => r.data);

export interface AdjustPayload {
  credits: number;
  reason: string;
}
export interface AdjustResponse {
  client_id: string;
  credits_delta: number;
  new_balance: number;
}

export const adjustCredits = (clientId: string, payload: AdjustPayload) =>
  api.post<AdjustResponse>(`/clients/${clientId}/adjust`, payload).then((r) => r.data);

export interface LedgerResponse {
  client_id: string;
  entries: LedgerEntry[];
  count: number;
  next_before: string | null;
}

export const getLedger = (clientId: string, limit = 50, before?: string) =>
  api
    .get<LedgerResponse>(`/clients/${clientId}/ledger`, {
      params: { limit, ...(before ? { before } : {}) },
    })
    .then((r) => r.data);

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface AnalyticsOverview {
  total_clients: number;
  active_clients: number;
  total_credits_sold_30d: number;
  total_credits_consumed_30d: number;
  total_revenue_inr_30d: number;
  top_5_clients_by_consumption: {
    client_id: string;
    org_name: string;
    credits_consumed_30d: number;
  }[];
}

export const getAnalyticsOverview = () =>
  api.get<AnalyticsOverview>('/analytics/overview').then((r) => r.data);

export interface BurningFastClient {
  client_id: string;
  org_name: string;
  whatsapp_number: string;
  credit_balance: number;
  daily_avg_consumption: number;
  days_remaining: number;
}

export const getClientsBurningFast = () =>
  api.get<BurningFastClient[]>('/analytics/clients-burning-fast').then((r) => r.data);
