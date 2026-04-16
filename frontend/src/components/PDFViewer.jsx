import { useState } from 'react';
import { X, AlertTriangle, ShieldCheck, Info, ChevronDown, ChevronUp, Filter, FileWarning } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

/* ═══════════════════════════════════════════════════════════
   Risk Style Constants
   ═══════════════════════════════════════════════════════════ */

const RISK_STYLES = {
  High: {
    bg: 'rgba(239, 68, 68, 0.08)',
    bgActive: 'rgba(239, 68, 68, 0.15)',
    border: '#ef4444',
    badge: 'bg-red-500/12 text-red-300 border border-red-500/25',
    badgeActive: 'bg-red-500/20 text-red-300 border border-red-500/35',
    icon: <AlertTriangle size={12} className="text-red-400" />,
    label: 'High',
    dot: 'bg-red-500',
  },
  Medium: {
    bg: 'rgba(245, 158, 11, 0.06)',
    bgActive: 'rgba(245, 158, 11, 0.12)',
    border: '#f59e0b',
    badge: 'bg-amber-500/12 text-amber-300 border border-amber-500/25',
    badgeActive: 'bg-amber-500/20 text-amber-300 border border-amber-500/35',
    icon: <Info size={12} className="text-amber-400" />,
    label: 'Medium',
    dot: 'bg-amber-500',
  },
  Low: {
    bg: 'rgba(34, 197, 94, 0.05)',
    bgActive: 'rgba(34, 197, 94, 0.10)',
    border: '#22c55e',
    badge: 'bg-emerald-500/12 text-emerald-300 border border-emerald-500/25',
    badgeActive: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/35',
    icon: <ShieldCheck size={12} className="text-emerald-400" />,
    label: 'Low',
    dot: 'bg-emerald-500',
  },
};

/* ═══════════════════════════════════════════════════════════
   Risk Badge
   ═══════════════════════════════════════════════════════════ */

function RiskBadge({ level, active = false }) {
  const style = RISK_STYLES[level] || RISK_STYLES.Low;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider ${active ? style.badgeActive : style.badge}`}>
      {style.icon}
      {style.label}
    </span>
  );
}

/* ═══════════════════════════════════════════════════════════
   Risk Summary Bar — Aggregate visualization
   ═══════════════════════════════════════════════════════════ */

function RiskSummaryBar({ counts, total }) {
  if (total === 0) return null;
  
  const segments = [
    { level: 'High', count: counts.High, color: 'bg-red-500' },
    { level: 'Medium', count: counts.Medium, color: 'bg-amber-500' },
    { level: 'Low', count: counts.Low, color: 'bg-emerald-500' },
  ].filter(s => s.count > 0);

  return (
    <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.05]">
      <div className="flex items-center justify-between mb-2.5">
        <h3 className="text-[11px] font-semibold text-white/50 uppercase tracking-wider">Risk Distribution</h3>
        <span className="text-[10px] text-white/25">{total} clauses</span>
      </div>
      
      {/* Progress bar */}
      <div className="flex h-2 rounded-full overflow-hidden bg-white/[0.03] mb-2.5">
        {segments.map(s => (
          <motion.div
            key={s.level}
            initial={{ width: 0 }}
            animate={{ width: `${(s.count / total) * 100}%` }}
            transition={{ duration: 0.6, ease: 'easeOut', delay: 0.1 }}
            className={`${s.color} first:rounded-l-full last:rounded-r-full`}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4">
        {segments.map(s => (
          <div key={s.level} className="flex items-center gap-1.5">
            <div className={`w-1.5 h-1.5 rounded-full ${s.color}`} />
            <span className="text-[10px] text-white/35">
              {s.count} {s.level}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Enhanced Clause Card
   ═══════════════════════════════════════════════════════════ */

function ClauseCard({ item, isActive, onClick, index }) {
  const style = RISK_STYLES[item.risk_level] || RISK_STYLES.Low;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.03 }}
      onClick={onClick}
      whileHover={{ scale: 1.003 }}
      whileTap={{ scale: 0.998 }}
      className="cursor-pointer"
    >
      <div
        className={`rounded-xl overflow-hidden transition-all duration-200 border ${
          isActive
            ? 'border-white/[0.1] shadow-lg shadow-black/25'
            : 'border-white/[0.04] hover:border-white/[0.08]'
        }`}
        style={{ backgroundColor: isActive ? style.bgActive : style.bg }}
      >
        {/* Top risk color bar */}
        <div className="h-0.5 w-full" style={{ backgroundColor: style.border }} />

        <div className="p-3.5">
          {/* Header */}
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-[10px] font-mono font-semibold text-white/30 tracking-wide">
                {item.clause_id}
              </span>
              {item.page_no && (
                <span className="text-[9px] text-white/15 font-medium">
                  p.{item.page_no}
                </span>
              )}
            </div>
            <RiskBadge level={item.risk_level} active={isActive} />
          </div>

          {/* Snippet */}
          <p className={`text-[12px] text-white/65 leading-relaxed ${isActive ? '' : 'line-clamp-2'}`}>
            {item.text_snippet}
          </p>

          {/* Expanded reason */}
          <AnimatePresence>
            {isActive && item.reason && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className="mt-2.5 pt-2.5 border-t border-white/[0.06]"
              >
                <div className="flex items-start gap-2">
                  <AlertTriangle size={11} className="text-amber-400/60 mt-0.5 shrink-0" />
                  <p className="text-[11px] text-white/40 leading-relaxed">{item.reason}</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Filter Tabs
   ═══════════════════════════════════════════════════════════ */

function FilterTabs({ filter, setFilter, counts }) {
  const tabs = [
    { key: 'All', label: 'All', count: counts.High + counts.Medium + counts.Low },
    { key: 'High', label: 'High', count: counts.High, color: 'text-red-300 bg-red-500/12 border-red-500/20' },
    { key: 'Medium', label: 'Med', count: counts.Medium, color: 'text-amber-300 bg-amber-500/12 border-amber-500/20' },
    { key: 'Low', label: 'Low', count: counts.Low, color: 'text-emerald-300 bg-emerald-500/12 border-emerald-500/20' },
  ];

  return (
    <div className="flex items-center gap-1 p-1 rounded-lg bg-white/[0.02]">
      {tabs.map(t => {
        const isActive = filter === t.key;
        return (
          <button
            key={t.key}
            onClick={() => setFilter(t.key)}
            className={`px-2.5 py-1 rounded-md text-[10px] font-semibold transition-all duration-150 ${
              isActive
                ? t.color || 'bg-white/[0.06] text-white/70 border border-white/[0.08]'
                : 'text-white/25 hover:text-white/40 border border-transparent'
            }`}
          >
            {t.label}
            {t.count > 0 && <span className="ml-1 opacity-60">{t.count}</span>}
          </button>
        );
      })}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Main PDFViewer / Risk Panel
   ═══════════════════════════════════════════════════════════ */

export default function PDFViewer({ document: docName, highlights, violations, onClose }) {
  const [activeIndex, setActiveIndex] = useState(-1);
  const [filter, setFilter] = useState('All');

  // Risk items come from the violations prop (parsed JSON array from detect-violations)
  // Falls back to highlights (citation sources) if violations not ready
  const riskItems = violations && violations.length > 0
    ? violations
    : (highlights || []).map(h => ({
        clause_id: `Page ${h.page}`,
        text_snippet: h.text_snippet,
        risk_level: 'Low',
        reason: 'Citation source',
        page_no: h.page,
      }));

  const counts = {
    High: riskItems.filter(r => r.risk_level === 'High').length,
    Medium: riskItems.filter(r => r.risk_level === 'Medium').length,
    Low: riskItems.filter(r => r.risk_level === 'Low').length,
  };

  const filteredItems = filter === 'All' 
    ? riskItems 
    : riskItems.filter(r => r.risk_level === filter);

  return (
    <div className="h-full flex flex-col relative overflow-hidden bg-[hsl(228,10%,5%)]">
      {/* Header */}
      <header className="h-12 border-b border-white/[0.05] flex items-center justify-between px-4 bg-[hsl(228,10%,6%)]/90 backdrop-blur-md z-10 shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <FileWarning size={14} className="text-[hsl(43,96%,56%)]/60 shrink-0" />
          <span className="text-[12px] font-medium text-white/70 truncate max-w-[180px]">{docName}</span>
          <span className="text-[9px] px-1.5 py-0.5 rounded-md bg-[hsl(43,96%,56%)]/8 text-[hsl(43,96%,56%)]/60 font-bold uppercase tracking-widest border border-[hsl(43,96%,56%)]/12">
            Risk
          </span>
        </div>
        <button 
          onClick={onClose} 
          className="p-1.5 rounded-lg hover:bg-white/5 text-white/25 hover:text-white/60 transition-colors"
        >
          <X size={16} />
        </button>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5 custom-scrollbar">
        {/* Risk Summary */}
        <RiskSummaryBar counts={counts} total={riskItems.length} />

        {/* Filter Tabs */}
        {riskItems.length > 0 && (
          <div className="flex items-center justify-between">
            <FilterTabs filter={filter} setFilter={setFilter} counts={counts} />
            <span className="text-[10px] text-white/20 font-medium">
              {filteredItems.length} clause{filteredItems.length !== 1 ? 's' : ''}
            </span>
          </div>
        )}

        {/* Empty state */}
        {riskItems.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-white/[0.02] border border-white/[0.05] flex items-center justify-center">
              <Filter size={20} className="text-white/15" />
            </div>
            <p className="text-[12px] text-white/25 leading-relaxed">
              No risk annotations available.<br />
              Run Violation Detection to begin.
            </p>
          </div>
        )}

        {/* Clause Cards */}
        <motion.div layout className="space-y-2">
          <AnimatePresence>
            {filteredItems.map((item, i) => (
              <ClauseCard
                key={`${item.clause_id}-${i}`}
                item={item}
                index={i}
                isActive={riskItems.indexOf(item) === activeIndex}
                onClick={() => setActiveIndex(riskItems.indexOf(item) === activeIndex ? -1 : riskItems.indexOf(item))}
              />
            ))}
          </AnimatePresence>
        </motion.div>

        {/* Filtered empty state */}
        {riskItems.length > 0 && filteredItems.length === 0 && (
          <div className="text-center py-8">
            <p className="text-[11px] text-white/20">No {filter.toLowerCase()}-risk clauses found.</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="h-8 border-t border-white/[0.04] flex items-center justify-center px-4 shrink-0">
        <span className="text-[9px] text-white/15 tracking-widest uppercase">SENA-Lex · Confidential Analysis</span>
      </div>
    </div>
  );
}
