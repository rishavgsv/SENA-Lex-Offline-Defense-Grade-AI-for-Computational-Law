import { useState, useRef, useEffect } from 'react';
import { Send, ArrowRight, ShieldCheck, Loader2, Sparkles, Target, FileText, ChevronDown, Search, Upload, Shield, Scale, MessageSquare, Zap, BookOpen, Telescope } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

/* ═══════════════════════════════════════════════════════════
   Confidence Breakdown Panel
   ═══════════════════════════════════════════════════════════ */

const DIMENSION_LABELS = {
  retrieval_relevance:    { label: 'Retrieval Relevance',    icon: '🔍' },
  answer_faithfulness:    { label: 'Answer Faithfulness',    icon: '🛡️' },
  cross_chunk_agreement:  { label: 'Cross-Chunk Agreement',  icon: '🔗' },
  citation_coverage:      { label: 'Citation Coverage',      icon: '📄' },
  query_coverage:         { label: 'Query Coverage',         icon: '🎯' },
};

function getBarColor(value) {
  if (value >= 0.70) return { bar: 'bg-emerald-500', glow: 'shadow-emerald-500/20' };
  if (value >= 0.40) return { bar: 'bg-amber-500',   glow: 'shadow-amber-500/20' };
  return { bar: 'bg-red-500', glow: 'shadow-red-500/20' };
}

function getConfidenceStyle(value) {
  if (value >= 0.70) return { text: 'text-emerald-400', bg: 'bg-emerald-500/8', border: 'border-emerald-500/15' };
  if (value >= 0.40) return { text: 'text-amber-400', bg: 'bg-amber-500/8', border: 'border-amber-500/15' };
  return { text: 'text-red-400', bg: 'bg-red-500/8', border: 'border-red-500/15' };
}

function ConfidenceBreakdownPanel({ breakdown, isExpanded, onToggle }) {
  if (!breakdown) return null;
  const finalPct = Math.round((breakdown.final_score ?? 0) * 100);
  const style = getConfidenceStyle(breakdown.final_score);

  return (
    <div className="mb-3">
      {/* Inline pill — click to expand */}
      <button
        onClick={onToggle}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full ${style.bg} border ${style.border} transition-all hover:brightness-110 cursor-pointer`}
      >
        <ShieldCheck size={11} className={style.text} />
        <span className={`text-[11px] font-semibold ${style.text}`}>
          {finalPct}% confident
        </span>
        <ChevronDown
          size={10}
          className={`${style.text} opacity-50 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Expandable breakdown */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="pt-3 pb-1 space-y-2">
              {Object.entries(DIMENSION_LABELS).map(([key, { label, icon }]) => {
                const value = breakdown[key] ?? 0;
                const pct = Math.round(value * 100);
                const colors = getBarColor(value);
                return (
                  <div key={key} className="flex items-center gap-2">
                    <span className="text-[12px] w-5 shrink-0">{icon}</span>
                    <span className="text-[11px] text-white/45 w-[130px] shrink-0 truncate">{label}</span>
                    <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.6, ease: 'easeOut' }}
                        className={`h-full rounded-full ${colors.bar} ${colors.glow}`}
                      />
                    </div>
                    <span className={`text-[10px] font-mono font-semibold w-9 text-right ${value >= 0.7 ? 'text-emerald-400/80' : value >= 0.4 ? 'text-amber-400/80' : 'text-red-400/80'}`}>
                      {pct}%
                    </span>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Empty State — shown when no documents uploaded
   ═══════════════════════════════════════════════════════════ */

function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="text-center max-w-sm"
      >
        <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-gradient-to-br from-[hsl(43,96%,56%)]/12 to-[hsl(43,96%,56%)]/3 border border-[hsl(43,96%,56%)]/15 flex items-center justify-center">
          <Scale size={28} className="text-[hsl(43,96%,56%)]/70" />
        </div>
        <h2 className="text-lg font-semibold text-white/85 mb-2">
          Welcome to SENA-Lex
        </h2>
        <p className="text-[13px] text-white/35 mb-8 leading-relaxed">
          Upload a legal document to begin AI-powered analysis.<br />
          Your data never leaves this device.
        </p>
        <div className="grid grid-cols-3 gap-2.5">
          {[
            { icon: Upload, label: 'Upload', desc: 'PDF, DOCX' },
            { icon: Search, label: 'Query', desc: 'Ask anything' },
            { icon: Shield, label: 'Analyze', desc: 'Detect risks' },
          ].map(({ icon: Icon, label, desc }) => (
            <div key={label} className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.05] hover:bg-white/[0.04] transition-colors">
              <Icon size={16} className="text-[hsl(43,96%,56%)]/60 mx-auto mb-1.5" />
              <p className="text-[11px] font-medium text-white/50">{label}</p>
              <p className="text-[9px] text-white/20 mt-0.5">{desc}</p>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Custom Document Selector Dropdown
   ═══════════════════════════════════════════════════════════ */

function DocumentSelector({ value, onChange, documents }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selected = documents.find(d => d.name === value);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] text-[12px] font-medium text-white/65 transition-all min-w-[160px] max-w-[200px]"
      >
        <FileText size={13} className="text-[hsl(43,96%,56%)]/60 shrink-0" />
        <span className="truncate flex-1 text-left">
          {selected ? selected.name : 'All Documents'}
        </span>
        <ChevronDown size={12} className={`text-white/25 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 4, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.96 }}
            transition={{ duration: 0.15 }}
            className="absolute bottom-full mb-1.5 left-0 w-full bg-[hsl(228,10%,10%)] border border-white/[0.08] rounded-xl shadow-2xl shadow-black/60 py-1 z-50 max-h-48 overflow-y-auto custom-scrollbar"
          >
            <button
              onClick={() => { onChange(''); setOpen(false); }}
              className={`w-full text-left px-3 py-2 text-[11px] transition-colors ${!value ? 'bg-[hsl(43,96%,56%)]/8 text-[hsl(43,96%,56%)]' : 'text-white/50 hover:bg-white/[0.04]'}`}
            >
              All Documents
            </button>
            {documents.map(d => (
              <button
                key={d.id}
                onClick={() => { onChange(d.name); setOpen(false); }}
                className={`w-full text-left px-3 py-2 text-[11px] transition-colors truncate ${
                  value === d.name ? 'bg-[hsl(43,96%,56%)]/8 text-[hsl(43,96%,56%)]' : 'text-white/50 hover:bg-white/[0.04]'
                }`}
              >
                {d.name}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Action Button
   ═══════════════════════════════════════════════════════════ */

function ActionButton({ icon: Icon, label, onClick, disabled, variant = 'default' }) {
  const styles = variant === 'danger'
    ? 'bg-red-500/6 hover:bg-red-500/12 border-red-500/12 hover:border-red-500/20 text-red-300/70 hover:text-red-300'
    : 'bg-white/[0.02] hover:bg-white/[0.05] border-white/[0.06] hover:border-white/[0.1] text-white/55 hover:text-white/75';

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-[12px] font-medium transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed ${styles}`}
    >
      <Icon size={13} /> {label}
    </button>
  );
}

/* ═══════════════════════════════════════════════════════════
   Message Bubble
   ═══════════════════════════════════════════════════════════ */

function MessageBubble({ msg, index, onCitationClick, onToggleBreakdown }) {
  const isUser = msg.role === 'user';
  const isSystem = msg.content?.startsWith('[System]') || msg.content?.startsWith('✅') || msg.content?.startsWith('❌');

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div className={`max-w-[80%] rounded-2xl p-4 transition-all ${
        isUser
          ? 'bg-gradient-to-br from-[hsl(43,96%,56%)]/12 to-[hsl(43,96%,56%)]/4 border border-[hsl(43,96%,56%)]/15 rounded-br-lg'
          : isSystem
            ? 'bg-[hsl(228,10%,8%)] border border-white/[0.04] rounded-bl-lg'
            : 'bg-[hsl(228,10%,8%)] border border-white/[0.06] rounded-bl-lg shadow-lg shadow-black/15'
      }`}>
        {/* Confidence indicator */}
        {!isUser && msg.confidence_breakdown ? (
          <ConfidenceBreakdownPanel
            breakdown={msg.confidence_breakdown}
            isExpanded={msg.breakdownExpanded}
            onToggle={() => onToggleBreakdown(index)}
          />
        ) : !isUser && msg.confidence && !isSystem ? (
          (() => {
            const style = getConfidenceStyle(msg.confidence);
            return (
              <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full ${style.bg} border ${style.border} mb-3`}>
                <ShieldCheck size={11} className={style.text} />
                <span className={`text-[11px] font-semibold ${style.text}`}>
                  {(msg.confidence * 100).toFixed(0)}% confident
                </span>
              </div>
            );
          })()
        ) : null}
        
        {/* Message text */}
        <p className={`leading-relaxed whitespace-pre-wrap ${
          isUser ? 'text-[13px] text-white/85' : 'text-[13px] text-white/75'
        }`}>
          {msg.content}
        </p>
        
        {/* Citation sources */}
        {msg.sources && msg.sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-white/[0.06] space-y-1.5">
            <p className="text-[10px] text-white/25 uppercase tracking-wider font-semibold mb-1.5">Verified Sources</p>
            {msg.sources.map((src, idx) => (
               <button 
                 key={idx}
                 onClick={() => onCitationClick(src)}
                 className="flex items-center gap-2 text-[11px] text-left w-full bg-white/[0.02] hover:bg-white/[0.05] p-2 rounded-lg border border-white/[0.04] hover:border-white/[0.08] transition-all group"
               >
                 <div className="flex-1 min-w-0">
                   <span className="text-[hsl(43,96%,56%)]/70 group-hover:text-[hsl(43,96%,56%)] font-medium">{src.document}</span>
                   <span className="text-white/25 ml-1.5">p.{src.page}</span>
                 </div>
                 <ArrowRight size={12} className="text-white/15 group-hover:text-white/40 transition-colors shrink-0" />
               </button>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Loading Skeleton
   ═══════════════════════════════════════════════════════════ */

function LoadingSkeleton() {
  return (
    <motion.div 
      initial={{ opacity: 0 }} 
      animate={{ opacity: 1 }} 
      className="flex justify-start"
    >
      <div className="bg-[hsl(228,10%,8%)] border border-white/[0.06] rounded-2xl rounded-bl-lg p-4 max-w-[70%]">
        <div className="flex items-center gap-2.5 mb-3">
          <div className="w-7 h-7 rounded-lg bg-[hsl(43,96%,56%)]/8 border border-[hsl(43,96%,56%)]/12 flex items-center justify-center">
            <Loader2 size={13} className="animate-spin text-[hsl(43,96%,56%)]/70" />
          </div>
          <div>
            <span className="text-[12px] font-medium text-white/50">Analyzing</span>
            <span className="text-[10px] text-white/20 ml-1.5">Searching vector space...</span>
          </div>
        </div>
        <div className="space-y-2">
          <div className="h-2.5 bg-white/[0.03] rounded-full w-full" style={{ animation: 'shimmer 1.5s infinite', backgroundSize: '200% 100%', backgroundImage: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.03) 50%, transparent 100%)' }} />
          <div className="h-2.5 bg-white/[0.03] rounded-full w-4/5" style={{ animation: 'shimmer 1.5s infinite 0.1s', backgroundSize: '200% 100%', backgroundImage: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.03) 50%, transparent 100%)' }} />
          <div className="h-2.5 bg-white/[0.03] rounded-full w-3/5" style={{ animation: 'shimmer 1.5s infinite 0.2s', backgroundSize: '200% 100%', backgroundImage: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.03) 50%, transparent 100%)' }} />
        </div>
      </div>
    </motion.div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Response Mode Selector
   ═══════════════════════════════════════════════════════════ */

const RESPONSE_MODES = [
  { key: 'brief',         icon: Zap,       label: 'Brief',         desc: '2-3 sentences',       color: 'text-sky-400',    bg: 'bg-sky-500/10',  border: 'border-sky-500/20',  activeBg: 'bg-sky-500/15' },
  { key: 'detailed',      icon: BookOpen,   label: 'Detailed',      desc: 'Standard analysis',   color: 'text-[hsl(43,96%,56%)]', bg: 'bg-[hsl(43,96%,56%)]/8', border: 'border-[hsl(43,96%,56%)]/15', activeBg: 'bg-[hsl(43,96%,56%)]/12' },
  { key: 'comprehensive', icon: Telescope,  label: 'Comprehensive', desc: 'Deep multi-paragraph', color: 'text-violet-400', bg: 'bg-violet-500/10', border: 'border-violet-500/20', activeBg: 'bg-violet-500/15' },
];

function ResponseModeSelector({ value, onChange }) {
  return (
    <div className="flex items-center gap-1 p-0.5 rounded-xl bg-white/[0.015] border border-white/[0.04]">
      {RESPONSE_MODES.map(mode => {
        const Icon = mode.icon;
        const isActive = value === mode.key;
        return (
          <button
            key={mode.key}
            onClick={() => onChange(mode.key)}
            className={`relative flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-all duration-200 ${isActive ? `${mode.activeBg} ${mode.color} ${mode.border} border shadow-sm` : 'text-white/30 hover:text-white/50 border border-transparent'}`}
            title={mode.desc}
          >
            <Icon size={12} />
            <span>{mode.label}</span>
            {isActive && (
              <motion.div
                layoutId="response-mode-indicator"
                className="absolute inset-0 rounded-lg border border-white/[0.05]"
                transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Main Chat Interface
   ═══════════════════════════════════════════════════════════ */

export default function ChatInterface({ documents, onCitationClick, onViolationsDetected }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hello. I am SENA-Lex, your highly secure & strictly offline legal assistant. Upload a document to begin, and I will cite exact pages for any query.",
      sources: []
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [documentFilter, setDocumentFilter] = useState("");
  const [responseMode, setResponseMode] = useState("detailed");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Clear chat history when switching document filters to prevent context bleed
  useEffect(() => {
    setMessages([
      {
        role: 'assistant',
        content: documentFilter 
          ? `Switched focus to: ${documentFilter}. I will now only draw answers from this document.`
          : "Hello. I am SENA-Lex, your highly secure & strictly offline legal assistant. Upload a document to begin, and I will cite exact pages for any query.",
        sources: []
      }
    ]);
  }, [documentFilter]);

  const handleToggleBreakdown = (index) => {
    setMessages(prev => {
      const updated = [...prev];
      const target = { ...updated[index] };
      target.breakdownExpanded = !target.breakdownExpanded;
      updated[index] = target;
      return updated;
    });
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading || documents.length === 0) return;

    const userMsg = input.trim();
    setInput("");
    
    const currentMessages = [...messages, { role: 'user', content: userMsg }];
    setMessages(currentMessages);
    setLoading(true);

    try {
      // Insert empty assistant response placeholder
      setMessages(prev => [...prev, { role: 'assistant', content: '', sources: [], confidence: 0, confidence_breakdown: null, breakdownExpanded: false }]);
      
      const sessionHistory = currentMessages
        .filter(m => m.role !== 'assistant' || (!m.content.startsWith('Hello. I am SENA-Lex') && !m.content.startsWith('Switched focus to')))
        .map(m => ({ role: m.role, content: m.content }));

      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: userMsg,
          session_id: "default",
          chat_history: sessionHistory,
          document_filter: documentFilter || null,
          response_mode: responseMode
        })
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(5));
              setMessages(prev => {
                const updated = [...prev];
                const lastIdx = updated.length - 1;
                const lastMsg = { ...updated[lastIdx] };
                if (data.confidence !== undefined) {
                  lastMsg.confidence = data.confidence;
                }
                if (data.sources) {
                  lastMsg.sources = data.sources;
                }
                if (data.confidence_breakdown) {
                  lastMsg.confidence_breakdown = data.confidence_breakdown;
                  lastMsg.confidence = data.confidence_breakdown.final_score;
                }
                if (data.text) lastMsg.content += data.text;
                if (data.error) lastMsg.content += "\n[Error] " + data.error;
                updated[lastIdx] = lastMsg;
                return updated;
              });
            } catch (err) {
              console.error("SSE JSON Parse Error:", err);
            }
          }
        }
      }
    } catch (err) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1].content = "Error connecting to the local backend.";
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  const performDocumentAction = async (endpoint, actionName) => {
    if (documents.length === 0 || loading) return;
    const targetDoc = documentFilter ? documentFilter : documents[documents.length - 1].name;
    const isViolations = endpoint === 'detect-violations';
    
    setLoading(actionName);
    
    setMessages(prev => [...prev, { 
      role: 'assistant', 
      content: `[System] Performing ${actionName} on ${targetDoc}...\n\n`, 
      sources: [], 
      confidence: 1.0 
    }]);

    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: targetDoc })
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(5));
              if (data.text) {
                fullText += data.text;
                if (!isViolations) {
                  setMessages(prev => {
                    const updated = [...prev];
                    const lastIdx = updated.length - 1;
                    const lastMsg = { ...updated[lastIdx] };
                    lastMsg.content += data.text;
                    updated[lastIdx] = lastMsg;
                    return updated;
                  });
                }
              }
              if (data.error) setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1].content += "\n[Error] " + data.error;
                return updated;
              });
            } catch (err) {}
          }
        }
      }

      // After stream completes, if violations — try to parse JSON Risk Array
      if (isViolations && onViolationsDetected) {
        try {
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1].content = `✅ Risk detection complete. View the semantic risk map on your right pane.`;
            return updated;
          });
          
          let parsed;
          try {
             parsed = JSON.parse(fullText.trim());
          } catch (e) {
             const jsonMatch = fullText.match(/({\s*[\s\S]*})/s);
             if (jsonMatch) parsed = JSON.parse(jsonMatch[1]);
          }
          
          const riskArray = parsed.violations || parsed;
          if (Array.isArray(riskArray) && riskArray.length > 0) {
            onViolationsDetected(targetDoc, riskArray);
          } else {
             // Fallback for array format
             const arrMatch = fullText.match(/(\[.*?\])/s);
             if (arrMatch) {
                const arr = JSON.parse(arrMatch[1]);
                if (Array.isArray(arr) && arr.length > 0) onViolationsDetected(targetDoc, arr);
             }
          }
        } catch (parseErr) {
          console.warn("Could not parse Risk Array from violations response.", parseErr);
          setMessages(prev => {
             const updated = [...prev];
             updated[updated.length - 1].content = `❌ Error: Received malformed JSON from model.`;
             return updated;
          });
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: "Failed to perform document action." }]);
    } finally {
      setLoading(false);
    }
  };

  // Show empty state when no documents uploaded
  if (documents.length === 0) {
    return (
      <div className="flex-1 flex flex-col h-full">
        <EmptyState />
        <div className="px-4 lg:px-8 pb-3 max-w-2xl mx-auto w-full">
          <div className="relative">
            <input
              type="text"
              disabled
              placeholder="Upload a document to begin..."
              className="w-full bg-white/[0.02] border border-white/[0.05] rounded-2xl py-3.5 pl-5 pr-14 text-[13px] text-white/80 placeholder:text-white/20 disabled:opacity-40 cursor-not-allowed"
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-transparent px-3 lg:px-8 max-w-3xl mx-auto w-full">
      {/* Message List */}
      <div className="flex-1 overflow-y-auto pb-4 pt-4 pr-2 custom-scrollbar space-y-4">
        <AnimatePresence>
          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              msg={msg}
              index={i}
              onCitationClick={onCitationClick}
              onToggleBreakdown={handleToggleBreakdown}
            />
          ))}
          {loading && <LoadingSkeleton />}
          <div ref={bottomRef} />
        </AnimatePresence>
      </div>

      {/* Bottom Controls */}
      <div className="pb-2 pt-1 mt-auto space-y-2.5">
        {/* Action Bar */}
        <div className="flex items-center gap-2 px-1">
          <DocumentSelector
            value={documentFilter}
            onChange={setDocumentFilter}
            documents={documents}
          />
          <div className="w-px h-5 bg-white/[0.06]" />
          <ActionButton
            icon={FileText}
            label={`Summarize ${documentFilter ? 'Selected' : 'Latest'} Doc`}
            onClick={() => performDocumentAction('summarize', 'Summary')}
            disabled={loading !== false}
          />
          <ActionButton
            icon={Target}
            label="Detect Violations"
            onClick={() => performDocumentAction('detect-violations', 'Risk Detection')}
            disabled={loading !== false}
            variant="danger"
          />
          
          {/* Spacer */}
          <div className="flex-1" />
          
          {/* Response Mode Selector */}
          <ResponseModeSelector value={responseMode} onChange={setResponseMode} />
        </div>

        {/* Chat Input */}
        <form onSubmit={handleSend} className="relative group">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a legal question in plain English..."
            disabled={loading}
            className="w-full bg-[hsl(228,10%,8%)] border border-white/[0.06] rounded-2xl py-3.5 pl-5 pr-14 text-[13px] text-white/85 placeholder:text-white/20 focus:outline-none focus:border-[hsl(43,96%,56%)]/25 focus:ring-1 focus:ring-[hsl(43,96%,56%)]/10 transition-all duration-200 disabled:opacity-50"
          />
          <button 
            type="submit" 
            disabled={!input.trim() || loading || documents.length === 0}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 p-2 rounded-xl bg-[hsl(43,96%,56%)] text-[hsl(228,20%,10%)] disabled:opacity-30 hover:brightness-110 transition-all duration-200 hover:shadow-lg hover:shadow-[hsl(43,96%,56%)]/15"
          >
            <Send size={15} />
          </button>
        </form>
      </div>
    </div>
  );
}
