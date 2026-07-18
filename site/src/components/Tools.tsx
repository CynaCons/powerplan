import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef } from 'react'

const tools = [
  { name: 'show_plan', kind: 'Read', desc: 'ASCII overview of majors + iterations with [done/total] progress.' },
  { name: 'show_current_iteration', kind: 'Read', desc: 'Detail of the active / first-open iteration (goal, tasks).' },
  { name: 'get_iteration', kind: 'Read', desc: 'Structured JSON for one version (goal, tasks, status, progress).' },
  { name: 'list_iterations', kind: 'Read', desc: 'Filter open | complete | all.' },
  { name: 'get_backlog', kind: 'Read', desc: 'Backlog section items.' },
  { name: 'find_task', kind: 'Read', desc: 'Substring search across task lines.' },
  { name: 'create_iteration', kind: 'Soon', desc: 'New ### vX.Y.Z section; version monotonicity enforced (v0.1.2).' },
  { name: 'complete_task', kind: 'Soon', desc: 'Tick a checkbox; optional [agent: id] tag (v0.1.3).' },
  { name: 'check_plan', kind: 'Soon', desc: 'Structure lint: versions, checkboxes, header drift (v0.1.3).' },
]

export function Tools() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })

  return (
    <section id="tools" className="py-24 px-4 bg-gradient-to-b from-transparent via-sky-950/20 to-transparent">
      <div className="max-w-5xl mx-auto" ref={ref}>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-12"
        >
          <h2 className="text-4xl font-bold text-white mb-3">MCP tool surface</h2>
          <p className="text-slate-400">
            Server name <code className="text-sky-300 mono">powerplan</code> — every tool accepts optional{' '}
            <code className="text-sky-300 mono">plan_path</code>.
          </p>
        </motion.div>

        <div className="rounded-xl border border-slate-800 overflow-hidden bg-[var(--pp-card)]">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="px-4 py-3 font-medium">Tool</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">What it does</th>
              </tr>
            </thead>
            <tbody>
              {tools.map((t, i) => (
                <motion.tr
                  key={t.name}
                  initial={{ opacity: 0 }}
                  animate={inView ? { opacity: 1 } : {}}
                  transition={{ delay: 0.05 * i }}
                  className="border-b border-slate-800/80 last:border-0 hover:bg-white/[0.03]"
                >
                  <td className="px-4 py-3 mono text-sky-300 whitespace-nowrap">{t.name}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs px-2 py-0.5 rounded border ${
                        t.kind === 'Read'
                          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                          : 'bg-amber-500/10 text-amber-200 border-amber-500/30'
                      }`}
                    >
                      {t.kind}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{t.desc}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
