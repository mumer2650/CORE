import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Link2, FileText, Activity } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import ApprovalModal from './components/ApprovalModal';
import MCPSidebar from './components/MCPSidebar';
import DocumentSidebar from './components/DocumentSidebar';
import LoginScreen from './components/LoginScreen';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [threadId, setThreadId] = useState(`thread_${Math.random().toString(36).substring(7)}`);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // Modal State
  const [approvalModal, setApprovalModal] = useState({ isOpen: false, pendingTools: [] });

  const messagesEndRef = useRef(null);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    // Placeholder for AI message being streamed
    setMessages(prev => [...prev, { role: 'assistant', content: '', isStreaming: true, toolStatuses: [] }]);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({ message: userMessage, thread_id: threadId }),
      });

      if (!response.body) throw new Error('No readable stream');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\\n\\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '');
            if (!dataStr) continue;
            
            try {
              const data = JSON.parse(dataStr);
              handleStreamEvent(data);
            } catch (err) {
              console.error('JSON parse error:', err);
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => {
        const newMsgs = [...prev];
        newMsgs[newMsgs.length - 1].content = 'Error connecting to the server.';
        newMsgs[newMsgs.length - 1].isStreaming = false;
        return newMsgs;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleStreamEvent = (data) => {
    setMessages(prev => {
      const newMsgs = [...prev];
      const lastMsgIndex = newMsgs.length - 1;
      const lastMsg = { ...newMsgs[lastMsgIndex] }; // Deep clone to fix React Strict Mode double-mutation

      if (data.type === 'token') {
        lastMsg.content += data.content;
      } else if (data.type === 'tool_start') {
        lastMsg.toolStatuses = [...(lastMsg.toolStatuses || []), { name: data.name, status: 'running' }];
      } else if (data.type === 'tool_end') {
        if (lastMsg.toolStatuses) {
          const idx = lastMsg.toolStatuses.findIndex(t => t.name === data.name && t.status === 'running');
          if (idx !== -1) {
            lastMsg.toolStatuses = [...lastMsg.toolStatuses];
            lastMsg.toolStatuses[idx] = { ...lastMsg.toolStatuses[idx], status: 'done' };
          }
        }
      } else if (data.type === 'requires_action') {
        setApprovalModal({ isOpen: true, pendingTools: data.pending_tools });
      } else if (data.type === 'done') {
        lastMsg.isStreaming = false;
      } else if (data.type === 'error') {
        lastMsg.content += `\\n\\n**Error:** ${data.detail}`;
        lastMsg.isStreaming = false;
      }

      newMsgs[lastMsgIndex] = lastMsg;
      return newMsgs;
    });
  };

  const handleApprovalResponse = async (approved) => {
    setApprovalModal({ isOpen: false, pendingTools: [] });
    setIsLoading(true);
    
    // We append a new streaming message bubble to catch the continuation
    setMessages(prev => [...prev, { role: 'assistant', content: '', isStreaming: true, toolStatuses: [] }]);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/approve/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({ thread_id: threadId, approved }),
      });

      if (!response.body) throw new Error('No readable stream');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\\n\\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '');
            if (!dataStr) continue;
            
            try {
              const data = JSON.parse(dataStr);
              handleStreamEvent(data);
            } catch (err) {}
          }
        }
      }
    } catch (error) {
      console.error('Approval stream error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return <LoginScreen onLogin={(newToken) => setToken(newToken)} />;
  }

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Left Sidebar - Documents */}
      <DocumentSidebar />

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0 border-x border-border">
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-6 border-b border-border bg-surface/50 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center">
              <Activity className="w-5 h-5 text-accent" />
            </div>
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">CORE Agent</h1>
          </div>
          <div className="flex items-center gap-4 text-sm text-slate-400">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span> {threadId}</span>
            <button 
              onClick={() => { localStorage.removeItem('token'); setToken(null); }}
              className="text-slate-500 hover:text-rose-400 transition-colors"
            >
              Sign out
            </button>
          </div>
        </header>

        {/* Chat History */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-4">
              <Bot className="w-16 h-16 text-slate-700" />
              <p className="text-lg">How can I assist you today?</p>
            </div>
          )}
          
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 max-w-4xl mx-auto ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`shrink-0 w-10 h-10 rounded-full flex items-center justify-center shadow-lg
                ${msg.role === 'user' ? 'bg-primary' : 'bg-surface border border-border'}`}>
                {msg.role === 'user' ? <User className="w-5 h-5 text-white" /> : <Bot className="w-6 h-6 text-accent" />}
              </div>
              
              <div className={`flex flex-col gap-2 max-w-[80%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                {msg.toolStatuses?.length > 0 && (
                  <div className="flex flex-col gap-1.5 w-full">
                    {msg.toolStatuses.map((t, i) => (
                      <div key={i} className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-surface border border-border text-xs text-slate-400 font-mono w-fit">
                        {t.status === 'running' ? <Loader2 className="w-3 h-3 animate-spin text-primary" /> : <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />}
                        {t.name}()
                      </div>
                    ))}
                  </div>
                )}
                
                {msg.content && (
                  <div className={`px-5 py-4 rounded-2xl shadow-sm text-[15px]
                    ${msg.role === 'user' 
                      ? 'bg-primary text-white rounded-tr-sm' 
                      : 'bg-surface border border-border text-slate-200 rounded-tl-sm prose'}`}>
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-surface/30 border-t border-border backdrop-blur-md">
          <form onSubmit={handleSend} className="max-w-4xl mx-auto relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask CORE anything..."
              className="w-full bg-surface border border-border rounded-xl pl-5 pr-14 py-4 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner"
              disabled={isLoading && !approvalModal.isOpen}
            />
            <button
              type="submit"
              disabled={!input.trim() || (isLoading && !approvalModal.isOpen)}
              className="absolute right-2 top-2 bottom-2 aspect-square rounded-lg bg-primary hover:bg-blue-600 disabled:bg-slate-700 disabled:text-slate-500 flex items-center justify-center text-white transition-colors"
            >
              {isLoading && !approvalModal.isOpen ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </form>
          <div className="max-w-4xl mx-auto mt-2 text-center text-xs text-slate-500">
            CORE can access uploaded documents and dynamic MCP tools.
          </div>
        </div>
      </main>

      {/* Right Sidebar - MCP Extensions */}
      <MCPSidebar />

      {/* HITL Approval Modal */}
      {approvalModal.isOpen && (
        <ApprovalModal 
          pendingTools={approvalModal.pendingTools} 
          onRespond={handleApprovalResponse} 
        />
      )}
    </div>
  );
}

export default App;
