import { useState } from 'react';
import ChatInterface from './components/ChatInterface';
import Sidebar from './components/Sidebar';
import PDFViewer from './components/PDFViewer';
import { Bot, Settings, Shield, Lock } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

function App() {
  const [activeDocument, setActiveDocument] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [citations, setCitations] = useState([]);
  const [violations, setViolations] = useState([]); // Risk Array from detect-violations
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[hsl(228,12%,5%)] text-[hsl(0,0%,93%)] selection:bg-[hsl(43,96%,56%)]/20 relative z-10">
      
      {/* Sidebar for Files */}
      <Sidebar 
        documents={documents} 
        setDocuments={setDocuments}
        setActiveDocument={setActiveDocument}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Main Chat Interface */}
      <main className="flex-1 flex flex-col relative h-full overflow-hidden">
        
        {/* Header */}
        <header className="h-14 border-b border-white/[0.06] flex items-center justify-between px-5 bg-[hsl(228,10%,6%)]/80 backdrop-blur-xl z-20 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-[hsl(43,96%,56%)]/10 border border-[hsl(43,96%,56%)]/20 flex items-center justify-center">
              <Shield size={16} className="text-[hsl(43,96%,56%)]" />
            </div>
            <div>
              <h1 className="font-bold text-[15px] tracking-tight leading-none">
                <span className="text-gradient-brand">SENA-Lex</span>
                <span className="text-white/25 font-normal ml-1.5 text-[13px]">Intelligence</span>
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/8 border border-emerald-500/15 mr-2">
              <Lock size={10} className="text-emerald-400" />
              <span className="text-[10px] font-medium text-emerald-400/80">Offline Mode</span>
            </div>
            <button className="p-2 rounded-lg hover:bg-white/5 transition-colors group">
              <Settings size={17} className="text-white/30 group-hover:text-white/60 transition-colors" />
            </button>
          </div>
        </header>

        {/* Workspace Area: Chat + Risk Panel */}
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 flex flex-col min-w-0">
            <ChatInterface 
              documents={documents} 
              onCitationClick={(citation) => {
                setActiveDocument(citation.document);
                setCitations([citation]);
              }}
              onViolationsDetected={(docName, riskArray) => {
                setActiveDocument(docName);
                setViolations(riskArray);
                setCitations([]);
              }}
            />
          </div>

          {/* Conditional Risk Panel — slides in from right */}
          <AnimatePresence mode="wait">
            {activeDocument && (
              <motion.div
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: '42%', opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ type: 'spring', damping: 28, stiffness: 220 }}
                className="h-full border-l border-white/[0.06] hidden lg:block overflow-hidden shrink-0"
              >
                <PDFViewer 
                  document={activeDocument} 
                  highlights={citations}
                  violations={violations}
                  onClose={() => { setActiveDocument(null); setViolations([]); }} 
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Bottom Status Bar */}
        <div className="h-7 border-t border-white/[0.04] flex items-center justify-between px-4 bg-[hsl(228,10%,5%)] text-[10px] text-white/25 shrink-0 z-20">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <Lock size={9} />
              Offline processing · Data never leaves your device
            </span>
          </div>
          <span>SENA-Lex v2.0</span>
        </div>
      </main>

    </div>
  );
}

export default App;
