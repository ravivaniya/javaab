import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import { createClient } from '../services/adminApi';
import ApiKeyModal from '../components/ApiKeyModal';

const schema = z.object({
  org_name: z.string().min(2, 'At least 2 characters'),
  contact_name: z.string().min(2, 'At least 2 characters'),
  contact_phone: z
    .string()
    .regex(/^\+?[0-9]{10,15}$/, 'Enter a valid phone number'),
  contact_email: z.string().email('Invalid email'),
  plan_tier: z.enum(['starter', 'growth', 'scale', 'enterprise']),
  rate_limit_per_minute: z.coerce.number().int().min(1).max(10000),
  rate_limit_per_day: z.coerce.number().int().min(1),
  credit_alert_threshold: z.coerce.number().int().min(0),
  whatsapp_number: z
    .string()
    .regex(/^\+?[0-9]{10,15}$/, 'Enter a valid WhatsApp number'),
  notes: z.string().max(500).optional(),
});
type FormValues = z.infer<typeof schema>;

function Field({
  label,
  error,
  hint,
  children,
}: {
  label: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-gray-400">{hint}</p>}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

const inputCls =
  'w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-gray-400';

export default function ClientCreate() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [apiKey, setApiKey] = useState<{ key: string; clientId: string } | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      plan_tier: 'starter',
      rate_limit_per_minute: 60,
      rate_limit_per_day: 50000,
      credit_alert_threshold: 2000,
    },
  });

  const mutation = useMutation({
    mutationFn: createClient,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['clients'] });
      setApiKey({ key: data.raw_api_key, clientId: data.client.client_id });
    },
  });

  function handleModalClose() {
    if (apiKey) navigate(`/clients/${apiKey.clientId}`);
  }

  return (
    <div className="max-w-xl">
      {apiKey && <ApiKeyModal apiKey={apiKey.key} onClose={handleModalClose} />}

      <div className="flex items-center gap-3 mb-6">
        <Link to="/clients" className="text-gray-400 hover:text-gray-700 text-sm">
          ← Clients
        </Link>
        <h1 className="text-xl font-semibold text-gray-900">New Client</h1>
      </div>

      <form
        onSubmit={handleSubmit((v) => mutation.mutate(v))}
        className="bg-white border border-gray-200 rounded-lg p-6 space-y-5"
      >
        <Field label="Organisation name" error={errors.org_name?.message}>
          <input type="text" {...register('org_name')} className={inputCls} />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Contact name" error={errors.contact_name?.message}>
            <input type="text" {...register('contact_name')} className={inputCls} />
          </Field>
          <Field label="Contact email" error={errors.contact_email?.message}>
            <input type="email" {...register('contact_email')} className={inputCls} />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Contact phone" error={errors.contact_phone?.message}>
            <input type="tel" {...register('contact_phone')} className={inputCls} placeholder="+91XXXXXXXXXX" />
          </Field>
          <Field
            label="WhatsApp number"
            error={errors.whatsapp_number?.message}
            hint="Used for credit alerts"
          >
            <input type="tel" {...register('whatsapp_number')} className={inputCls} placeholder="+91XXXXXXXXXX" />
          </Field>
        </div>

        <Field label="Plan tier" error={errors.plan_tier?.message}>
          <select {...register('plan_tier')} className={inputCls}>
            <option value="starter">Starter</option>
            <option value="growth">Growth</option>
            <option value="scale">Scale</option>
            <option value="enterprise">Enterprise</option>
          </select>
        </Field>

        <div className="grid grid-cols-3 gap-4">
          <Field label="Rate limit / min" error={errors.rate_limit_per_minute?.message}>
            <input type="number" {...register('rate_limit_per_minute')} className={inputCls} />
          </Field>
          <Field label="Rate limit / day" error={errors.rate_limit_per_day?.message}>
            <input type="number" {...register('rate_limit_per_day')} className={inputCls} />
          </Field>
          <Field label="Alert threshold" error={errors.credit_alert_threshold?.message} hint="Credits">
            <input type="number" {...register('credit_alert_threshold')} className={inputCls} />
          </Field>
        </div>

        <Field label="Notes" error={errors.notes?.message}>
          <textarea {...register('notes')} rows={2} className={inputCls} placeholder="Optional internal notes" />
        </Field>

        {mutation.isError && (
          <p className="text-sm text-red-600">
            {(mutation.error as { response?: { data?: { detail?: string } } })?.response?.data
              ?.detail ?? 'Failed to create client'}
          </p>
        )}

        <div className="flex gap-3 pt-1">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="px-4 py-2 bg-gray-800 text-white text-sm rounded hover:bg-gray-700 disabled:opacity-50"
          >
            {mutation.isPending ? 'Creating…' : 'Create Client'}
          </button>
          <Link
            to="/clients"
            className="px-4 py-2 border border-gray-300 text-sm rounded hover:bg-gray-50"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
