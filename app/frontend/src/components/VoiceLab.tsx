import { useEffect, useState } from 'react'

interface Props {
  projectId: string
}

export default function VoiceLab({ projectId }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const [refTick, setRefTick] = useState(0)

  useEffect(() => {
    fetch(`/api/projects/${projectId}/voice/status`)
      .then((r) => r.json())
      .then((j) => {
        if (j.has_reference) setRefTick((t) => t + 1)
        if (!j.model_ready) setMsg(`XTTS no listo: ${(j.missing_files || []).join(', ')}`)
      })
      .catch(() => undefined)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  async function upload() {
    if (!file) return
    setBusy(true)
    setMsg('Subiendo y extrayendo audio…')
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(`/api/projects/${projectId}/voice/reference`, {
        method: 'POST',
        body: fd
      })
      if (!res.ok) throw new Error(await res.text())
      setMsg('Referencia lista ✓ — ya puedes Narrar desde cada escena.')
      setRefTick((t) => t + 1)
    } catch (e) {
      setMsg(`Error: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h3>Voice Lab — clon de voz</h3>
      <p>
        <small>Sube mp4/mp3/wav/m4a con la voz a clonar (se usan ~20 s).</small>
      </p>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          type="file"
          accept=".mp4,.mp3,.wav,.m4a"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <button disabled={busy || !file} onClick={upload}>
          {busy ? 'Procesando…' : 'Subir referencia'}
        </button>
      </div>
      {msg && <p>{msg}</p>}
      {refTick > 0 && (
        <audio controls src={`/api/projects/${projectId}/voice/reference`} style={{ height: 32 }} />
      )}
    </section>
  )
}
