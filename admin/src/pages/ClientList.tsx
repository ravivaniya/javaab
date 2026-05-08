import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { listClients, type Client } from '../services/adminApi';

type FilterTab = 'all' | 'active' | 'suspended' | 'low_credit';

const PAGE_SIZE = 20;

function balanceCls(client: Client): string {
  if (!client.is_active || client.credit_balance <= 0) return 'text-red-600 font-mono font-semibold';
  if (client.credit_balance < client.credit_alert_threshold) return 'text-amber-600 font-mono font-semibold';
  return 'text-green-700 font-mono font-semibold';
}

function planBadgeCls(tier: string): string {
  const map: Record<string, string> = {
    starter: 'bg-gray-100 text-gray-700',
    growth: 'bg-blue-50 text-blue-700',
    scale: 'bg-purple-50 text-purple-700',
    enterprise: 'bg-amber-50 text-amber-700',
  };
  return map[tier] ?? 'bg-gray-100 text-gray-700';
}

export default function ClientList() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<FilterTab>('all');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const { data: allClients = [], isLoading, isError } = useQuery({
    queryKey: ['clients'],
    queryFn: () => listClients(false),
    staleTime: 30_000,
  });

  const filtered = useMemo(() => {
    let list = allClients;

    if (filter === 'active') list = list.filter((c) => c.is_active);
    else if (filter === 'suspended') list = list.filter((c) => !c.is_active);
    else if (filter === 'low_credit')
      list = list.filter(
        (c) => c.is_active && c.credit_balance > 0 && c.credit_balance < c.credit_alert_threshold,
      );

    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((c) => c.org_name.toLowerCase().includes(q));
    }

    return list;
  }, [allClients, filter, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function handleFilterChange(tab: FilterTab) {
    setFilter(tab);
    setPage(1);
  }

  function handleSearch(q: string) {
    setSearch(q);
    setPage(1);
  }

  const filterTabs: { key: FilterTab; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'active', label: 'Active' },
    { key: 'suspended', label: 'Suspended' },
    { key: 'low_credit', label: 'Low Credit' },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold text-gray-900">Clients</h1>
        <Link
          to="/clients/new"
          className="px-4 py-2 bg-gray-800 text-white text-sm rounded hover:bg-gray-700"
        >
          + New Client
        </Link>
      </div>

      {/* Filters + Search */}
      <div className="flex items-center gap-4 mb-4">
        <div className="flex border border-gray-200 rounded overflow-hidden text-sm">
          {filterTabs.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => handleFilterChange(key)}
              className={`px-3 py-1.5 ${
                filter === key
                  ? 'bg-gray-800 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <input
          type="search"
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          placeholder="Search by org name…"
          className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-gray-400 w-56"
        />
        <span className="text-sm text-gray-400 ml-auto">{filtered.length} clients</span>
      </div>

      {isLoading && <p className="text-gray-500 text-sm">Loading…</p>}
      {isError && <p className="text-red-600 text-sm">Failed to load clients.</p>}

      {!isLoading && !isError && (
        <>
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr className="text-left text-gray-500">
                  <th className="px-4 py-3 font-medium">Org Name</th>
                  <th className="px-4 py-3 font-medium">Plan</th>
                  <th className="px-4 py-3 font-medium">Balance</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Last Activity</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {paginated.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-400 text-sm">
                      No clients found.
                    </td>
                  </tr>
                )}
                {paginated.map((client: Client) => (
                  <tr
                    key={client.client_id}
                    onClick={() => navigate(`/clients/${client.client_id}`)}
                    className="hover:bg-gray-50 cursor-pointer"
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{client.org_name}</div>
                      <div className="text-xs text-gray-400">{client.contact_name}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 text-xs rounded font-medium ${planBadgeCls(client.plan_tier)}`}>
                        {client.plan_tier}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={balanceCls(client)}>
                        {client.credit_balance.toLocaleString()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 text-xs rounded font-medium ${
                          client.is_active
                            ? 'bg-green-50 text-green-700'
                            : 'bg-red-50 text-red-700'
                        }`}
                      >
                        {client.is_active ? 'Active' : 'Suspended'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {new Date(client.updated_at).toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </td>
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <Link
                        to={`/clients/${client.client_id}`}
                        className="text-gray-500 hover:text-gray-900 text-xs underline"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center gap-3 mt-4 text-sm">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 border border-gray-300 rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Prev
            </button>
            <span className="text-gray-500">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1 border border-gray-300 rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
