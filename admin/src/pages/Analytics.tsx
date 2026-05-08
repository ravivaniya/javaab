import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getAnalyticsOverview, getClientsBurningFast } from '../services/adminApi';

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-semibold text-gray-900 mt-1">
        {typeof value === 'number' ? value.toLocaleString('en-IN') : value}
      </p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function Analytics() {
  const overview = useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: getAnalyticsOverview,
    refetchInterval: 60_000,
  });

  const burning = useQuery({
    queryKey: ['analytics', 'burning-fast'],
    queryFn: getClientsBurningFast,
    refetchInterval: 60_000,
  });

  const data = overview.data;
  const burnList = burning.data ?? [];

  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900 mb-6">Analytics</h1>

      {overview.isError && <p className="text-red-600 text-sm mb-4">Failed to load analytics.</p>}

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <StatCard label="Total clients" value={data?.total_clients ?? '—'} />
        <StatCard label="Active clients" value={data?.active_clients ?? '—'} />
        <StatCard
          label="Credits sold (30d)"
          value={data?.total_credits_sold_30d ?? '—'}
        />
        <StatCard
          label="Credits consumed (30d)"
          value={data?.total_credits_consumed_30d ?? '—'}
        />
        <StatCard
          label="Revenue (30d)"
          value={data ? `₹${data.total_revenue_inr_30d.toLocaleString('en-IN')}` : '—'}
        />
      </div>

      {/* Top 5 clients */}
      <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6">
        <h2 className="text-base font-medium text-gray-900 mb-4">Top 5 clients by consumption (30d)</h2>
        {!data || data.top_5_clients_by_consumption.length === 0 ? (
          <p className="text-sm text-gray-400">No data yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-200">
                <th className="pb-2 pr-4 font-medium">Organisation</th>
                <th className="pb-2 font-medium text-right">Credits consumed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.top_5_clients_by_consumption.map((c) => (
                <tr key={c.client_id}>
                  <td className="py-2 pr-4">
                    <Link
                      to={`/clients/${c.client_id}`}
                      className="text-gray-800 hover:underline"
                    >
                      {c.org_name}
                    </Link>
                  </td>
                  <td className="py-2 font-mono text-gray-700 text-right">
                    {c.credits_consumed_30d.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Burning fast */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <h2 className="text-base font-medium text-gray-900 mb-1">
          Clients running low
          {burnList.length > 0 && (
            <span className="ml-2 px-2 py-0.5 text-xs bg-red-50 text-red-700 rounded font-normal">
              {burnList.length} at risk
            </span>
          )}
        </h2>
        <p className="text-xs text-gray-400 mb-4">Projected to run out in &lt; 7 days based on 7-day avg.</p>

        {burning.isLoading && <p className="text-sm text-gray-400">Loading…</p>}
        {burning.isError && <p className="text-sm text-red-600">Failed to load burn data.</p>}

        {!burning.isLoading && burnList.length === 0 && (
          <p className="text-sm text-gray-400">No clients at risk right now.</p>
        )}

        {burnList.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-200">
                <th className="pb-2 pr-4 font-medium">Organisation</th>
                <th className="pb-2 pr-4 font-medium text-right">Balance</th>
                <th className="pb-2 pr-4 font-medium text-right">Avg / day</th>
                <th className="pb-2 pr-4 font-medium text-right">Days left</th>
                <th className="pb-2 font-medium">WhatsApp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {burnList.map((c) => (
                <tr key={c.client_id}>
                  <td className="py-2 pr-4">
                    <Link to={`/clients/${c.client_id}`} className="text-gray-800 hover:underline">
                      {c.org_name}
                    </Link>
                  </td>
                  <td className="py-2 pr-4 font-mono text-gray-700 text-right">
                    {c.credit_balance.toLocaleString()}
                  </td>
                  <td className="py-2 pr-4 font-mono text-gray-500 text-right">
                    {c.daily_avg_consumption.toFixed(1)}
                  </td>
                  <td className="py-2 pr-4 text-right">
                    <span
                      className={`font-semibold ${
                        c.days_remaining < 2
                          ? 'text-red-600'
                          : c.days_remaining < 4
                          ? 'text-amber-600'
                          : 'text-gray-800'
                      }`}
                    >
                      {c.days_remaining.toFixed(1)}d
                    </span>
                  </td>
                  <td className="py-2 font-mono text-xs text-gray-600">
                    {c.whatsapp_number}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
