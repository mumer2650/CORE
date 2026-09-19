import { useState, useEffect } from 'react';
import { Database, UploadCloud, FileText, Loader2, CheckCircle2, AlertCircle, Trash2, ExternalLink } from 'lucide-react';

export default function DocumentSidebar() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, uploading, processing, success, error
  const [taskId, setTaskId] = useState('');

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatus('idle');
    }
  };

  const [progressText, setProgressText] = useState('');
  const [documents, setDocuments] = useState([]);

  const fetchDocuments = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/documents/', {
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
      });
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (e) {
      console.error("Failed to fetch documents", e);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleDelete = async (id) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/documents/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
      });
      if (res.ok) {
        setDocuments(prev => prev.filter(d => d.id !== id));
      }
    } catch (e) {
      console.error("Failed to delete document", e);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus('uploading');
    setProgressText('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/ingest/', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + localStorage.getItem('token')
        },
        body: formData
      });
      
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      
      setTaskId(data.task_id);
      setStatus('processing');
      
      // Poll /api/ingest/{task_id}
      const pollInterval = setInterval(async () => {
        try {
          const pollRes = await fetch(`http://127.0.0.1:8000/api/ingest/${data.task_id}`, {
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
          });
          if (pollRes.ok) {
            const pollData = await pollRes.json();
            setProgressText(pollData.progress || '');
            if (pollData.status === 'completed') {
              clearInterval(pollInterval);
              setStatus('success');
              fetchDocuments(); // Refresh the list
              setTimeout(() => {
                setStatus('idle');
                setFile(null);
                setProgressText('');
              }, 5000);
            } else if (pollData.status === 'failed') {
              clearInterval(pollInterval);
              setStatus('error');
              setProgressText(pollData.error || 'Processing failed');
            }
          }
        } catch (e) {
          console.error("Polling error", e);
        }
      }, 2000);

    } catch (err) {
      setStatus('error');
    }
  };

  return (
    <aside className="w-72 bg-surface border-r border-border flex flex-col hidden md:flex">
      <div className="h-16 flex items-center px-6 border-b border-border">
        <h2 className="font-bold flex items-center gap-2 text-slate-200">
          <Database className="w-5 h-5 text-secondary" />
          RAG Knowledge
        </h2>
      </div>
      
      <div className="p-6">
        <p className="text-sm text-slate-400 mb-6 leading-relaxed">
          Upload PDFs or text files to CORE's private vector database. The agent will retrieve relevant info automatically.
        </p>

        <div className="border-2 border-dashed border-border hover:border-secondary/50 bg-slate-900/50 transition-colors rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer relative">
          <input 
            type="file" 
            accept=".pdf,.txt" 
            onChange={handleFileChange}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
          <UploadCloud className="w-8 h-8 text-slate-500 mb-3" />
          <span className="text-sm font-medium text-slate-300">Drag & Drop file</span>
          <span className="text-xs text-slate-500 mt-1">PDF or TXT only</span>
        </div>

        {file && (
          <div className="mt-4 p-3 bg-slate-900 border border-border rounded-lg flex items-center justify-between">
            <div className="flex items-center gap-3 overflow-hidden">
              <FileText className="w-4 h-4 text-secondary shrink-0" />
              <span className="text-sm text-slate-300 truncate">{file.name}</span>
            </div>
            
            {(status === 'idle' || status === 'error') && (
              <button onClick={handleUpload} className="text-xs bg-secondary text-white px-3 py-1.5 rounded hover:bg-emerald-600 transition-colors">
                {status === 'error' ? 'Retry' : 'Upload'}
              </button>
            )}
            {(status === 'uploading' || status === 'processing') && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-secondary font-mono">{progressText}</span>
                <Loader2 className="w-4 h-4 animate-spin text-secondary" />
              </div>
            )}
            {status === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
            {status === 'error' && <AlertCircle className="w-4 h-4 text-rose-500" />}
          </div>
        )}
        
        {status === 'success' && (
          <p className="text-xs text-emerald-400 mt-3 text-center">
            File processed and successfully embedded!
          </p>
        )}
        
        {status === 'error' && (
          <p className="text-xs text-rose-400 mt-3 text-center">
            {progressText || 'An error occurred during upload.'}
          </p>
        )}

        <div className="mt-8">
          <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">Your Documents</h3>
          <div className="space-y-2">
            {documents.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No documents uploaded yet.</p>
            ) : (
              documents.map(doc => (
                <div key={doc.id} className="p-3 bg-slate-900 border border-border rounded-lg flex items-center justify-between group">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                    <div className="flex flex-col overflow-hidden">
                      <span className="text-sm text-slate-300 truncate" title={doc.filename}>{doc.filename}</span>
                      <span className="text-[10px] text-slate-500">{new Date(doc.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {doc.storage_url && (
                      <a href={doc.storage_url} target="_blank" rel="noopener noreferrer" className="p-1.5 text-slate-400 hover:text-secondary rounded hover:bg-surface transition-colors" title="View Document">
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                    <button onClick={() => handleDelete(doc.id)} className="p-1.5 text-slate-400 hover:text-rose-400 rounded hover:bg-surface transition-colors" title="Delete Document & Embeddings">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </aside>
  );
}
