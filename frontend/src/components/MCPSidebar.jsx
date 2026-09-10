import { useState, useEffect } from 'react';
import { GitBranch, Blocks, Plug, Loader2, ServerCrash, CheckCircle2 } from 'lucide-react';

export default function MCPSidebar() {
  const [formData, setFormData] = useState({
    name: 'My Custom Server',
    transport: 'stdio',
    command: 'npx',
    args: '-y,@modelcontextprotocol/server-postgres',
    envKey: 'POSTGRES_URL',
    envVal: ''
  });
  
  const [status, setStatus] = useState('idle'); // idle, loading, success, error
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('mcp_connected') === 'true') {
      setStatus('success');
      window.history.replaceState({}, document.title, window.location.pathname);
      setTimeout(() => setStatus('idle'), 3000);
    }
  }, []);

  const handleGithubConnect = () => {
    const token = localStorage.getItem('token');
    if (!token) return;
    window.location.href = `http://127.0.0.1:8000/api/oauth/github/login?token=${token}`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus('loading');
    
    const payload = {
      name: formData.name,
      transport: formData.transport,
      command: formData.command,
      args: formData.args.split(',').map(s => s.trim()),
      env: formData.envKey && formData.envVal ? { [formData.envKey]: formData.envVal } : {}
    };

    try {
      const res = await fetch('http://127.0.0.1:8000/api/mcp/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + localStorage.getItem('token')
        },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to connect');
      }
      
      setStatus('success');
      setTimeout(() => setStatus('idle'), 3000);
    } catch (err) {
      setErrorMsg(err.message);
      setStatus('error');
    }
  };

  return (
    <aside className="w-80 bg-surface border-l border-border flex flex-col hidden lg:flex">
      <div className="h-16 flex items-center px-6 border-b border-border">
        <h2 className="font-bold flex items-center gap-2 text-slate-200">
          <Blocks className="w-5 h-5 text-accent" />
          MCP Extensions
        </h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-6">
        <p className="text-sm text-slate-400 mb-6 leading-relaxed">
          Connect external MCP servers to give CORE dynamic capabilities during your session.
        </p>

        {/* GitHub OAuth Button */}
        <div className="mb-6 pb-6 border-b border-border">
          <button 
            onClick={handleGithubConnect}
            className="w-full bg-[#24292e] hover:bg-[#1b1f23] text-white font-medium py-3 rounded-lg flex items-center justify-center gap-3 transition-colors border border-slate-700 shadow-sm"
          >
            <GitBranch className="w-5 h-5" />
            Connect with GitHub
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <h3 className="text-sm font-bold text-slate-300">Manual Configuration</h3>
          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Server Name</label>
            <input 
              type="text" 
              value={formData.name}
              onChange={e => setFormData({...formData, name: e.target.value})}
              className="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-accent outline-none"
            />
          </div>
          
          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Transport</label>
            <select 
              value={formData.transport}
              onChange={e => setFormData({...formData, transport: e.target.value})}
              className="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-accent outline-none"
            >
              <option value="stdio">Stdio (Local command)</option>
              <option value="sse">SSE (Remote URL)</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Command</label>
            <input 
              type="text" 
              value={formData.command}
              onChange={e => setFormData({...formData, command: e.target.value})}
              className="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-accent outline-none"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Args (comma separated)</label>
            <input 
              type="text" 
              value={formData.args}
              onChange={e => setFormData({...formData, args: e.target.value})}
              className="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-accent outline-none"
            />
          </div>

          <div className="p-4 bg-slate-900/50 border border-border rounded-xl space-y-3 mt-2">
            <h3 className="text-xs font-bold text-slate-300">Environment Variables</h3>
            <div className="space-y-2">
              <input 
                type="text" 
                placeholder="Key (e.g. POSTGRES_URL)"
                value={formData.envKey}
                onChange={e => setFormData({...formData, envKey: e.target.value})}
                className="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-accent outline-none"
              />
              <input 
                type="password" 
                placeholder="Value"
                value={formData.envVal}
                onChange={e => setFormData({...formData, envVal: e.target.value})}
                className="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-accent outline-none"
              />
            </div>
          </div>

          <button 
            type="submit"
            disabled={status === 'loading'}
            className="w-full mt-4 bg-accent hover:bg-violet-600 text-white font-medium py-2.5 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            {status === 'loading' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plug className="w-4 h-4" />}
            Connect Server
          </button>
        </form>

        {status === 'success' && (
          <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg flex items-center gap-2 text-emerald-400 text-sm">
            <CheckCircle2 className="w-4 h-4" /> Bound successfully
          </div>
        )}
        
        {status === 'error' && (
          <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg flex items-start gap-2 text-rose-400 text-sm">
            <ServerCrash className="w-4 h-4 shrink-0 mt-0.5" />
            <p>{errorMsg}</p>
          </div>
        )}
      </div>
    </aside>
  );
}
