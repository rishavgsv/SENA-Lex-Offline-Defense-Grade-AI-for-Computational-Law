import { useState, useRef, useEffect } from 'react';
import { FileText, Upload, CheckCircle2, Loader2, X, Server, Trash2, ChevronLeft, ChevronRight, Layers } from 'lucide-react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';

export default function Sidebar({ documents, setDocuments, setActiveDocument, collapsed, onToggleCollapse }) {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const [sysStatus, setSysStatus] = useState({ online: false, ollama: false, chunks: 0 });
  const [indexingProgress, setIndexingProgress] = useState({});
  const fileInputRef = useRef(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await axios.get(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/status`);
        setSysStatus({ online: true, ollama: res.data.ollama_connected, chunks: res.data.total_chunks });
      } catch (err) {
        setSysStatus({ online: false, ollama: false, chunks: 0 });
      }
    };
    fetchStatus();

    const fetchDocs = async () => {
      try {
        const res = await axios.get(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/documents`);
        setDocuments(res.data);
      } catch (err) {
        console.error("Could not load historical docs", err);
      }
    };
    fetchDocs();

    const fetchProgress = async () => {
      try {
        const res = await axios.get(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/documents/progress`);
        setIndexingProgress(res.data);
      } catch (err) {}
    };

    const interval = setInterval(fetchStatus, 10000);
    const progInterval = setInterval(fetchProgress, 1000);
    return () => { clearInterval(interval); clearInterval(progInterval); };
  }, []);

  const handleUpload = async (e) => {
    let file;
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      file = e.dataTransfer.files[0];
    } else if (e.target.files) {
      file = e.target.files[0];
    }
    
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/upload`, formData);
      setDocuments([...documents, { 
        id: Date.now(), 
        name: res.data.filename, 
        chunks: res.data.chunks_indexed,
        status: 'ready' 
      }]);
    } catch (error) {
      const detail = error.response?.data?.detail || error.message || "Upload failed. Try again.";
      setUploadError(detail);
      console.error("Upload failed", error);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = null;
    }
  };

  const handleDelete = async (e, docName) => {
    e.stopPropagation();
    if (deleting) return;
    setDeleting(docName);
    try {
      await axios.post(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/documents/delete`, { filename: docName });
      setDocuments(prev => prev.filter(d => d.name !== docName));
      setActiveDocument(prev => prev === docName ? null : prev);
    } catch (err) {
      console.error("Delete failed", err);
    } finally {
      setDeleting(null);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    handleUpload(e);
  };

  const getFileIcon = (name) => {
    if (name.endsWith('.pdf')) return '📄';
    if (name.endsWith('.docx')) return '📝';
    if (name.endsWith('.txt')) return '📋';
    return '📄';
  };

  return (
    <motion.aside 
      animate={{ width: collapsed ? 60 : 280 }}
      transition={{ type: 'spring', damping: 25, stiffness: 250 }}
      className="bg-[hsl(228,10%,6%)] flex flex-col border-r border-white/[0.04] relative z-30 overflow-hidden shrink-0"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Collapse Toggle */}
      <button
        onClick={onToggleCollapse}
        className="absolute top-3 right-2 p-1 rounded-md hover:bg-white/5 text-white/20 hover:text-white/50 transition-all z-10"
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      {/* Header + Upload */}
      <div className={`px-4 pt-5 pb-4 ${collapsed ? 'px-2' : ''}`}>
        {!collapsed && (
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[11px] uppercase tracking-[0.15em] text-white/30 font-semibold">Library</h2>
            {documents.length > 0 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-white/5 text-white/30 font-medium">
                {documents.length}
              </span>
            )}
          </div>
        )}
        
        <button 
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className={`w-full relative group overflow-hidden rounded-xl border transition-all duration-300 cursor-pointer ${
            collapsed ? 'p-2 aspect-square flex items-center justify-center' : 'p-3.5'
          } ${
            isDragOver 
              ? 'bg-[hsl(43,96%,56%)]/15 border-[hsl(43,96%,56%)]/40 shadow-[0_0_24px_rgba(234,179,80,0.15)]' 
              : 'bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04] hover:border-white/[0.1]'
          }`}
        >
          {uploading ? (
            <Loader2 className="animate-spin text-[hsl(43,96%,56%)]" size={collapsed ? 18 : 22} />
          ) : (
            <>
              {!collapsed ? (
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-[hsl(43,96%,56%)]/10 border border-[hsl(43,96%,56%)]/15 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                    <Upload className="text-[hsl(43,96%,56%)]" size={16} />
                  </div>
                  <div className="text-left">
                    <span className="text-[13px] font-medium text-white/80 block leading-tight">Upload Document</span>
                    <span className="text-[10px] text-white/25">.pdf, .docx, .txt</span>
                  </div>
                </div>
              ) : (
                <Upload className="text-[hsl(43,96%,56%)]" size={18} />
              )}
            </>
          )}
        </button>
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleUpload} 
          className="hidden" 
          accept=".pdf,.docx,.txt"
        />
        {uploadError && !collapsed && (
          <motion.div 
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-2.5 p-2.5 rounded-lg bg-red-500/8 border border-red-500/20 text-red-400 text-[11px] leading-relaxed"
          >
            <strong>Error:</strong> {uploadError}
          </motion.div>
        )}
      </div>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto px-2 space-y-1 custom-scrollbar">
        <AnimatePresence>
          {documents.map(doc => {
            const progress = indexingProgress[doc.name];
            const isIndexing = !!progress;
            const percentage = isIndexing ? Math.round((progress.current / progress.total) * 100) : 100;

            return (
              <motion.div 
                key={doc.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                layout
                onClick={() => setActiveDocument(doc.name)}
                className={`group rounded-lg cursor-pointer transition-all duration-200 relative overflow-hidden ${
                  collapsed
                    ? 'p-2 flex items-center justify-center'
                    : 'p-2.5 flex items-start gap-2.5 hover:bg-white/[0.03] border border-transparent hover:border-white/[0.06]'
                }`}
              >
                {/* Indexing progress bar */}
                {isIndexing && (
                  <motion.div 
                    className="absolute left-0 bottom-0 h-[2px] bg-[hsl(43,96%,56%)] z-0"
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: 0.5, ease: 'easeOut' }}
                  />
                )}

                {/* File icon */}
                <div className={`shrink-0 flex items-center justify-center ${collapsed ? '' : 'w-8 h-8 rounded-lg bg-blue-500/8 border border-blue-500/10'}`}>
                  {collapsed ? (
                    <span className="text-sm" title={doc.name}>{getFileIcon(doc.name)}</span>
                  ) : (
                    <FileText size={14} className="text-blue-400/70" />
                  )}
                </div>

                {/* File info */}
                {!collapsed && (
                  <>
                    <div className="flex-1 min-w-0 relative z-10">
                      <p className="text-[12px] font-medium truncate text-white/80 leading-tight">{doc.name}</p>
                      {isIndexing ? (
                        <div className="flex items-center gap-1.5 mt-1">
                          <Loader2 size={10} className="animate-spin text-[hsl(43,96%,56%)]" />
                          <p className="text-[10px] text-[hsl(43,96%,56%)] font-medium">Indexing {percentage}%</p>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 mt-1">
                          <Layers size={9} className="text-white/20" />
                          <p className="text-[10px] text-white/25">{doc.chunks} chunks</p>
                        </div>
                      )}
                    </div>

                    {/* Delete button */}
                    {deleting === doc.name ? (
                      <Loader2 size={12} className="animate-spin text-red-400 shrink-0 mt-1" />
                    ) : (
                      <button
                        onClick={(e) => handleDelete(e, doc.name)}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-red-500/10 text-white/15 hover:text-red-400 transition-all shrink-0"
                        title="Remove document"
                      >
                        <Trash2 size={12} />
                      </button>
                    )}
                  </>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>

        {documents.length === 0 && !uploading && !collapsed && (
          <div className="px-3 py-8 text-center">
            <div className="w-10 h-10 mx-auto mb-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center">
              <FileText size={18} className="text-white/15" />
            </div>
            <p className="text-[11px] text-white/20 leading-relaxed">
              No documents yet.<br />
              Upload a file to begin analysis.
            </p>
          </div>
        )}
      </div>

      {/* Status Footer */}
      {!collapsed && (
        <div className="px-3 pt-3 pb-3 border-t border-white/[0.04] mt-auto">
          <div className="flex items-center gap-1.5 flex-wrap">
            <StatusPill label="API" connected={sysStatus.online} />
            <StatusPill label="Ollama" connected={sysStatus.ollama} />
          </div>
          {sysStatus.chunks > 0 && (
            <p className="text-[9px] text-white/15 mt-1.5 px-0.5">
              {sysStatus.chunks.toLocaleString()} total chunks in memory
            </p>
          )}
        </div>
      )}

      {/* Collapsed status dots */}
      {collapsed && (
        <div className="pb-3 flex flex-col items-center gap-1.5 mt-auto">
          <div className={`w-2 h-2 rounded-full ${sysStatus.online ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} 
               title={sysStatus.online ? 'API Connected' : 'API Disconnected'} />
          <div className={`w-2 h-2 rounded-full ${sysStatus.ollama ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}
               title={sysStatus.ollama ? 'Ollama Connected' : 'Ollama Disconnected'} />
        </div>
      )}
    </motion.aside>
  );
}

/* ── Reusable status pill ────────────────────────────────── */
function StatusPill({ label, connected }) {
  return (
    <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium transition-colors ${
      connected 
        ? 'bg-emerald-500/8 border border-emerald-500/15 text-emerald-400/80' 
        : 'bg-red-500/8 border border-red-500/15 text-red-400/80'
    }`}>
      <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
      {label}
    </div>
  );
}
