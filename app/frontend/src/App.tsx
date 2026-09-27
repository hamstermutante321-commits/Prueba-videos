import { useEffect, useState } from 'react'

export default function App() {
  const [health, setHealth] = useState('checking...')

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then((j) => setHealth(JSON.stringify(j)))
      .catch(() => setHealth('backend offline (vite proxy -> 127.0.0.1:8000)'))
  }, [])

  return (
    <div style={{ fontFamily: 'system-ui', padding: 24, maxWidth: 720 }}>
      <h1>StoryForge Local Studio</h1>
      <p>Phase 1 — esqueleto frontend + backend conectados por /api.</p>
      <p>
        <strong>Backend health:</strong> <code>{health}</code>
      </p>
      <ol>
        <li>Idea Lab / árbol de ideas (Phase 7)</li>
        <li>Scene Planner, Image/Motion Studio</li>
        <li>Voice Lab, Caption Studio, Final Render</li>
      </ol>
    </div>
  )
}
