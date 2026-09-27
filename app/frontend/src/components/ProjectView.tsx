import { useEffect, useState } from 'react'
import { api, type Project, type StoryPlan } from '../api'

interface Props {
  project: Project
  onBack: () => void
}

export default function ProjectView({ project, onBack }: Props) {
  const [plan, setPlan] = useState<StoryPlan | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .getStoryPlan(project.id)
      .then(setPlan)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [project.id])

  return (
    <section>
      <button onClick={onBack}>← Volver al dashboard</button>
      <h2>{project.title}</h2>
      <p>
        <small>
          {project.settings.scene_count} escenas · {project.settings.style} ·{' '}
          {project.settings.target_duration_seconds}s objetivo
        </small>
      </p>

      <h3>Idea Lab (vista previa — árbol completo en Phase 7)</h3>
      {error && <p style={{ color: 'crimson' }}>Error: {error}</p>}
      {plan === null ? (
        <p>Cargando story plan…</p>
      ) : (
        <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12 }}>
          <p>
            <strong>Hook:</strong> {plan.hook || <em>pendiente (Phase 5/8)</em>}
          </p>
          <p>
            <strong>Resumen:</strong> {plan.summary || <em>pendiente</em>}
          </p>
          <p>
            <strong>Cliffhanger:</strong> {plan.cliffhanger || <em>pendiente</em>}
          </p>
          <p>
            <strong>Escenas:</strong> {plan.scenes.length}
          </p>
        </div>
      )}

      <h3>Etapas del pipeline</h3>
      <ol>
        <li>Idea Lab / árbol de ideas → Phase 5–7</li>
        <li>Scene Planner → Phase 8</li>
        <li>Image Studio → Phase 10</li>
        <li>Motion Studio → Phase 12</li>
        <li>Voice Lab → Phase 14</li>
        <li>Caption Studio → Phase 15–16</li>
        <li>Final Render → Phase 17</li>
      </ol>
    </section>
  )
}
