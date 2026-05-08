import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  getClient,
  updateClient,
  suspendClient,
  reactivateClient,
  rotateKey,
  type Client,
  type FeatureKey,
  type UsageSummary,
  type LedgerEntry,
} from '../services/adminApi';
import TopupForm from '../components/TopupForm';
import AdjustForm from '../components/AdjustForm';
import ConfirmDialog from '../components/ConfirmDialog';
import ApiKeyModal from '../components/ApiKeyModal';
import LedgerTable from '../components/LedgerTable';

// ── Edit card ─────────────────────────────────────────────────────────────────

const editSchema = z.object({
  contact_name: z.string().min(2),
  contact_phone: z.string().regex(/^\+?[0-9]{10,15}$/),
  contact_email: z.string().email(),
  plan_tier: z.enum(['starter', 'growth', 'scale', 'enterprise']),
  whatsapp_number: z.string().regex(/^\+?[0-9]{10,15}$/),
  notes: z.string().max(500).optional(),
});
type EditValues = z.infer<typeof editSchema>;

const settingsSchema = z.object({
  rate_limit_per_minute: z.coerce.number().int().min(1),
  rate_limit_per_day: z.coerce.number().int().min(1),
  credit_alert_threshold: z.coerce.number().int().min(0),
});
type SettingsValues = z.infer<typeof settingsSchema>;

const inputCls =
  'w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-gray-400';

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

// ── Balance colour ─────────────────────────────────────────────────────────────

function balanceColour(client: Client): string {
  if (!client.is_active || client.credit_balance <= 0) return 'text-red-600';
  if (client.credit_balance < client.credit_alert_threshold) return 'text-amber-600';
  return 'text-green-700';
}

// ── Usage tab ─────────────────────────────────────────────────────────────────

const FEATURE_LABELS: Record<FeatureKey, string> = {
  chat_simple: 'Chat (Simple)',
  chat_medium: 'Chat (Medium)',
  chat_complex: 'Chat (Complex)',
  chat_image: 'Chat (Image)',
  qpg: 'Question Paper Gen',
  dpp: 'DPP',
  embedding: 'Embedding',
};

function UsageTab({ usage }: { usage: UsageSummary }) {
  const rows = Object.entries(usage.by_feature) as [FeatureKey, { credits: number; tokens_input: number; tokens_output: number; count: number }][];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total credits', value: usage.total_credits.toLocaleString() },
          { label: 'Total tokens', value: usage.total_tokens.toLocaleString() },
          { label: 'Daily avg', value: `${usage.daily_avg.toFixed(1)} cr/day` },
          { label: 'EOM forecast', value: `+${usage.forecast_eom.toLocaleString()} cr` },
        ].map(({ label, value }) => (
          <div key={label} className="bg-gray-50 border border-gray-200 rounded p-3">
            <p className="text-xs text-gray-500">{label}</p>
            <p className="text-base font-semibold text-gray-900 mt-0.5">{value}</p>
          </div>
        ))}
      </div>

      {rows.length === 0 ? (
        <p className="text-sm text-gray-400">No usage in the last 30 days.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-200">
              <th className="pb-2 pr-4 font-medium">Feature</th>
              <th className="pb-2 pr-4 font-medium text-right">Requests</th>
              <th className="pb-2 pr-4 font-medium text-right">Credits</th>
              <th className="pb-2 pr-4 font-medium text-right">Tokens in</th>
              <th className="pb-2 font-medium text-right">Tokens out</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map(([feature, stats]) => (
              <tr key={feature}>
                <td className="py-2 pr-4 text-gray-800">{FEATURE_LABELS[feature] ?? feature}</td>
                <td className="py-2 pr-4 font-mono text-gray-700 text-right">{stats.count.toLocaleString()}</td>
                <td className="py-2 pr-4 font-mono text-gray-700 text-right">{stats.credits.toLocaleString()}</td>
                <td className="py-2 pr-4 font-mono text-gray-700 text-right">{stats.tokens_input.toLocaleString()}</td>
                <td className="py-2 font-mono text-gray-700 text-right">{stats.tokens_output.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ── Inline ledger from detail response ────────────────────────────────────────

function InlineLedger({ entries, clientId }: { entries: LedgerEntry[]; clientId: string }) {
  return <LedgerTable clientId={clientId} initialEntries={entries} />;
}

// ── Main page ─────────────────────────────────────────────────────────────────

type TabKey = 'ledger' | 'usage' | 'settings';

export default function ClientDetail() {
  const { client_id } = useParams<{ client_id: string }>();
  const qc = useQueryClient();

  const [activeTab, setActiveTab] = useState<TabKey>('ledger');
  const [showTopup, setShowTopup] = useState(false);
  const [showAdjust, setShowAdjust] = useState(false);
  const [confirmSuspend, setConfirmSuspend] = useState(false);
  const [confirmRotate, setConfirmRotate] = useState(false);
  const [rotatedKey, setRotatedKey] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['client', client_id],
    queryFn: () => getClient(client_id!),
    enabled: !!client_id,
  });

  const client = data?.client;

  // Edit info form
  const editForm = useForm<EditValues>({
    resolver: zodResolver(editSchema),
    values: client
      ? {
          contact_name: client.contact_name,
          contact_phone: client.contact_phone,
          contact_email: client.contact_email,
          plan_tier: client.plan_tier,
          whatsapp_number: client.whatsapp_number,
          notes: client.notes ?? '',
        }
      : undefined,
  });

  // Settings form
  const settingsForm = useForm<SettingsValues>({
    resolver: zodResolver(settingsSchema),
    values: client
      ? {
          rate_limit_per_minute: client.rate_limit_per_minute,
          rate_limit_per_day: client.rate_limit_per_day,
          credit_alert_threshold: client.credit_alert_threshold,
        }
      : undefined,
  });

  const updateMutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateClient>[1]) =>
      updateClient(client_id!, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['client', client_id] });
      setEditMode(false);
    },
  });

  const settingsMutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateClient>[1]) =>
      updateClient(client_id!, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['client', client_id] });
    },
  });

  const suspendMutation = useMutation({
    mutationFn: () =>
      client?.is_active ? suspendClient(client_id!) : reactivateClient(client_id!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['client', client_id] });
      qc.invalidateQueries({ queryKey: ['clients'] });
      setConfirmSuspend(false);
    },
  });

  const rotateMutation = useMutation({
    mutationFn: () => rotateKey(client_id!),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['client', client_id] });
      setConfirmRotate(false);
      setRotatedKey(res.new_raw_api_key);
    },
  });

  if (isLoading) return <p className="text-gray-500 text-sm">Loading…</p>;
  if (isError || !client) return <p className="text-red-600 text-sm">Client not found.</p>;

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'ledger', label: 'Ledger' },
    { key: 'usage', label: '30-Day Usage' },
    { key: 'settings', label: 'Settings' },
  ];

  return (
    <div className="max-w-4xl space-y-6">
      {/* Modals */}
      {showTopup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg border border-gray-200 shadow-lg w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-gray-900">Add Credits</h2>
              <button onClick={() => setShowTopup(false)} className="text-gray-400 hover:text-gray-700 text-lg leading-none">×</button>
            </div>
            <TopupForm clientId={client_id!} onClose={() => setShowTopup(false)} />
          </div>
        </div>
      )}
      {showAdjust && (
        <AdjustForm clientId={client_id!} onClose={() => setShowAdjust(false)} />
      )}
      {confirmSuspend && (
        <ConfirmDialog
          title={client.is_active ? 'Suspend Client' : 'Reactivate Client'}
          message={
            client.is_active
              ? `Suspend ${client.org_name}? Their API key will stop working immediately.`
              : `Reactivate ${client.org_name}? Requires balance > 0.`
          }
          confirmLabel={client.is_active ? 'Suspend' : 'Reactivate'}
          danger={client.is_active}
          onConfirm={() => suspendMutation.mutate()}
          onCancel={() => setConfirmSuspend(false)}
        />
      )}
      {confirmRotate && (
        <ConfirmDialog
          title="Rotate API Key"
          message={`Generate a new API key for ${client.org_name}? The existing key will stop working immediately.`}
          confirmLabel="Rotate Key"
          danger
          onConfirm={() => rotateMutation.mutate()}
          onCancel={() => setConfirmRotate(false)}
        />
      )}
      {rotatedKey && (
        <ApiKeyModal apiKey={rotatedKey} onClose={() => setRotatedKey(null)} />
      )}

      {/* Breadcrumb */}
      <div>
        <Link to="/clients" className="text-gray-400 hover:text-gray-700 text-sm">
          ← Clients
        </Link>
      </div>

      {/* ── Info card ─────────────────────────────────────────────────────── */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">{client.org_name}</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {client.api_key_prefix}••••••••
              <span className="ml-3 text-xs text-gray-400">Created {new Date(client.created_at).toLocaleDateString('en-IN')}</span>
            </p>
          </div>
          <button
            onClick={() => setEditMode((v) => !v)}
            className="text-sm text-gray-500 hover:text-gray-900 border border-gray-300 rounded px-3 py-1"
          >
            {editMode ? 'Cancel' : 'Edit'}
          </button>
        </div>

        {editMode ? (
          <form
            onSubmit={editForm.handleSubmit((v) => updateMutation.mutate(v))}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-4">
              <Field label="Contact name" error={editForm.formState.errors.contact_name?.message}>
                <input {...editForm.register('contact_name')} className={inputCls} />
              </Field>
              <Field label="Contact email" error={editForm.formState.errors.contact_email?.message}>
                <input {...editForm.register('contact_email')} className={inputCls} />
              </Field>
              <Field label="Contact phone" error={editForm.formState.errors.contact_phone?.message}>
                <input {...editForm.register('contact_phone')} className={inputCls} />
              </Field>
              <Field label="WhatsApp number" error={editForm.formState.errors.whatsapp_number?.message}>
                <input {...editForm.register('whatsapp_number')} className={inputCls} />
              </Field>
              <Field label="Plan tier" error={editForm.formState.errors.plan_tier?.message}>
                <select {...editForm.register('plan_tier')} className={inputCls}>
                  <option value="starter">Starter</option>
                  <option value="growth">Growth</option>
                  <option value="scale">Scale</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </Field>
            </div>
            <Field label="Notes">
              <textarea {...editForm.register('notes')} rows={2} className={inputCls} />
            </Field>
            {updateMutation.isError && (
              <p className="text-sm text-red-600">Failed to save changes.</p>
            )}
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={updateMutation.isPending}
                className="px-4 py-2 bg-gray-800 text-white text-sm rounded hover:bg-gray-700 disabled:opacity-50"
              >
                {updateMutation.isPending ? 'Saving…' : 'Save Changes'}
              </button>
            </div>
          </form>
        ) : (
          <div className="grid grid-cols-3 gap-4 text-sm">
            {[
              ['Contact', client.contact_name],
              ['Email', client.contact_email],
              ['Phone', client.contact_phone],
              ['WhatsApp', client.whatsapp_number],
              ['Plan', client.plan_tier],
              ['Notes', client.notes ?? '—'],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-gray-400 font-medium text-xs">{label}</dt>
                <dd className="mt-0.5 text-gray-800">{value}</dd>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Balance + actions ─────────────────────────────────────────────── */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-sm text-gray-500 mb-1">Credit Balance</p>
            <p className={`text-4xl font-bold font-mono ${balanceColour(client)}`}>
              {client.credit_balance.toLocaleString()}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Alert threshold: {client.credit_alert_threshold.toLocaleString()} credits
            </p>
          </div>

          <div className="flex flex-wrap gap-2 justify-end">
            <button
              onClick={() => setShowTopup(true)}
              className="px-3 py-1.5 bg-gray-800 text-white text-sm rounded hover:bg-gray-700"
            >
              Add Credits
            </button>
            <button
              onClick={() => setShowAdjust(true)}
              className="px-3 py-1.5 border border-gray-300 text-sm rounded hover:bg-gray-50"
            >
              Manual Adjustment
            </button>
            <button
              onClick={() => setConfirmRotate(true)}
              className="px-3 py-1.5 border border-gray-300 text-sm rounded hover:bg-gray-50"
            >
              Rotate API Key
            </button>
            <button
              onClick={() => setConfirmSuspend(true)}
              disabled={suspendMutation.isPending}
              className={`px-3 py-1.5 text-sm rounded border disabled:opacity-50 ${
                client.is_active
                  ? 'border-red-300 text-red-600 hover:bg-red-50'
                  : 'border-green-300 text-green-600 hover:bg-green-50'
              }`}
            >
              {client.is_active ? 'Suspend' : 'Reactivate'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Tabs ──────────────────────────────────────────────────────────── */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="flex border-b border-gray-200">
          {tabs.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-5 py-3 text-sm font-medium border-b-2 -mb-px ${
                activeTab === key
                  ? 'border-gray-800 text-gray-900'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="p-5">
          {activeTab === 'ledger' && (
            <InlineLedger entries={data.ledger} clientId={client_id!} />
          )}
          {activeTab === 'usage' && <UsageTab usage={data.usage_summary} />}
          {activeTab === 'settings' && (
            <form
              onSubmit={settingsForm.handleSubmit((v) => settingsMutation.mutate(v))}
              className="space-y-4 max-w-sm"
            >
              <Field
                label="Rate limit per minute"
                error={settingsForm.formState.errors.rate_limit_per_minute?.message}
              >
                <input
                  type="number"
                  {...settingsForm.register('rate_limit_per_minute')}
                  className={inputCls}
                />
              </Field>
              <Field
                label="Rate limit per day"
                error={settingsForm.formState.errors.rate_limit_per_day?.message}
              >
                <input
                  type="number"
                  {...settingsForm.register('rate_limit_per_day')}
                  className={inputCls}
                />
              </Field>
              <Field
                label="Credit alert threshold"
                error={settingsForm.formState.errors.credit_alert_threshold?.message}
              >
                <input
                  type="number"
                  {...settingsForm.register('credit_alert_threshold')}
                  className={inputCls}
                />
              </Field>

              {settingsMutation.isError && (
                <p className="text-sm text-red-600">Failed to save settings.</p>
              )}
              {settingsMutation.isSuccess && (
                <p className="text-sm text-green-600">Settings saved.</p>
              )}

              <button
                type="submit"
                disabled={settingsMutation.isPending}
                className="px-4 py-2 bg-gray-800 text-white text-sm rounded hover:bg-gray-700 disabled:opacity-50"
              >
                {settingsMutation.isPending ? 'Saving…' : 'Save Settings'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
