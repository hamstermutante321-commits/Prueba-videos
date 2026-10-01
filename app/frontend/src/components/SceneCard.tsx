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
  const [backend, setBackend] = useState('wan_i2v')
  const [mode, setMode] = useState('fast')
  const [seconds, setSeconds] = useState(3)
  const [seed, setSeed] = useState('')
  const [teacache, setTeacache] = useState('default')
  const [interp, setInterp] = useState(true)
  const [upscaler, setUpscaler] = useState('anime')
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
          onClick={() =>
            run('Generando video… (minutos)', () =>
              api.genVideo(projectId, scene.scene_id, scene.motion_prompt, 'subtle', backend, {
                mode,
                seconds,
                seed: seed === '' ? undefined : Number(seed),
                teacache: teacache === 'default' ? undefined : teacache === 'off' ? 0 : Number(teacache),
                interpolate: interp,
                upscaler
              }), 'video')
          }
        >
          🎬 Video
        </button>
        <select value={backend} onChange={(e) => setBackend(e.target.value)} title="Backend image-to-video">
          <option value="wan_i2v">Wan 2.2 (recomendado)</option>
          <option value="cogvideox_i2v">CogVideoX-5B</option>
          <option value="framepack">FramePack (no instalado)</option>
          <option value="ltx">LTX (deprecated)</option>
        </select>
        {backend === 'wan_i2v' && (
          <>
            <select value={mode} onChange={(e) => setMode(e.target.value)} title="Mode">
              <option value="fast">FAST</option>
              <option value="final">FINAL</option>
            </select>
            <label title="Duración">
              <input
                type="number" min={1} max={6} step={0.5} value={seconds}
                onChange={(e) => setSeconds(Number(e.target.value))}
                style={{ width: 52 }} />s
            </label>
            <label title="Seed (vacío = aleatorio)">
              Seed:<input
                value={seed} onChange={(e) => setSeed(e.target.value)}
                placeholder="auto" style={{ width: 70 }} />
            </label>
            <select value={teacache} onChange={(e) => setTeacache(e.target.value)} title="TeaCache">
              <option value="default">TeaCache auto</option>
              <option value="off">TeaCache off</option>
              <option value="0.2">TeaCache 0.2</option>
              <option value="0.4">TeaCache 0.4</option>
            </select>
            <label title="Frame interpolation (FINAL)">
              <input type="checkbox" checked={interp} onChange={(e) => setInterp(e.target.checked)} />RIFE
            </label>
            <select value={upscaler} onChange={(e) => setUpscaler(e.target.value)} title="Upscaler (FINAL)">
              <option value="anime">UP: Anime</option>
              <option value="general">UP: General</option>
              <option value="none">UP: None</option>
            </select>
          </>
        )}
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
