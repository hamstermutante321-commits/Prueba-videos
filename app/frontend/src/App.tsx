import { useEffect, useState } from 'react'
import Dashboard from './components/Dashboard'
import ProjectView from './components/ProjectView'
import { api, type Project } from './api'

export default function App() {
  const [health, setHealth] = useState('checking...')
  const [selected, setSelected] = useState<Project | null>(null)

  useEffect(() => {
    api
      .health()
      .then((j) => setHealth(`${j.status} (${j.phase})`))
      .catch(() => setHealth('backend offline (vite proxy -> 127.0.0.1:8000)'))
  }, [])

  return (
    <div style={{ fontFamily: 'system-ui', padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <h1>StoryForge Local Studio</h1>
        <small>
          backend: <code>{health}</code>
        </small>
      </header>
      {selected === null ? (
        <Dashboard onCreated={setSelected} />
      ) : (
        <ProjectView project={selected} onBack={() => setSelected(null)} />
      )}
    </div>
  )
}
