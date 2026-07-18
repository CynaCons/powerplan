import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef, useState } from 'react'

const snippets = {
  mcp: `{
  "mcpServers": {
    "powerplan": {
      "command": "python",
      "args": ["-m", "powerplan"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}`,
  usage: `# Every tool accepts optional plan_path (default = walk-up from cwd)

create_plan(title="My App", goal="Ship MVP")
  → writes ./PLAN.md if missing

get_current_iteration()
  → scoped JSON for what to work on now

add_task(version="v0.1.0", text="Wire auth", plan_path="docs/PLAN.md")
  → explicit path when not at repo root

complete_task(version="v0.1.0", task="Wire auth", agent="grok-4.5")`,
  dual: `{
  "mcpServers": {
    "powerplan": {
      "command": "python",
      "args": ["-m", "powerplan"]
    },
    "powerspawn": {
      "command": "python",
      "args": ["-m", "powerspawn.mcp_server"]
    }
  }
}`,
  grok: `[mcp_servers.powerplan]
command = "python"
args = ["-m", "powerplan"]
env = { PYTHONUNBUFFERED = "1" }
enabled = true`,
  submodule: `# PowerSpawn vendors powerplan as a submodule
git submodule update --init --recursive
# Register BOTH MCP servers — they do not merge`,
}

function Block({ title, code }: { title: string; code: string }) {
  const [ok, setOk] = useState(false)
  return (
    <div className="rounded-xl border border-slate-800 bg-[#0f1628] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800">
        <span className="text-sm text-slate-400">{title}</span>
        <button
          type="button"
          className="text-xs px-2 py-1 rounded bg-slate-700 hover:bg-slate-600"
          onClick={() => {
            navigator.clipboard.writeText(code)
            setOk(true)
            setTimeout(() => setOk(false), 1500)
          }}
        >
          {ok ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="p-4 mono text-xs md:text-sm text-slate-300 overflow-x-auto leading-relaxed">
        {code}
      </pre>
    </div>
  )
}

export function Integration() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })

  return (
    <section id="integrate" className="py-24 px-4 bg-gradient-to-b from-violet-950/20 to-transparent">
      <div className="max-w-4xl mx-auto" ref={ref}>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-12"
        >
          <h2 className="text-4xl font-bold text-white mb-3">Integrate in your projects</h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            powerplan is a <strong className="text-slate-200">standalone</strong> MCP. PowerSpawn can
            vendor it as a <strong className="text-slate-200">submodule</strong> so spawn-based
            projects get both — still registered as two servers.
          </p>
        </motion.div>

        <div className="space-y-6">
          <Block title="Project .mcp.json (Claude Code & friends)" code={snippets.mcp} />
          <Block title="Agent flow: create_plan + plan_path" code={snippets.usage} />
          <Block title="With PowerSpawn (peer MCP servers)" code={snippets.dual} />
          <Block title="Grok config.toml" code={snippets.grok} />
          <Block title="PowerSpawn submodule init" code={snippets.submodule} />
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ delay: 0.3 }}
          className="mt-10 text-center text-sm text-slate-500"
        >
          Standalone repo:{' '}
          <a className="text-sky-400 hover:underline" href="https://github.com/CynaCons/powerplan">
            github.com/CynaCons/powerplan
          </a>
          {' · '}
          Pairs with{' '}
          <a className="text-sky-400 hover:underline" href="https://github.com/CynaCons/PowerSpawn">
            PowerSpawn
          </a>
        </motion.p>
      </div>
    </section>
  )
}
