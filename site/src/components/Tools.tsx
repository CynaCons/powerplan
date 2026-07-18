import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef } from 'react'

const tools = [
  { name: 'create_plan', kind: 'Bootstrap', desc: 'Create PLAN.md when missing (title, goal, optional plan_path, force).' },
  { name: 'get_current_iteration', kind: 'Agent', desc: 'JSON for the current iteration — preferred agent entry point.' },
  { name: 'get_iteration', kind: 'Agent', desc: 'JSON for one version (tasks, progress) without full-file read.' },
  { name: 'list_iterations / find_task', kind: 'Agent', desc: 'Navigate open work without loading all of PLAN.md.' },
  { name: 'create_major / create_iteration / add_task', kind: 'Mutate', desc: 'Grow the plan surgically (powernote-style headers).' },
  { name: 'complete_task / reopen_task', kind: 'Mutate', desc: 'Tick checkboxes; optional [agent: id] tags.' },
  { name: 'start_iteration / close_iteration', kind: 'Lifecycle', desc: 'Mark ACTIVE/current or COMPLETE (force if open tasks).' },
  { name: 'check_plan', kind: 'Lint', desc: 'Structure issues: duplicates, multi-current, complete-with-open.' },
  { name: 'show_plan', kind: 'Skim', desc: 'Compact index only — not a full dump; agents prefer get_* tools.' },
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
            Server <code className="text-sky-300 mono">powerplan</code> — every tool accepts optional{' '}
            <code className="text-sky-300 mono">plan_path</code> (default: walk-up from cwd).
          </p>
        </motion.div>

        <div className="rounded-xl border border-slate-800 overflow-hidden bg-[var(--pp-card)]">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="px-4 py-3 font-medium">Tool</th>
                <th className="px-4 py-3 font-medium">Kind</th>
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
                        t.kind === 'Agent' || t.kind === 'Bootstrap'
                          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                          : t.kind === 'Mutate' || t.kind === 'Lifecycle'
                            ? 'bg-sky-500/10 text-sky-300 border-sky-500/30'
                            : 'bg-slate-500/10 text-slate-300 border-slate-500/30'
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
