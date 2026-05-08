import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getLedger, type LedgerEntry } from '../services/adminApi';

const TYPE_CLS: Record<string, string> = {
  topup: 'bg-green-50 text-green-700',
  consumption: 'bg-gray-100 text-gray-600',
  adjustment: 'bg-blue-50 text-blue-700',
  refund: 'bg-teal-50 text-teal-700',
};

interface Props {
  clientId: string;
  initialEntries?: LedgerEntry[];
}

export default function LedgerTable({ clientId, initialEntries }: Props) {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [history, setHistory] = useState<string[]>([]);

  const isFirstPage = history.length === 0 && !cursor;

  const { data, isLoading } = useQuery({
    queryKey: ['ledger', clientId, cursor ?? 'first'],
    queryFn: () => getLedger(clientId, 50, cursor),
    placeholderData: isFirstPage && initialEntries
      ? { client_id: clientId, entries: initialEntries, count: initialEntries.length, next_before: initialEntries[initialEntries.length - 1]?.created_at ?? null }
      : undefined,
    staleTime: 10_000,
  });

  const entries = data?.entries ?? [];

  function goNext() {
    if (!data?.next_before) return;
    setHistory((h) => [...h, cursor ?? '']);
    setCursor(data.next_before!);
  }

  function goPrev() {
    const prev = history[history.length - 1];
    setHistory((h) => h.slice(0, -1));
    setCursor(prev === '' ? undefined : prev);
  }

  if (isLoading && !initialEntries) return <p className="text-gray-500 text-sm">Loading ledger…</p>;
  if (!entries.length) return <p className="text-gray-500 text-sm">No ledger entries yet.</p>;

  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-gray-500">
            <th className="pb-2 pr-4 font-medium">Date</th>
            <th className="pb-2 pr-4 font-medium">Type</th>
            <th className="pb-2 pr-4 font-medium text-right">Credits</th>
            <th className="pb-2 pr-4 font-medium text-right">Balance After</th>
            <th className="pb-2 pr-4 font-medium">Ref / Note</th>
            <th className="pb-2 font-medium">By</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {entries.map((e: LedgerEntry) => (
            <tr key={e.ledger_id}>
              <td className="py-2 pr-4 text-gray-500 text-xs whitespace-nowrap">
                {new Date(e.created_at).toLocaleString('en-IN', {
                  day: 'numeric',
                  month: 'short',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </td>
              <td className="py-2 pr-4">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${TYPE_CLS[e.type] ?? 'bg-gray-100 text-gray-600'}`}>
                  {e.type}
                </span>
              </td>
              <td className={`py-2 pr-4 font-mono text-right ${e.credits >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                {e.credits >= 0 ? '+' : ''}{e.credits.toLocaleString()}
              </td>
              <td className="py-2 pr-4 font-mono text-gray-700 text-right">
                {e.balance_after.toLocaleString()}
              </td>
              <td className="py-2 pr-4 text-gray-600 text-xs max-w-xs truncate">
                {e.payment_ref ? <span className="font-mono">{e.payment_ref}</span> : null}
                {e.payment_ref && e.note ? ' · ' : null}
                {e.note}
                {e.feature ? <span className="ml-1 text-gray-400">[{e.feature}]</span> : null}
              </td>
              <td className="py-2 text-gray-400 text-xs">{e.created_by}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex items-center gap-3 mt-4">
        <button
          onClick={goPrev}
          disabled={history.length === 0}
          className="px-3 py-1 text-sm border border-gray-300 rounded disabled:opacity-40 hover:bg-gray-50"
        >
          Newer
        </button>
        <button
          onClick={goNext}
          disabled={!data?.next_before}
          className="px-3 py-1 text-sm border border-gray-300 rounded disabled:opacity-40 hover:bg-gray-50"
        >
          Older
        </button>
      </div>
    </div>
  );
}
