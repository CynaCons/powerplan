import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef } from 'react'

const layers = [
  {
    title: 'You / coordinator agent',
    sub: 'Claude · Grok · Cursor · Codex',
    body: 'Sets goals, starts iterations, judges “done” from real evidence — outside the tool.',
    color: 'from-sky-600 to-sky-800',
  },
  {
    title: 'powerplan MCP',
    sub: 'stdio · tools · file lock',
    body: 'Single writer for PLAN.md. Reads any reasonable plan; rewrites only touched lines.',
    color: 'from-violet-600 to-violet-900',
  },
  {
    title: 'PLAN.md in your repo',
    sub: 'walk-up discovery from cwd',
    body: 'Majors, iterations, goals, checkboxes, backlog. Phase-like prose stays opaque and preserved.',
    color: 'from-emerald-700 to-emerald-950',
  },
]

const flow = [
  { n: '1', t: 'Discover', d: 'Walk up from the project cwd to the nearest PLAN.md (or pass plan_path).' },
  { n: '2', t: 'Show truth', d: 'show_plan / show_current_iteration — ASCII progress the coordinator can trust.' },
  { n: '3', t: 'Mutate surgically', d: 'create_iteration, complete_task, … (v0.1.2+) with optional [agent: id] tags.' },
  { n: '4', t: 'Keep header synced', d: 'start/close iteration auto-syncs active state — no hand-maintained “Active:” drift.' },
]

export function HowItWorks() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })

  return (
    <section id="how" className="py-24 px-4">
      <div className="max-w-5xl mx-auto" ref={ref}>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-14"
        >
          <h2 className="text-4xl font-bold text-white mb-3">How it works</h2>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">
            Layered supervision: humans and coordinators decide; powerplan is the only sanctioned
            PLAN.md writer for the swarm.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-4 mb-16">
          {layers.map((L, i) => (
            <motion.div
              key={L.title}
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.1 * i }}
              className={`rounded-xl p-5 bg-gradient-to-br ${L.color} border border-white/10`}
            >
              <div className="text-xs uppercase tracking-wider text-white/60 mb-1">{L.sub}</div>
              <h3 className="text-lg font-semibold text-white mb-2">{L.title}</h3>
              <p className="text-sm text-white/80 leading-relaxed">{L.body}</p>
            </motion.div>
          ))}
        </div>

        {/* Visual: plan shape */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.25 }}
          className="mb-16 rounded-xl border border-slate-700 bg-[var(--pp-card)] p-6 overflow-x-auto"
        >
          <div className="text-xs text-slate-500 mono mb-3">Managed format (powernote-style)</div>
          <pre className="mono text-sm leading-relaxed text-slate-300">
{`## v0.1 — Core server
### v0.1.2 — Mutation tools
**Goal:** Surgical writes + optional agent tags
- [x] create_iteration
- [ ] add_task / complete_task
- [ ] file lock around RMW

## Backlog
- ASCII gantt timeline`}
          </pre>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {flow.map((f, i) => (
            <motion.div
              key={f.n}
              initial={{ opacity: 0, y: 16 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.15 + i * 0.08 }}
              className="rounded-xl border border-slate-800 bg-[var(--pp-card)] p-5"
            >
              <div className="w-8 h-8 rounded-full bg-sky-500/20 text-sky-300 flex items-center justify-center font-bold text-sm mb-3">
                {f.n}
              </div>
              <h4 className="font-semibold text-white mb-1">{f.t}</h4>
              <p className="text-sm text-slate-400">{f.d}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
