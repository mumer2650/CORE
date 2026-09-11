import { ShieldAlert, Check, X, Code2 } from 'lucide-react';

export default function ApprovalModal({ pendingTools, onRespond }) {
  if (!pendingTools || pendingTools.length === 0) return null;

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-[#050505]/60 backdrop-blur-sm">
      <div className="w-full max-w-sm bg-[#0A0A0B]/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.5)] overflow-hidden animate-in fade-in zoom-in-95 duration-300">
        
        {/* Header */}
        <div className="p-5 border-b border-white/5 relative overflow-hidden">
          {/* Subtle Warning Glow */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-32 bg-rose-500/10 blur-3xl pointer-events-none rounded-full"></div>
          
          <div className="flex items-center gap-3 relative z-10">
            <div className="p-2 bg-rose-500/10 rounded-xl border border-rose-500/20 shadow-[0_0_15px_rgba(244,63,94,0.15)]">
              <ShieldAlert className="w-4 h-4 text-rose-400" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white/90 tracking-wide">Approval Required</h2>
              <p className="text-[11px] text-white/50 mt-0.5">Review the requested action payload.</p>
            </div>
          </div>
        </div>

        {/* Payload Content */}
        <div className="p-5 max-h-72 overflow-y-auto space-y-4">
          {pendingTools.map((tc, idx) => (
            <div key={idx} className="bg-black/40 rounded-xl border border-white/5 p-4 shadow-inner">
              <div className="font-mono text-xs font-medium text-emerald-400 mb-3 flex items-center gap-2">
                <Code2 className="w-3.5 h-3.5" />
                {tc.name}
              </div>
              <div className="relative group">
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"></div>
                <pre className="text-[10px] text-white/60 bg-transparent overflow-x-auto leading-relaxed font-mono">
                  {JSON.stringify(tc.args, null, 2)}
                </pre>
              </div>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="p-4 border-t border-white/5 bg-white/[0.02] flex items-center justify-end gap-3">
          <button
            onClick={() => onRespond(false)}
            className="px-4 py-2 rounded-xl flex items-center gap-2 text-xs font-medium text-white/50 hover:text-white/90 hover:bg-white/5 transition-all duration-200"
          >
            <X className="w-3.5 h-3.5" /> Reject
          </button>
          <button
            onClick={() => onRespond(true)}
            className="px-5 py-2 rounded-xl flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white text-xs font-semibold shadow-[0_0_20px_rgba(16,185,129,0.2)] hover:shadow-[0_0_25px_rgba(16,185,129,0.3)] transition-all duration-300"
          >
            <Check className="w-3.5 h-3.5" /> Approve
          </button>
        </div>
      </div>
    </div>
  );
}
