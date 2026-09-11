import { useState, useEffect } from 'react';
import { GitBranch, Blocks, CheckCircle2, Unplug, Loader2 } from 'lucide-react';

export default function MCPSidebar() {
  const [status, setStatus] = useState('idle');
  const [connections, setConnections] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchConnections = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const res = await fetch('http://127.0.0.1:8000/api/mcp/connections', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setConnections(data.connections || []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConnections();

    const params = new URLSearchParams(window.location.search);
    if (params.get('mcp_connected') === 'true') {
      setStatus('success');
      window.history.replaceState({}, document.title, window.location.pathname);
      setTimeout(() => setStatus('idle'), 4000);
    }
  }, []);

  const handleGithubConnect = () => {
    const token = localStorage.getItem('token');
    if (!token) return;
    window.location.href = `http://127.0.0.1:8000/api/oauth/github/login?token=${token}`;
  };

  const handleToggle = async (name) => {
    const token = localStorage.getItem('token');
    if (!token) return;
    // Optimistic update
    setConnections(prev => prev.map(c => c.name === name ? { ...c, disabled: !c.disabled } : c));
    try {
      await fetch(`http://127.0.0.1:8000/api/mcp/connections/${encodeURIComponent(name)}/toggle`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}` }
      });
    } catch (err) {
      console.error(err);
      fetchConnections(); // revert on fail
    }
  };

  const handleDisconnect = async (name) => {
    const token = localStorage.getItem('token');
    if (!token) return;
    // Optimistic update
    setConnections(prev => prev.filter(c => c.name !== name));
    try {
      await fetch(`http://127.0.0.1:8000/api/mcp/connections/${encodeURIComponent(name)}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
    } catch (err) {
      console.error(err);
      fetchConnections();
    }
  };

  const githubConnection = connections.find(c => c.name === 'GitHub (OAuth)');

  return (
    <aside className="w-80 bg-[#0A0A0B]/95 backdrop-blur-2xl border-l border-white/5 flex flex-col hidden lg:flex relative overflow-hidden">
      {/* Premium Glow Overlay */}
      <div className="absolute top-0 left-0 w-full h-64 bg-violet-600/10 rounded-full blur-[100px] pointer-events-none -translate-y-1/2"></div>
      
      <div className="h-16 flex items-center px-6 border-b border-white/5 relative z-10">
        <h2 className="font-bold flex items-center gap-3 text-white/90 text-sm tracking-wide uppercase">
          <div className="p-1.5 bg-violet-500/20 rounded-md border border-violet-500/30">
            <Blocks className="w-4 h-4 text-violet-400" />
          </div>
          Integrations
        </h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-6 relative z-10 space-y-8">
        
        {/* Active Connections */}
        <section>
          <h3 className="text-xs font-semibold text-white/30 uppercase tracking-widest mb-4">Active Modules</h3>
          
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-5 h-5 text-violet-400 animate-spin" />
            </div>
          ) : connections.length === 0 ? (
            <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.05] text-center shadow-inner">
              <p className="text-xs text-white/40">No modules connected yet.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {connections.map(conn => (
                <div key={conn.name} className="relative group p-4 rounded-2xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.05] hover:border-white/[0.1] transition-all duration-300 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-xl transition-all duration-500 ${conn.disabled ? 'bg-white/5 border border-white/10' : 'bg-emerald-500/20 border border-emerald-500/30 shadow-[0_0_20px_rgba(16,185,129,0.15)]'}`}>
                        <GitBranch className={`w-4 h-4 transition-colors duration-500 ${conn.disabled ? 'text-white/40' : 'text-emerald-400'}`} />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-white/90 tracking-wide">{conn.name}</h4>
                        <p className={`text-[10px] uppercase tracking-wider font-medium mt-0.5 transition-colors duration-500 ${conn.disabled ? 'text-white/30' : 'text-emerald-400/80'}`}>
                          {conn.disabled ? 'Paused' : 'Active'}
                        </p>
                      </div>
                    </div>
                    
                    {/* Toggle Switch */}
                    <button 
                      onClick={() => handleToggle(conn.name)}
                      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-300 ease-in-out focus:outline-none ${conn.disabled ? 'bg-white/10' : 'bg-emerald-500'}`}
                    >
                      <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-lg ring-0 transition duration-300 ease-in-out ${conn.disabled ? 'translate-x-0' : 'translate-x-4'}`} />
                    </button>
                  </div>
                  
                  {/* Disconnect Button (Hidden until hover) */}
                  <div className="pt-3 mt-3 border-t border-white/[0.05] flex justify-end opacity-0 group-hover:opacity-100 transition-opacity duration-300 translate-y-1 group-hover:translate-y-0">
                    <button 
                      onClick={() => handleDisconnect(conn.name)}
                      className="text-xs font-medium text-rose-400/50 hover:text-rose-400 flex items-center gap-1.5 transition-colors"
                    >
                      <Unplug className="w-3.5 h-3.5" />
                      Disconnect
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Available Integrations */}
        {!githubConnection && !loading && (
          <section>
            <h3 className="text-xs font-semibold text-white/30 uppercase tracking-widest mb-4">Discover</h3>
            
            <div className="p-[1px] rounded-2xl bg-gradient-to-b from-white/10 to-transparent shadow-xl">
              <div className="p-5 rounded-[15px] bg-[#0A0A0B] flex flex-col gap-5">
                <div className="flex items-start gap-3">
                  <div className="p-2.5 rounded-xl bg-white/5 border border-white/10">
                    <GitBranch className="w-5 h-5 text-white/90" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-white/90 tracking-wide">GitHub</h4>
                    <p className="text-xs text-white/50 leading-relaxed mt-1.5">
                      Supercharge CORE with access to search repositories, read code, and analyze PRs.
                    </p>
                  </div>
                </div>
                <button 
                  onClick={handleGithubConnect}
                  className="w-full relative group overflow-hidden bg-white/5 hover:bg-white/10 text-white/90 font-medium py-2.5 rounded-xl flex items-center justify-center gap-2 transition-all duration-300 border border-white/10 hover:border-white/20"
                >
                  <span className="relative z-10 text-sm tracking-wide">Connect Integration</span>
                  <div className="absolute inset-0 bg-gradient-to-r from-violet-500/0 via-violet-500/20 to-violet-500/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000 ease-in-out"></div>
                </button>
              </div>
            </div>
          </section>
        )}

        {status === 'success' && (
          <div className="absolute bottom-6 left-6 right-6 p-4 bg-emerald-500/10 border border-emerald-500/20 backdrop-blur-xl rounded-2xl flex items-center gap-3 text-emerald-400 text-sm shadow-[0_0_30px_rgba(16,185,129,0.15)] transition-all">
            <CheckCircle2 className="w-5 h-5 shrink-0" /> 
            <div>
              <p className="font-semibold tracking-wide">Integration Bound</p>
              <p className="text-emerald-400/70 text-[11px] mt-0.5">The module is ready to use.</p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
