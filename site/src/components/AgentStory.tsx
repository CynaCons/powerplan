import { motion, useScroll, useTransform, useInView } from 'framer-motion'
import { useMemo, useRef, useState, useEffect } from 'react'

type Frame = {
  id: string
  label: string
  tool: string
  args: string
  planLines: string[]
  side?: string
}

const FRAMES: Frame[] = [
  {
    id: 'empty',
    label: '1 · No plan yet',
    tool: 'create_plan',
    args: 'title="Aurora Notes", goal="Ship MVP"',
    planLines: ['(no PLAN.md in project)'],
  },
  {
    id: 'skeleton',
    label: '2 · Skeleton written',
    tool: 'create_plan',
    args: '→ ./PLAN.md created',
    planLines: [
      '# Aurora Notes — Implementation Plan',
      '',
      '**Goal:** Ship MVP',
      '',
      '---',
      '',
      '## v0.1 — Foundation',
      '### v0.1.0 — Bootstrap',
      '- [ ] Define first tasks',
    ],
  },
  {
    id: 'structure',
    label: '3 · Structure grows',
    tool: 'create_iteration + add_task',
    args: 'version="v0.1.1", text="Infinite canvas"',
    planLines: [
      '## v0.1 — Foundation',
      '### v0.1.0 — Bootstrap',
      '- [x] Define first tasks',
      '### v0.1.1 — Canvas (current)',
      '- [ ] Infinite canvas pan/zoom',
      '- [ ] Place text on click',
    ],
  },
  {
    id: 'grow',
    label: '4 · More tasks',
    tool: 'add_task',
    args: 'version="v0.1.1", text="Smoke: npm run dev"',
    planLines: [
      '### v0.1.1 — Canvas (current)',
      '- [ ] Infinite canvas pan/zoom',
      '- [ ] Place text on click',
      '- [ ] Smoke: npm run dev',
    ],
  },
  {
    id: 'tick',
    label: '5 · Work lands',
    tool: 'complete_task',
    args: 'version="v0.1.1", task="Infinite canvas"',
    planLines: [
      '### v0.1.1 — Canvas (current)',
      '- [x] Infinite canvas pan/zoom',
      '- [ ] Place text on click',
      '- [ ] Smoke: npm run dev',
    ],
  },
  {
    id: 'scoped',
    label: '6 · Agent reads scoped JSON',
    tool: 'get_current_iteration',
    args: '(no full PLAN.md read)',
    planLines: [
      '### v0.1.1 — Canvas (current)',
      '- [x] Infinite canvas pan/zoom',
      '- [ ] Place text on click',
      '- [ ] Smoke: npm run dev',
    ],
    side: `{
  "current": {
    "version": "v0.1.1",
    "title": "Canvas (current)",
    "progress": { "done": 1, "total": 3 },
    "tasks": [
      { "text": "Infinite canvas pan/zoom", "done": true },
      { "text": "Place text on click", "done": false },
      { "text": "Smoke: npm run dev", "done": false }
    ]
  }
}`,
  },
]

function PlanPane({ lines, highlightDone }: { lines: string[]; highlightDone?: boolean }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-[#0a101c] overflow-hidden h-full">
      <div className="px-3 py-1.5 border-b border-slate-800 text-[10px] mono text-slate-500">
        PLAN.md
      </div>
      <pre className="p-3 mono text-[11px] md:text-xs leading-relaxed text-slate-300 overflow-auto max-h-[280px]">
        {lines.map((ln, i) => {
          const done = highlightDone && ln.includes('- [x]')
          const open = ln.includes('- [ ]')
          return (
            <div
              key={i}
              className={
                done ? 'text-emerald-400' : open ? 'text-amber-200/90' : 'text-slate-300'
              }
            >
              {ln || '\u00A0'}
            </div>
          )
        })}
      </pre>
    </div>
  )
}

export function AgentStory() {
  const sectionRef = useRef<HTMLElement>(null)
  const inView = useInView(sectionRef, { once: false, margin: '-20%' })
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ['start end', 'end start'],
  })

  const frameIndexMotion = useTransform(scrollYProgress, [0.15, 0.85], [0, FRAMES.length - 1])
  const [frame, setFrame] = useState(0)
  const [auto, setAuto] = useState(true)

  useEffect(() => {
    const unsub = frameIndexMotion.on('change', (v) => {
      if (!auto) return
      setFrame(Math.min(FRAMES.length - 1, Math.max(0, Math.round(v))))
    })
    return unsub
  }, [frameIndexMotion, auto])

  // Autoplay when in view and user hasn't scrubbed via chips
  useEffect(() => {
    if (!inView || !auto) return
    const id = window.setInterval(() => {
      setFrame((f) => (f + 1) % FRAMES.length)
    }, 2800)
    return () => window.clearInterval(id)
  }, [inView, auto])

  const f = FRAMES[frame]
  const reduced = useMemo(() => {
    if (typeof window === 'undefined') return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }, [])

  return (
    <section
      id="story"
      ref={sectionRef}
      className="py-24 px-4 bg-gradient-to-b from-violet-950/25 via-transparent to-transparent"
    >
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <div className="inline-flex text-xs mono px-3 py-1 rounded-full border border-violet-500/40 text-violet-300 bg-violet-500/10 mb-4">
            AGENT × MCP × PLAN
          </div>
          <h2 className="text-4xl font-bold text-white mb-3">How an agent extends the plan</h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            Scroll or watch the loop: tool calls on the left, PLAN.md on the right.
            {reduced ? ' (reduced motion: step with the chips below)' : ''}
          </p>
        </div>

        {/* Step chips */}
        <div className="flex flex-wrap justify-center gap-2 mb-8">
          {FRAMES.map((fr, i) => (
            <button
              key={fr.id}
              type="button"
              onClick={() => {
                setAuto(false)
                setFrame(i)
              }}
              className={`px-3 py-1.5 rounded-full text-xs mono border transition-colors ${
                i === frame
                  ? 'border-sky-400 bg-sky-500/20 text-sky-200'
                  : 'border-slate-700 text-slate-400 hover:border-slate-500'
              }`}
            >
              {fr.label}
            </button>
          ))}
        </div>

        <div className="grid lg:grid-cols-2 gap-6 items-stretch">
          <motion.div
            key={f.id + '-tool'}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: reduced ? 0 : 0.35 }}
            className="rounded-xl border border-slate-700 bg-[var(--pp-card)] p-5"
          >
            <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">
              MCP tool call
            </div>
            <div className="mono text-sky-300 text-lg mb-2">{f.tool}</div>
            <div className="mono text-sm text-slate-400 mb-6">{f.args}</div>
            {f.side ? (
              <>
                <div className="text-[10px] uppercase tracking-wider text-emerald-500/80 mb-2">
                  Tool result (scoped — not the whole file)
                </div>
                <pre className="mono text-[11px] text-emerald-200/90 bg-black/30 rounded-lg p-3 overflow-auto max-h-[240px] border border-emerald-900/40">
                  {f.side}
                </pre>
              </>
            ) : (
              <div className="text-sm text-slate-500">
                Coordinator never hand-edits PLAN.md — powerplan is the single writer.
              </div>
            )}
          </motion.div>

          <motion.div
            key={f.id + '-plan'}
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: reduced ? 0 : 0.35 }}
          >
            <PlanPane lines={f.planLines} highlightDone />
          </motion.div>
        </div>

        <p className="text-center text-xs text-slate-500 mt-8 mono">
          create_plan → create_iteration → add_task → complete_task → get_current_iteration
        </p>
      </div>
    </section>
  )
}
