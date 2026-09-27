import { useState } from 'react'
import { api, type StoryPlan } from '../api'

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
      <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
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
      </div>
      <ol>
        {plan.scenes.map((s) => (
          <li key={s.scene_id} style={{ marginBottom: 12, border: '1px solid #ddd', borderRadius: 8, padding: 8 }}>
            <strong>
              {s.order}. {s.title}
            </strong>{' '}
            <small>({s.duration_seconds}s)</small>
            <p>
              <em>{s.purpose}</em>
            </p>
            <details>
              <summary>Prompts y narración</summary>
              <p>
                <strong>🖼 Imagen (EN):</strong> {s.image_prompt}
              </p>
              <p>
                <strong>🎬 Motion (EN):</strong> {s.motion_prompt}
              </p>
              <p>
                <strong>🎙 Narración:</strong> {s.narration}
              </p>
            </details>
          </li>
        ))}
      </ol>
    </section>
  )
}
