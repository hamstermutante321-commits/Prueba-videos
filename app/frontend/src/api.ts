export interface ProjectSettings {
  aspect_ratio: string
  scene_count: number
  style: string
  target_duration_seconds: number
}

export interface Project {
  id: string
  title: string
  created_at: string
  updated_at: string
  settings: ProjectSettings
}

export interface StoryPlan {
  hook: string
  summary: string
  cliffhanger: string
  scenes: unknown[]
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${text}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => req<{ status: string; app: string; phase: string }>('/api/health'),
  listProjects: () => req<Project[]>('/api/projects'),
  getProject: (id: string) => req<Project>(`/api/projects/${id}`),
  getStoryPlan: (id: string) => req<StoryPlan>(`/api/projects/${id}/story-plan`),
  createProject: (title: string, settings?: Partial<ProjectSettings>) =>
    req<Project>('/api/projects', {
      method: 'POST',
      body: JSON.stringify({ title, settings })
    })
}
