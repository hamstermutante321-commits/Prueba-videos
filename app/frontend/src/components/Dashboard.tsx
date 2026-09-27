import { useState } from 'react'
import { api, type Project } from '../api'

interface Props {
  onCreated: (p: Project) => void
}

export default function Dashboard({ onCreated }: Props) {
  const [projects, setProjects] = useState<Project[] | null>(null)
  const [error, setError] = useState('')
  const [title, setTitle] = useState('')
  const [style, setStyle] = useState('anime cinematografico')
  const [sceneCount, setSceneCount] = useState(6)
  const [creating, setCreating] = useState(false)

  async function refresh() {
    setError('')
    try {
      setProjects(await api.listProjects())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  if (projects === null && !error) {
    void refresh()
  }

  async function create() {
    if (!title.trim()) return
    setCreating(true)
    setError('')
    try {
      const p = await api.createProject(title.trim(), {
        style,
        scene_count: sceneCount
      })
      setTitle('')
      setProjects(await api.listProjects())
      onCreated(p)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setCreating(false)
    }
  }

  return (
    <section>
      <h2>Dashboard</h2>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
        <input
          placeholder="Título del proyecto"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          style={{ flex: '2 1 200px', padding: 6 }}
        />
        <input
          placeholder="Estilo visual"
          value={style}
          onChange={(e) => setStyle(e.target.value)}
          style={{ flex: '2 1 200px', padding: 6 }}
        />
        <label>
          Escenas:{' '}
          <input
            type="number"
            min={1}
            max={12}
            value={sceneCount}
            onChange={(e) => setSceneCount(Number(e.target.value))}
            style={{ width: 60, padding: 6 }}
          />
        </label>
        <button onClick={create} disabled={creating || !title.trim()}>
          {creating ? 'Creando…' : 'Crear proyecto'}
        </button>
        <button onClick={refresh}>Recargar</button>
      </div>
      {error && <p style={{ color: 'crimson' }}>Error: {error}</p>}
      {projects === null ? (
        <p>Cargando proyectos…</p>
      ) : projects.length === 0 ? (
        <p>No hay proyectos todavía. Crea el primero arriba.</p>
      ) : (
        <ul>
          {projects.map((p) => (
            <li key={p.id}>
              <button
                onClick={() => onCreated(p)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#0366d6', fontSize: 15, padding: 0 }}
              >
                {p.title}
              </button>{' '}
              <small>
                ({p.settings.scene_count} escenas · {p.settings.style})
              </small>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
