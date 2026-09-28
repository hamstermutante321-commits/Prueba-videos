import { useEffect, useState } from 'react'
import Dashboard from './components/Dashboard'
import ProjectView from './components/ProjectView'
import VoiceLab from './components/VoiceLab'
import { api, type Project } from './api'

const NAMES: Record<string, string> = {
  ollama: 'Ollama (ideas)',
  comfyui: 'ComfyUI (imagen/video)',
  xtts: 'XTTS (voz)',
  whisperx: 'WhisperX (subtítulos)',
  ffmpeg: 'FFmpeg (render)'
}

export default function App() {
  const [health, setHealth] = useState('checking...')
  const [selected, setSelected] = useState<Project | null>(null)
  const [sys, setSys] = useState<Record<string, { ok: boolean; hint?: string }> | null>(null)

  useEffect(() => {
    api
      .health()
      .then((j) => setHealth(`${j.status} (${j.phase})`))
      .catch(() => setHealth('backend offline (vite proxy -> 127.0.0.1:8000)'))
    api
      .systemStatus()
      .then(setSys)
      .catch(() => setSys(null))
  }, [])

  return (
    <div style={{ fontFamily: 'system-ui', padding: 24, maxWidth: 860, margin: '0 auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap' }}>
        <h1>StoryForge Local Studio</h1>
        <small>
          backend: <code>{health}</code>
        </small>
      </header>
      <section style={{ border: '1px solid #ddd', borderRadius: 8, padding: 8, marginBottom: 16 }}>
        <strong>Sistema:</strong>{' '}
        {sys === null ? (
          <em>cargando…</em>
        ) : (
          Object.entries(NAMES).map(([k, label]) => (
            <span key={k} title={sys[k]?.hint || 'ok'} style={{ marginRight: 12 }}>
              {sys[k]?.ok ? '🟢' : '🔴'} {label}
            </span>
          ))
        )}
      </section>
      {selected === null ? (
        <Dashboard onCreated={setSelected} />
      ) : (
        <>
          <ProjectView project={selected} onBack={() => setSelected(null)} />
          <hr style={{ margin: '24px 0' }} />
          <VoiceLab projectId={selected.id} />
        </>
      )}
    </div>
  )
}
