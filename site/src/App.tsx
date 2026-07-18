import { Hero } from './components/Hero'
import { HowItWorks } from './components/HowItWorks'
import { Tools } from './components/Tools'
import { Integration } from './components/Integration'
import { Principles } from './components/Principles'
import { Footer } from './components/Footer'

function App() {
  return (
    <div className="min-h-screen bg-[var(--pp-bg)]">
      <Hero />
      <HowItWorks />
      <Tools />
      <Principles />
      <Integration />
      <Footer />
    </div>
  )
}

export default App
