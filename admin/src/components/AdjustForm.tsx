import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { adjustCredits } from '../services/adminApi';

const schema = z.object({
  credits: z.coerce
    .number()
    .int('Must be a whole number')
    .refine((v) => v !== 0, 'Cannot be zero'),
  reason: z.string().min(3, 'At least 3 characters').max(500),
});
type FormValues = z.infer<typeof schema>;

const inputCls =
  'w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-gray-400';

interface Props {
  clientId: string;
  onClose: () => void;
}

export default function AdjustForm({ clientId, onClose }: Props) {
  const qc = useQueryClient();
  const [succeeded, setSucceeded] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      adjustCredits(clientId, { credits: values.credits, reason: values.reason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['client', clientId] });
      qc.invalidateQueries({ queryKey: ['clients'] });
      qc.invalidateQueries({ queryKey: ['ledger', clientId] });
      setSucceeded(true);
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg border border-gray-200 shadow-lg w-full max-w-md p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">Manual Adjustment</h2>

        {succeeded ? (
          <div className="space-y-4">
            <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-3">
              Adjustment applied. Balance and ledger have been refreshed.
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
        ) : (
          <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Credits (positive to add, negative to deduct)
              </label>
              <input
                type="number"
                {...register('credits')}
                className={inputCls}
                placeholder="e.g. -500 or 1000"
              />
              {errors.credits && (
                <p className="mt-1 text-xs text-red-600">{errors.credits.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Reason</label>
              <textarea
                {...register('reason')}
                rows={3}
                className={inputCls}
                placeholder="e.g. Refund for downtime on 2026-05-01"
              />
              {errors.reason && (
                <p className="mt-1 text-xs text-red-600">{errors.reason.message}</p>
              )}
            </div>

            {mutation.isError && (
              <p className="text-sm text-red-600">
                {(mutation.error as { response?: { data?: { detail?: string } } })?.response?.data
                  ?.detail ?? 'Adjustment failed'}
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
                {mutation.isPending ? 'Saving…' : 'Apply Adjustment'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
