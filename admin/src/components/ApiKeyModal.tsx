import { useState } from 'react';

interface Props {
  apiKey: string;
  onClose: () => void;
}

export default function ApiKeyModal({ apiKey, onClose }: Props) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg border border-gray-200 shadow-lg w-full max-w-lg p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-1">API Key Created</h2>
        <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2 mb-4">
          This key will not be shown again. Copy it now and store it securely.
        </p>

        <div className="flex items-center gap-2 mb-6">
          <code className="flex-1 bg-gray-50 border border-gray-200 rounded px-3 py-2 text-sm font-mono break-all text-gray-900">
            {apiKey}
          </code>
          <button
            onClick={handleCopy}
            className="shrink-0 px-3 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
          >
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>

        <div className="flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-800 text-white text-sm rounded hover:bg-gray-700"
          >
            I've saved the key
          </button>
        </div>
      </div>
    </div>
  );
}
