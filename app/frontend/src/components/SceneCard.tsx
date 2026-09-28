import { useState } from 'react'
import { api, type Scene } from '../api'

interface Props {
  projectId: string
  scene: Scene
}

export default function SceneCard({ projectId, scene }: Props) {
  const [busy, setBusy] = useState('')
  const [msg, setMsg] = useState('')
  const [status, setStatus] = useState<Record<string, string>>(scene.status || {})
  const urls = api.sceneUrls(projectId, scene.scene_id)

  async function run(label: string, fn: () => Promise<unknown>, doneKey?: string) {
    setBusy(label)
    setMsg('')
    try {
      const res = (await fn()) as { file?: string; words?: number; seconds?: number }
      if (doneKey) setStatus((s) => ({ ...s, [doneKey]: 'done' }))
      setMsg(
        `OK${res.file ? ': ' + res.file : ''}${res.words ? ': ' + res.words + ' palabras' : ''}`
      )
    } catch (e) {
      setMsg(`Error: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setBusy('')
    }
  }

  const st = (k: string) => status[k] || 'pending'

  return (
    <li style={{ marginBottom: 12, border: '1px solid #ddd', borderRadius: 8, padding: 8 }}>
      <strong>
        {scene.order}. {scene.title}
      </strong>{' '}
      <small>({scene.duration_seconds}s)</small>
      <p>
        <em>{scene.purpose}</em>
      </p>
      <p>
        <small>
          🖼 {st('image')} · 🎬 {st('video')} · 🎙 {st('audio')} · 💬 {st('subtitle')}
        </small>
      </p>
      <details>
        <summary>Prompts y narración</summary>
        <p>
          <strong>🖼 Imagen (EN):</strong> {scene.image_prompt}
        </p>
        <p>
          <strong>🎬 Motion (EN):</strong> {scene.motion_prompt}
        </p>
        <p>
          <strong>🎙 Narración:</strong> {scene.narration}
        </p>
      </details>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
        <button
          disabled={busy !== ''}
          onClick={() => run('Generando imagen… (minutos)', () => api.genImage(projectId, scene.scene_id, scene.image_prompt), 'image')}
        >
          🖼 Imagen
        </button>
        <button
          disabled={busy !== ''}
          onClick={() => run('Generando video… (minutos)', () => api.genVideo(projectId, scene.scene_id, scene.motion_prompt), 'video')}
        >
          🎬 Video
        </button>
        <button
          disabled={busy !== ''}
          onClick={() => run('Narrando…', () => api.narrate(projectId, scene.scene_id, scene.narration), 'audio')}
        >
          🎙 Narrar
        </button>
        <button
          disabled={busy !== ''}
          onClick={() =>
            run('Transcribiendo…', async () => {
              const t = await api.transcribe(projectId, scene.scene_id)
              await api.makeAss(projectId, scene.scene_id)
              return t
            }, 'subtitle')
          }
        >
          💬 Subtítulos
        </button>
      </div>
      {busy && <p>⏳ {busy}</p>}
      {msg && <p>{msg}</p>}
      <div style={{ display: 'flex', gap: 12, marginTop: 6, flexWrap: 'wrap' }}>
        {st('image') === 'done' && (
          <a href={urls.image} target="_blank" rel="noreferrer">
            ver imagen
          </a>
        )}
        {st('video') === 'done' && (
          <a href={urls.clip} target="_blank" rel="noreferrer">
            ver clip
          </a>
        )}
        {st('audio') === 'done' && (
          <audio controls src={urls.narration} style={{ height: 32 }} />
        )}
      </div>
    </li>
  )
}
