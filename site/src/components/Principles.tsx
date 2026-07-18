import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef } from 'react'

const items = [
  {
    title: 'Single writer',
    body: 'All plan mutations go through powerplan tools. Direct file edits are a process lint, not an OS lock.',
  },
  {
    title: 'Tolerant reader, surgical writer',
    body: 'Parse any reasonable PLAN.md flavor. Rewrite only touched lines. Preserve freeform prose byte-for-byte.',
  },
  {
    title: 'Truthful header',
    body: 'Active-iteration state is derived and auto-synced — never hand-maintained “Active:” drift.',
  },
  {
    title: 'Evidence is process, not a parameter',
    body: 'No audit journal in the MCP. Coordinators and humans judge “done” from real artifacts outside the tool.',
  },
  {
    title: 'Lightweight attribution',
    body: 'Optional agent= on mutations → trailing [agent: id] on the line. No heavy audit log file.',
  },
  {
    title: 'Zero per-project config',
    body: 'Walk up from cwd to the nearest PLAN.md. Override with plan_path when needed.',
  },
]

export function Principles() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })

  return (
    <section className="py-24 px-4">
      <div className="max-w-5xl mx-auto" ref={ref}>
        <motion.h2
          initial={{ opacity: 0, y: 12 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-4xl font-bold text-white text-center mb-12"
        >
          Product principles
        </motion.h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((it, i) => (
            <motion.div
              key={it.title}
              initial={{ opacity: 0, y: 16 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.06 * i }}
              className="p-5 rounded-xl border border-slate-800 bg-[var(--pp-card)] hover:border-sky-500/40 transition-colors"
            >
              <h3 className="font-semibold text-white mb-2">{it.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{it.body}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
