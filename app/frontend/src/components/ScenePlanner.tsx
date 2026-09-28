import { useState } from 'react'
import { api, type StoryPlan } from '../api'
import SceneCard from './SceneCard'

interface Props {
  projectId: string
  style: string
  plan: StoryPlan | null
  onPlan: (plan: StoryPlan) => void
}

export default function ScenePlanner({ projectId, style, plan, onPlan }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [extra, setExtra] = useState(2)
  const [renderMsg, setRenderMsg] = useState('')

  async function cont() {
    setBusy(true)
    setError('')
    try {
      onPlan(await api.continueStory(projectId, extra, style))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function doRender() {
    setBusy(true)
    setRenderMsg('Renderizando final… (minutos)')
    try {
      const res = await api.render(projectId)
      setRenderMsg(`Final listo: ${res.seconds}s — míralo abajo.`)
    } catch (e) {
      setRenderMsg(`Error: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setBusy(false)
    }
  }

  if (!plan || plan.scenes.length === 0) {
    return (
      <section>
        <h3>Scene Planner</h3>
        <p>
          <em>Sin historia todavía. Elige una rama en el Idea Lab y pulsa “Usar esta rama”.</em>
        </p>
      </section>
    )
  }

  return (
    <section>
      <h3>Scene Planner — {plan.scenes.length} escenas</h3>
      <p>
        <strong>Hook:</strong> {plan.hook}
      </p>
      <p>
        <strong>Cliffhanger:</strong> {plan.cliffhanger}
      </p>
      {error && <p style={{ color: 'crimson' }}>Error: {error}</p>}
      <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
        <label>
          Extra:{' '}
          <input
            type="number"
            min={1}
            max={6}
            value={extra}
            onChange={(e) => setExtra(Number(e.target.value))}
            style={{ width: 56, padding: 6 }}
          />
        </label>
        <button disabled={busy} onClick={cont}>
          {busy ? 'Continuando… (minutos)' : 'Continue Story +'}
        </button>
        <button disabled={busy} onClick={doRender} style={{ fontWeight: 'bold' }}>
          🎞 Export final 9:16
        </button>
        <a href={api.renderUrl(projectId)} target="_blank" rel="noreferrer">
          descargar final.mp4
        </a>
      </div>
      {renderMsg && <p>{renderMsg}</p>}
      <ol style={{ paddingLeft: 20 }}>
        {plan.scenes.map((s) => (
          <SceneCard key={s.scene_id} projectId={projectId} scene={s} />
        ))}
      </ol>
    </section>
  )
}
