import { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader2, Plus, MessageSquare, Activity, ShieldAlert, Check, X, Code2, Square } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import ApprovalModal from './components/ApprovalModal';
import MCPSidebar from './components/MCPSidebar';
import DocumentSidebar from './components/DocumentSidebar';
import LoginScreen from './components/LoginScreen';
import ThreadManager from './components/ThreadManager';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [threadId, setThreadId] = useState(
    localStorage.getItem('threadId') || `thread_${Math.random().toString(36).substring(7)}`
  );
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // Modal State
  const [approvalModal, setApprovalModal] = useState({ isOpen: false, pendingTools: [] });
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load chat history when threadId changes
  useEffect(() => {
    if (!token) return;
    localStorage.setItem('threadId', threadId);
    
    const fetchHistory = async () => {
      setIsLoading(true);
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/chat/threads/${threadId}`, {
          headers: { 'Authorization': 'Bearer ' + token }
        });
        if (res.ok) {
          const data = await res.json();
          setMessages(data.messages || []);
        } else if (res.status === 401 || res.status === 403) {
          // Unauthorized or Forbidden: token is invalid, expired, or access denied
          localStorage.removeItem('token');
          localStorage.removeItem('threadId');
          setToken(null);
          setThreadId(`thread_${Math.random().toString(36).substring(7)}`);
        } else {
          setMessages([]);
        }
      } catch (error) {
        console.error("Failed to load history", error);
        setMessages([]);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchHistory();
  }, [threadId, token]);

  const handleThreadChange = (newThreadId) => {
    if (newThreadId !== threadId) {
      setThreadId(newThreadId);
    }
  };

  const handleSend = async (e) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    // Placeholder for AI message being streamed
    setMessages(prev => [...prev, { role: 'assistant', content: '', isStreaming: true, toolStatuses: [] }]);

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({ message: userMessage, thread_id: threadId }),
        signal: abortControllerRef.current.signal
      });

      if (response.status === 401 || response.status === 403) {
        localStorage.removeItem('token');
        localStorage.removeItem('threadId');
        setToken(null);
        setThreadId(`thread_${Math.random().toString(36).substring(7)}`);
        return;
      }

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
      if (error.name === 'AbortError') {
        console.log('Stream stopped by user');
      } else {
        console.error('Chat error:', error);
        setMessages(prev => {
          const newMsgs = [...prev];
          newMsgs[newMsgs.length - 1].content = 'Error connecting to the server.';
          newMsgs[newMsgs.length - 1].isStreaming = false;
          return newMsgs;
        });
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
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
        lastMsg.isStreaming = false;
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

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/approve/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({ thread_id: threadId, approved }),
        signal: abortControllerRef.current.signal
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
      if (error.name === 'AbortError') {
        console.log('Approval stream stopped by user');
      } else {
        console.error('Approval stream error:', error);
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setMessages(prev => {
      const newMsgs = [...prev];
      if (newMsgs.length > 0) {
        newMsgs[newMsgs.length - 1].isStreaming = false;
        if (!newMsgs[newMsgs.length - 1].content) {
          newMsgs[newMsgs.length - 1].content = "*(Stopped generating)*";
        }
      }
      return newMsgs;
    });
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
          <div className="flex items-center gap-4">
            <ThreadManager currentThread={threadId} onSelectThread={handleThreadChange} />
            <div className="w-px h-6 bg-border"></div>
            <button 
              onClick={() => { 
                localStorage.removeItem('token'); 
                localStorage.removeItem('threadId');
                setToken(null); 
                setThreadId(`thread_${Math.random().toString(36).substring(7)}`);
                setMessages([]);
              }}
              className="text-sm text-slate-500 hover:text-rose-400 transition-colors"
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
            <div key={idx} className={`flex w-full max-w-4xl mx-auto ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`flex flex-col gap-2 max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                {msg.toolStatuses?.length > 0 && (
                  <div className="flex flex-col gap-1.5 w-full">
                    {msg.toolStatuses.map((t, i) => (
                      <div key={i} className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface border border-border text-xs text-slate-400 font-mono w-fit">
                        {t.status === 'running' ? <Loader2 className="w-3 h-3 animate-spin text-primary" /> : <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />}
                        {t.name}()
                      </div>
                    ))}
                  </div>
                )}
                
                {(!msg.content && msg.isStreaming && (!msg.toolStatuses || msg.toolStatuses.length === 0)) && (
                  <div className="py-2 flex items-center">
                    <div className="flex items-center gap-1 h-5 px-1">
                      <div className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                      <div className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                      <div className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce"></div>
                    </div>
                  </div>
                )}
                
                {msg.content && (
                  <div className={`text-[15px] overflow-x-auto
                    ${msg.role === 'user' 
                      ? 'px-5 py-3.5 bg-surface border border-border/50 text-slate-200 rounded-3xl rounded-tr-sm shadow-sm' 
                      : 'text-slate-200 prose prose-invert prose-p:leading-relaxed max-w-none'}`}>
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-surface/30 border-t border-border backdrop-blur-md relative">
          
          {/* Stop Generating Button was moved into the input form below */}
          <form onSubmit={handleSend} className="max-w-4xl mx-auto relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask CORE anything..."
              className="w-full bg-surface border border-border rounded-xl pl-5 pr-14 py-4 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner disabled:opacity-50"
              disabled={isLoading || approvalModal.isOpen}
            />
            {isLoading && !approvalModal.isOpen ? (
              <button
                type="button"
                onClick={handleStop}
                className="absolute right-2 top-2 bottom-2 aspect-square rounded-lg bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/30 text-rose-400 flex items-center justify-center transition-all shadow-sm"
                title="Stop generating"
              >
                <Square className="w-4 h-4 fill-current" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim()}
                className="absolute right-2 top-2 bottom-2 aspect-square rounded-lg bg-primary hover:bg-blue-600 disabled:bg-slate-700 disabled:text-slate-500 flex items-center justify-center text-white transition-colors"
              >
                <Send className="w-5 h-5" />
              </button>
            )}
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
