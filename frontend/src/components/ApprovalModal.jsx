import { ShieldAlert, Check, X } from 'lucide-react';

export default function ApprovalModal({ pendingTools, onRespond }) {
  if (!pendingTools || pendingTools.length === 0) return null;

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-6 border-b border-border bg-rose-500/10">
          <div className="flex items-center gap-3 text-rose-500">
            <ShieldAlert className="w-6 h-6" />
            <h2 className="text-xl font-bold">Action Requires Approval</h2>
          </div>
          <p className="mt-2 text-sm text-slate-300">
            The agent wants to execute a sensitive action. Please review the payload below.
          </p>
        </div>

        <div className="p-6 max-h-96 overflow-y-auto space-y-4">
          {pendingTools.map((tc, idx) => (
            <div key={idx} className="bg-slate-900 rounded-xl border border-border p-4">
              <div className="font-mono text-sm text-primary mb-2 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
                {tc.name}
              </div>
              <pre className="text-xs text-slate-300 bg-black/50 p-3 rounded-lg overflow-x-auto">
                {JSON.stringify(tc.args, null, 2)}
              </pre>
            </div>
          ))}
        </div>

        <div className="p-4 border-t border-border bg-surface/50 flex items-center justify-end gap-3">
          <button
            onClick={() => onRespond(false)}
            className="px-4 py-2 rounded-lg flex items-center gap-2 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
          >
            <X className="w-4 h-4" /> Reject
          </button>
          <button
            onClick={() => onRespond(true)}
            className="px-6 py-2 rounded-lg flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white font-medium shadow-lg shadow-emerald-500/20 transition-all"
          >
            <Check className="w-4 h-4" /> Approve Action
          </button>
        </div>
      </div>
    </div>
  );
}
