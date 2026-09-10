import { useState, useEffect, useRef } from 'react';
import { MessageSquare, Plus, ChevronDown, Loader2 } from 'lucide-react';

export default function ThreadManager({ currentThread, onSelectThread }) {
  const [isOpen, setIsOpen] = useState(false);
  const [threads, setThreads] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchThreads = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/chat/threads', {
        headers: {
          'Authorization': 'Bearer ' + localStorage.getItem('token')
        }
      });
      if (res.ok) {
        const data = await res.json();
        setThreads(data.threads || []);
      }
    } catch (error) {
      console.error("Failed to fetch threads", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpen = () => {
    setIsOpen(!isOpen);
    if (!isOpen) {
      fetchThreads();
    }
  };

  const handleNewChat = () => {
    onSelectThread(`thread_${Math.random().toString(36).substring(7)}`);
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button 
        onClick={handleOpen}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-slate-800 transition-colors border border-transparent hover:border-border text-slate-300"
      >
        <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
        <span className="text-sm font-medium truncate max-w-[150px]">{currentThread}</span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-64 bg-surface border border-border rounded-xl shadow-2xl overflow-hidden z-50">
          <div className="p-2 border-b border-border">
            <button 
              onClick={handleNewChat}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-white bg-primary hover:bg-blue-600 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Chat
            </button>
          </div>
          
          <div className="max-h-64 overflow-y-auto p-2 space-y-1">
            {isLoading ? (
              <div className="flex items-center justify-center py-4 text-slate-500">
                <Loader2 className="w-5 h-5 animate-spin" />
              </div>
            ) : threads.length === 0 ? (
              <div className="text-center py-4 text-sm text-slate-500">
                No past threads found
              </div>
            ) : (
              threads.map((thread) => (
                <button
                  key={thread}
                  onClick={() => { onSelectThread(thread); setIsOpen(false); }}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors text-left
                    ${thread === currentThread 
                      ? 'bg-slate-800 text-white' 
                      : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'}`}
                >
                  <MessageSquare className="w-4 h-4 shrink-0" />
                  <span className="truncate">{thread}</span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
