export function Footer() {
  return (
    <footer className="py-12 px-4 border-t border-slate-800">
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-500">
        <div>
          <span className="text-slate-300 font-semibold">powerplan</span>
          {' '}— PLAN.md MCP for agentic development
        </div>
        <div className="flex gap-4">
          <a href="https://github.com/CynaCons/powerplan" className="hover:text-sky-400">
            GitHub
          </a>
          <a href="https://github.com/CynaCons/powerplan/blob/main/PRD.md" className="hover:text-sky-400">
            PRD
          </a>
          <a href="https://github.com/CynaCons/PowerSpawn" className="hover:text-sky-400">
            PowerSpawn
          </a>
        </div>
      </div>
    </footer>
  )
}
