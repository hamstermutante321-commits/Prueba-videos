import { useEffect, useState } from 'react'
import { api, type Project, type StoryPlan } from '../api'
import IdeaLab from './IdeaLab'
import ScenePlanner from './ScenePlanner'

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
      {error && <p style={{ color: 'crimson' }}>Error: {error}</p>}
      <IdeaLab projectId={project.id} style={project.settings.style} onStory={setPlan} />
      <hr style={{ margin: '24px 0' }} />
      <ScenePlanner
        projectId={project.id}
        style={project.settings.style}
        plan={plan}
        onPlan={setPlan}
      />
    </section>
  )
}
