import { useEffect, useMemo, useState } from 'react'
import { api, type IdeaNode, type IdeaTree, type StoryPlan } from '../api'

interface Props {
  projectId: string
  style: string
  onStory: (plan: StoryPlan) => void
}

const STATUS_LABEL: Record<string, string> = {
  pending: 'Pendiente',
  active: 'Activa',
  favorite: '★ Favorita',
  archived: 'Archivada',
  discarded: 'Descartada',
  selected_for_story: '✓ En historia'
}

export default function IdeaLab({ projectId, style, onStory }: Props) {
  const [tree, setTree] = useState<IdeaTree | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [idea, setIdea] = useState('')
  const [count, setCount] = useState(4)
  const [sceneCount, setSceneCount] = useState(6)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  async function load() {
    setError('')
    try {
      const t = await api.getIdeas(projectId)
      setTree(t)
      if (!selectedId && t.root_id) setSelectedId(t.root_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const nodes = useMemo(() => (tree ? Object.values(tree.nodes) : []), [tree])
  const selected: IdeaNode | null =
    (selectedId && tree?.nodes[selectedId]) || null

  function childrenOf(id: string | null): IdeaNode[] {
    return nodes
      .filter((n) => n.parent_id === id)
      .sort((a, b) => a.created_at.localeCompare(b.created_at))
  }

  function breadcrumb(node: IdeaNode): IdeaNode[] {
    const chain: IdeaNode[] = []
    let cur: IdeaNode | undefined = node
    while (cur && tree) {
      chain.unshift(cur)
      cur = cur.parent_id ? tree.nodes[cur.parent_id] : undefined
    }
    return chain
  }

  async function run(label: string, fn: () => Promise<IdeaTree | { tree: IdeaTree }>) {
    setBusy(label)
    setError('')
    try {
      const res = await fn()
      const t = 'tree' in res ? res.tree : res
      setTree(t)
      if (selectedId && !t.nodes[selectedId]) setSelectedId(t.root_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy('')
    }
  }

  async function materialize() {
    if (!selected) return
    setBusy('Convirtiendo rama en historia… (puede tardar minutos)')
    setError('')
    try {
      const plan = await api.materialize(projectId, selected.id, sceneCount, style)
      onStory(plan)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy('')
    }
  }

  function renderBranch(parentId: string | null, depth: number): React.ReactNode {
    return childrenOf(parentId).map((n) => (
      <div key={n.id} style={{ marginLeft: depth * 18, marginTop: 4 }}>
        <button
          onClick={() => setSelectedId(n.id)}
          style={{
            background: n.id === selectedId ? '#e8f0fe' : 'none',
            border: '1px solid #ccc',
            borderRadius: 6,
            cursor: 'pointer',
            padding: '4px 8px',
            textAlign: 'left',
            maxWidth: '100%'
          }}
        >
          <strong>
            {n.depth === 0 ? '🌱 ' : '↳ '}
            {n.title}
          </strong>{' '}
          <small>[{STATUS_LABEL[n.status] || n.status}]</small>
        </button>
        {renderBranch(n.id, depth + 1)}
      </div>
    ))
  }

  return (
    <section>
      <h3>Idea Lab — árbol de ideas</h3>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
        <input
          placeholder="Idea libre… ej: un joven héroe descubre un secreto en el bosque"
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          style={{ flex: '3 1 280px', padding: 6 }}
        />
        <label>
          Ideas:{' '}
          <input
            type="number"
            min={1}
            max={8}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            style={{ width: 56, padding: 6 }}
          />
        </label>
        <button
          disabled={busy !== '' || idea.trim().length < 3}
          onClick={() =>
            run('Generando ideas… (puede tardar minutos)', () =>
              api.generateRootIdeas(projectId, idea.trim(), style, count)
            )
          }
        >
          Generar ideas
        </button>
        <button disabled={busy !== ''} onClick={load}>
          Recargar
        </button>
      </div>
      {busy && <p>⏳ {busy}</p>}
      {error && <p style={{ color: 'crimson' }}>Error: {error}</p>}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 280px', border: '1px solid #ddd', borderRadius: 8, padding: 8 }}>
          <strong>Árbol</strong>
          {tree?.root_id ? (
            renderBranch(null, 0)
          ) : (
            <p>
              <em>Vacío. Genera las primeras ideas arriba.</em>
            </p>
          )}
        </div>
        <div style={{ flex: '2 1 320px', border: '1px solid #ddd', borderRadius: 8, padding: 12 }}>
          {selected ? (
            <>
              <p>
                {breadcrumb(selected).map((b, i) => (
                  <span key={b.id}>
                    {i > 0 && ' → '}
                    <button
                      onClick={() => setSelectedId(b.id)}
                      style={{ background: 'none', border: 'none', color: '#0366d6', cursor: 'pointer', padding: 0 }}
                    >
                      {b.title.slice(0, 30)}
                    </button>
                  </span>
                ))}
              </p>
              <h4>{selected.title}</h4>
              <p>{selected.summary}</p>
              {selected.hook && (
                <p>
                  <strong>Hook:</strong> {selected.hook}
                </p>
              )}
              {selected.conflict && (
                <p>
                  <strong>Conflicto:</strong> {selected.conflict}
                </p>
              )}
              {selected.cliffhanger && (
                <p>
                  <strong>Cliffhanger:</strong> {selected.cliffhanger}
                </p>
              )}
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                <button
                  disabled={busy !== ''}
                  onClick={() =>
                    run('Generando subideas…', () =>
                      api.generateChildren(projectId, selected.id, count)
                    )
                  }
                >
                  Generar subideas
                </button>
                {selected.parent_id && (
                  <button
                    disabled={busy !== ''}
                    onClick={() => {
                      const parent = tree?.nodes[selected.parent_id!]
                      if (parent?.parent_id !== undefined) {
                        const pid = parent.parent_id
                        void run('Generando hermanas…', () =>
                          pid
                            ? api.generateChildren(projectId, pid, count)
                            : api.generateRootIdeas(projectId, idea.trim() || selected.title, style, count)
                        )
                      }
                    }}
                  >
                    Más hermanas
                  </button>
                )}
                {(['pending', 'favorite', 'archived', 'active'] as const).map((s) => (
                  <button
                    key={s}
                    disabled={busy !== '' || selected.status === s}
                    onClick={() =>
                      run('', async () => {
                        await api.setIdeaStatus(projectId, selected.id, s)
                        return api.getIdeas(projectId)
                      })
                    }
                  >
                    {s === 'pending' ? 'Dejar pendiente' : STATUS_LABEL[s]}
                  </button>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 6, marginTop: 12, alignItems: 'center' }}>
                <label>
                  Escenas:{' '}
                  <input
                    type="number"
                    min={1}
                    max={12}
                    value={sceneCount}
                    onChange={(e) => setSceneCount(Number(e.target.value))}
                    style={{ width: 56, padding: 6 }}
                  />
                </label>
                <button disabled={busy !== ''} onClick={materialize} style={{ fontWeight: 'bold' }}>
                  Usar esta rama →
                </button>
              </div>
            </>
          ) : (
            <p>
              <em>Selecciona un nodo del árbol.</em>
            </p>
          )}
        </div>
      </div>
    </section>
  )
}
