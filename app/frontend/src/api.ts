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
  scenes: Scene[]
}

export interface IdeaNode {
  id: string
  project_id: string
  parent_id: string | null
  depth: number
  title: string
  summary: string
  hook: string
  conflict: string
  cliffhanger: string
  status: string
  created_at: string
}

export interface IdeaTree {
  root_id: string | null
  nodes: Record<string, IdeaNode>
  active_node_id: string | null
  selected_story_node_id: string | null
}

export interface Scene {
  scene_id: string
  order: number
  title: string
  purpose: string
  duration_seconds: number
  image_prompt: string
  motion_prompt: string
  narration: string
  subtitle_text: string
  image_path: string | null
  video_path: string | null
  audio_path: string | null
  status: Record<string, string>
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
    }),
  getIdeas: (projectId: string) => req<IdeaTree>(`/api/projects/${projectId}/ideas`),
  generateRootIdeas: (projectId: string, idea: string, style: string, count: number) =>
    req<{ created: IdeaNode[]; tree: IdeaTree }>(`/api/projects/${projectId}/ideas/root`, {
      method: 'POST',
      body: JSON.stringify({ idea, style, count })
    }),
  generateChildren: (projectId: string, nodeId: string, count: number) =>
    req<{ created: IdeaNode[]; tree: IdeaTree }>(
      `/api/projects/${projectId}/ideas/${nodeId}/children`,
      { method: 'POST', body: JSON.stringify({ count }) }
    ),
  setIdeaStatus: (projectId: string, nodeId: string, status: string) =>
    req<IdeaNode>(`/api/projects/${projectId}/ideas/${nodeId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status })
    }),
  materialize: (projectId: string, nodeId: string, sceneCount: number, style: string) =>
    req<StoryPlan>(`/api/projects/${projectId}/story/materialize`, {
      method: 'POST',
      body: JSON.stringify({ node_id: nodeId, scene_count: sceneCount, style })
    }),
  continueStory: (projectId: string, extraScenes: number, style: string) =>
    req<StoryPlan>(`/api/projects/${projectId}/story/continue`, {
      method: 'POST',
      body: JSON.stringify({ extra_scenes: extraScenes, style })
    }),
  systemStatus: () => req<Record<string, { ok: boolean; hint?: string }>>('/api/system/status'),
  genImage: (projectId: string, sceneId: string, prompt: string, preset = 'draft', model = 'sdxl') =>
    req<{ file: string }>(`/api/projects/${projectId}/scenes/${sceneId}/image`, {
      method: 'POST',
      body: JSON.stringify({ prompt, preset, model })
    }),
  genVideo: (
    projectId: string,
    sceneId: string,
    motionPrompt: string,
    preset = 'subtle',
    backend = 'wan_i2v',
    wan?: {
      mode?: string
      seconds?: number
      seed?: number
      teacache?: number
      interpolate?: boolean
      upscaler?: string
    }
  ) =>
    req<{ file: string; bytes: number; backend: string }>(`/api/projects/${projectId}/scenes/${sceneId}/video`, {
      method: 'POST',
      body: JSON.stringify({
        motion_prompt: motionPrompt,
        preset,
        backend,
        mode: wan?.mode ?? 'fast',
        seconds: wan?.seconds ?? 3,
        seed: wan?.seed,
        teacache: wan?.teacache ?? -1,
        interpolate: wan?.interpolate ?? true,
        upscaler: wan?.upscaler ?? 'anime'
      })
    }),
  videoBackends: () => req<{ default: string; backends: { name: string; label: string; role: string; notes: string }[] }>('/api/system/video-backends'),
  narrate: (projectId: string, sceneId: string, text: string) =>
    req<{ ok: boolean }>(`/api/projects/${projectId}/scenes/${sceneId}/narration`, {
      method: 'POST',
      body: JSON.stringify({ text, language: 'es' })
    }),
  transcribe: (projectId: string, sceneId: string) =>
    req<{ ok: boolean; words: number }>(`/api/projects/${projectId}/scenes/${sceneId}/subtitles`, {
      method: 'POST',
      body: JSON.stringify({ language: 'es' })
    }),
  makeAss: (projectId: string, sceneId: string, style = 'classic') =>
    req<{ ok: boolean; blocks: unknown[] }>(`/api/projects/${projectId}/scenes/${sceneId}/subtitles/ass`, {
      method: 'POST',
      body: JSON.stringify({ style })
    }),
  render: (projectId: string) =>
    req<{ ok: boolean; seconds: number }>(`/api/projects/${projectId}/render`, {
      method: 'POST'
    }),
  sceneUrls: (projectId: string, sceneId: string) => ({
    image: `/api/projects/${projectId}/scenes/${sceneId}/image`,
    clip: `/api/projects/${projectId}/scenes/${sceneId}/clip`,
    narration: `/api/projects/${projectId}/scenes/${sceneId}/narration`
  }),
  renderUrl: (projectId: string) => `/api/projects/${projectId}/render`
}
