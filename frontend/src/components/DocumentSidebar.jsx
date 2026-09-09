import { useState } from 'react';
import { Database, UploadCloud, FileText, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

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

  const handleUpload = async () => {
    if (!file) return;
    setStatus('uploading');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/documents/upload', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + localStorage.getItem('token')
        },
        body: formData
      });
      
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      
      setTaskId(data.task_id);
      setStatus('success');
      
      // In a real app, we would poll /api/documents/status/{task_id} here
      // For this demo, we'll just show success
      setTimeout(() => {
        setStatus('idle');
        setFile(null);
      }, 5000);

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
            
            {status === 'idle' && (
              <button onClick={handleUpload} className="text-xs bg-secondary text-white px-3 py-1.5 rounded hover:bg-emerald-600 transition-colors">
                Upload
              </button>
            )}
            {status === 'uploading' && <Loader2 className="w-4 h-4 animate-spin text-secondary" />}
            {status === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
            {status === 'error' && <AlertCircle className="w-4 h-4 text-rose-500" />}
          </div>
        )}
        
        {status === 'success' && (
          <p className="text-xs text-emerald-400 mt-3 text-center">
            File queued for background processing.
          </p>
        )}
      </div>
    </aside>
  );
}
