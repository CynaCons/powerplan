import { motion, useInView } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'

type ExampleMeta = {
  id: string
  title: string
  blurb: string
  file: string
  when: string
}

const EXAMPLES: ExampleMeta[] = [
  {
    id: 'greenfield',
    title: 'Greenfield skeleton',
    blurb: 'What create_plan produces — goal, divider, first major/iteration, open tasks.',
    file: 'examples/greenfield.md',
    when: 'Empty repo / first agent session',
  },
  {
    id: 'mid',
    title: 'Mid-project + Current Status',
    blurb: 'Status table at the top, current iteration marked, backlog for later.',
    file: 'examples/mid-project.md',
    when: 'Active shipping with mixed open/done work',
  },
  {
    id: 'history',
    title: 'Multi-major history',
    blurb: 'Completed majors, user-feedback iterations, planned section, future backlog.',
    file: 'examples/history.md',
    when: 'Mature plan agents should not re-read end-to-end',
  },
]

export function Examples() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })
  const [active, setActive] = useState(0)
  const [bodies, setBodies] = useState<Record<string, string>>({})

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const base = import.meta.env.BASE_URL || '/'
      const next: Record<string, string> = {}
      for (const ex of EXAMPLES) {
        try {
          const res = await fetch(`${base}${ex.file}`)
          next[ex.id] = res.ok ? await res.text() : `# missing ${ex.file}`
        } catch {
          next[ex.id] = `# failed to load ${ex.file}`
        }
      }
      if (!cancelled) setBodies(next)
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const ex = EXAMPLES[active]
  const body = bodies[ex.id] || 'Loading…'

  return (
    <section id="examples" className="py-24 px-4" ref={ref}>
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-12"
        >
          <div className="inline-flex text-xs mono px-3 py-1 rounded-full border border-emerald-500/40 text-emerald-300 bg-emerald-500/10 mb-4">
            REAL PLANS — the product
          </div>
          <h2 className="text-4xl font-bold text-white mb-3">Example plans</h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            powerplan authors and rewrites markdown that looks like this — human-readable,
            agent-operable. Pick an example; agents use tools so they never need the whole file.
          </p>
        </motion.div>

        <div className="flex flex-col lg:flex-row gap-6">
          <div className="lg:w-72 shrink-0 space-y-2">
            {EXAMPLES.map((item, i) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setActive(i)}
                className={`w-full text-left p-4 rounded-xl border transition-colors ${
                  i === active
                    ? 'border-sky-500/60 bg-sky-500/10'
                    : 'border-slate-800 bg-[var(--pp-card)] hover:border-slate-600'
                }`}
              >
                <div className="font-semibold text-white text-sm mb-1">{item.title}</div>
                <div className="text-xs text-slate-400 mb-2">{item.blurb}</div>
                <div className="text-[11px] mono text-sky-400/80">{item.when}</div>
              </button>
            ))}
            <a
              href={`https://github.com/CynaCons/powerplan/blob/main/site/public/${ex.file}`}
              target="_blank"
              rel="noreferrer"
              className="block text-center text-sm text-slate-400 hover:text-sky-300 py-2"
            >
              Open raw on GitHub →
            </a>
          </div>

          <motion.div
            key={ex.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex-1 rounded-xl border border-slate-700 bg-[#0c1220] overflow-hidden shadow-2xl min-h-[420px]"
          >
            <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-[#0a101c]">
              <span className="mono text-xs text-slate-500">{ex.file}</span>
              <span className="text-[10px] uppercase tracking-wider text-emerald-400/80">PLAN.md</span>
            </div>
            <pre className="p-4 mono text-[12px] md:text-[13px] leading-relaxed text-slate-300 overflow-auto max-h-[560px] whitespace-pre-wrap">
              {body}
            </pre>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
