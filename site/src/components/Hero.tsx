import { motion } from 'framer-motion'
import { useState } from 'react'

const demoLines = [
  { t: '$ powerplan show_plan', c: 'text-sky-400', d: 0.2 },
  { t: 'PLAN.md  ·  active: v0.1.2 — Mutations', c: 'text-slate-400', d: 0.5 },
  { t: '', c: '', d: 0.55 },
  { t: '  v0.1.0  Core server          [6/6] ████████  done', c: 'text-emerald-400', d: 0.7 },
  { t: '  v0.1.1  Read/show tools      [3/3] ████████  done', c: 'text-emerald-400', d: 0.9 },
  { t: '  v0.1.2  Mutation tools       [1/5] ██░░░░░░  open ←', c: 'text-amber-300', d: 1.1 },
  { t: '  v0.1.3  Lifecycle            [0/5] ░░░░░░░░  open', c: 'text-slate-500', d: 1.3 },
  { t: '', c: '', d: 1.4 },
  { t: 'complete_task("v0.1.2", "add_task")  [agent: grok-4.5]', c: 'text-violet-300', d: 1.7 },
  { t: '✓ task ticked · surgical write · header still truthful', c: 'text-emerald-400', d: 2.1 },
]

function Copy({ text }: { text: string }) {
  const [ok, setOk] = useState(false)
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard.writeText(text)
        setOk(true)
        setTimeout(() => setOk(false), 1500)
      }}
      className="text-xs px-2 py-1 rounded bg-sky-600/80 hover:bg-sky-500 transition-colors"
    >
      {ok ? 'Copied' : 'Copy'}
    </button>
  )
}

export function Hero() {
  const install = 'pip install -e ".[dev]"  # or: python -m powerplan'

  return (
    <section className="relative min-h-[90vh] flex flex-col items-center justify-center px-4 py-20 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-sky-900/25 via-transparent to-transparent" />
      <div className="absolute inset-0 opacity-20 pointer-events-none"
        style={{
          backgroundImage:
            'radial-gradient(circle at 20% 30%, #38bdf833 0%, transparent 40%), radial-gradient(circle at 80% 60%, #a78bfa33 0%, transparent 35%)',
        }}
      />

      <div className="relative z-10 max-w-5xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-sky-500/40 bg-sky-500/10 text-sky-300 text-sm mb-8"
        >
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          MCP server · server name <span className="mono">powerplan</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="text-5xl md:text-7xl font-bold tracking-tight mb-5"
        >
          <span className="bg-gradient-to-r from-sky-300 via-violet-300 to-emerald-300 bg-clip-text text-transparent">
            powerplan
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.12 }}
          className="text-xl md:text-2xl text-slate-300 max-w-2xl mx-auto mb-4"
        >
          PLAN.md as the operational backbone of agentic development
        </motion.p>
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.18 }}
          className="text-slate-400 max-w-xl mx-auto mb-10"
        >
          One MCP. Human-language tools. A single writer for iterations and tasks —
          so coordinators and worker agents stay aligned without freeform file thrash.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.22 }}
          className="flex flex-wrap items-center justify-center gap-3 mb-14"
        >
          <a
            href="https://github.com/CynaCons/powerplan"
            className="px-6 py-3 rounded-lg bg-sky-600 hover:bg-sky-500 font-semibold transition-colors"
          >
            View on GitHub
          </a>
          <a
            href="#how"
            className="px-6 py-3 rounded-lg border border-slate-600 hover:border-slate-400 font-semibold transition-colors"
          >
            How it works
          </a>
          <a
            href="#integrate"
            className="px-6 py-3 rounded-lg border border-slate-700 text-slate-300 hover:border-slate-500 font-semibold transition-colors"
          >
            Integrate
          </a>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="max-w-2xl mx-auto text-left"
        >
          <div className="rounded-xl border border-slate-700 bg-[#0f1628] shadow-2xl overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-slate-800 bg-[#0c1220]">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
              <span className="ml-3 text-xs text-slate-500 mono">coordinator · powerplan</span>
            </div>
            <div className="p-4 mono text-sm space-y-1 min-h-[240px]">
              {demoLines.map((line, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: line.d }}
                  className={line.c || 'text-slate-300'}
                >
                  {line.t || '\u00A0'}
                </motion.div>
              ))}
            </div>
          </div>
          <div className="mt-4 flex items-center justify-center gap-2 text-sm text-slate-400">
            <code className="px-3 py-2 rounded-lg bg-[var(--pp-card)] border border-slate-700 mono text-slate-300 text-xs md:text-sm">
              {install}
            </code>
            <Copy text="pip install -e .[dev]" />
          </div>
        </motion.div>
      </div>
    </section>
  )
}
