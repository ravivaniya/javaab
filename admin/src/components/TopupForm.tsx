import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { topupCredits } from '../services/adminApi';

const schema = z.object({
  credits: z.coerce.number().int().positive('Must be a positive integer'),
  amount_inr: z.coerce.number().int().min(0, 'Cannot be negative'),
  payment_ref: z.string().max(200).default(''),
  note: z.string().max(500).optional(),
});
type FormValues = z.infer<typeof schema>;

const PRESETS = [
  { label: 'Starter Pack', credits: 5000, amount_inr: 10000 },
  { label: 'Growth Pack', credits: 20000, amount_inr: 35000 },
  { label: 'Scale Pack', credits: 60000, amount_inr: 90000 },
  { label: 'Free Trial', credits: 1000, amount_inr: 0 },
] as const;

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

interface Props {
  clientId: string;
  onClose: () => void;
}

export default function TopupForm({ clientId, onClose }: Props) {
  const qc = useQueryClient();
  const [succeeded, setSucceeded] = useState(false);
  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      topupCredits(clientId, {
        credits: values.credits,
        amount_inr: values.amount_inr,
        payment_ref: values.payment_ref,
        note: values.note,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['client', clientId] });
      qc.invalidateQueries({ queryKey: ['clients'] });
      qc.invalidateQueries({ queryKey: ['ledger', clientId] });
      reset();
      setSucceeded(true);
    },
  });

  function applyPreset(preset: (typeof PRESETS)[number]) {
    setValue('credits', preset.credits, { shouldValidate: true });
    setValue('amount_inr', preset.amount_inr, { shouldValidate: true });
    setValue('note', `${preset.label} — ₹${preset.amount_inr.toLocaleString('en-IN')} / ${preset.credits.toLocaleString()} credits`);
  }

  if (succeeded) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-3">
          Credits added successfully. Balance and ledger have been refreshed.
        </p>
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-gray-800 text-white text-sm rounded hover:bg-gray-700"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
      {/* Presets */}
      <div>
        <p className="text-xs font-medium text-gray-500 mb-2">Quick presets</p>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => applyPreset(p)}
              className="px-3 py-1.5 text-xs border border-gray-300 rounded hover:bg-gray-50"
            >
              {p.label}
              {p.amount_inr > 0 && (
                <span className="ml-1 text-gray-400">
                  ₹{p.amount_inr.toLocaleString('en-IN')} / {p.credits.toLocaleString()} cr
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Credits" error={errors.credits?.message}>
          <input type="number" {...register('credits')} className={inputCls} placeholder="e.g. 5000" />
        </Field>
        <Field label="Amount (₹ INR)" error={errors.amount_inr?.message}>
          <input type="number" {...register('amount_inr')} className={inputCls} placeholder="e.g. 10000" />
        </Field>
      </div>

      <Field label="Payment reference" error={errors.payment_ref?.message}>
        <input
          type="text"
          {...register('payment_ref')}
          className={inputCls}
          placeholder="UTR / UPI / invoice number"
        />
      </Field>

      <Field label="Note">
        <textarea
          {...register('note')}
          rows={2}
          className={inputCls}
          placeholder="Optional note"
        />
      </Field>

      {mutation.isError && (
        <p className="text-sm text-red-600">
          {(mutation.error as { response?: { data?: { detail?: string } } })?.response?.data
            ?.detail ?? 'Top-up failed'}
        </p>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={mutation.isPending}
          className="px-4 py-2 bg-gray-800 text-white text-sm rounded hover:bg-gray-700 disabled:opacity-50"
        >
          {mutation.isPending ? 'Adding…' : 'Add Credits'}
        </button>
      </div>
    </form>
  );
}
