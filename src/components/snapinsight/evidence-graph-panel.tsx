"use client"

import dynamic from "next/dynamic"
import { useEffect, useMemo, useState } from "react"
import { ChevronDown, ChevronUp, GitBranch, Loader2 } from "lucide-react"

import type {
  AnalysisResponse,
  GraphNode,
  ProductGraphResponse,
} from "@/lib/snapinsight-api"
import { fetchProductGraph } from "@/lib/snapinsight-api"

const EvidenceGraphFlow = dynamic(
  () =>
    import("@/components/snapinsight/evidence-graph-flow").then(
      (module) => module.EvidenceGraphFlow
    ),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[320px] items-center justify-center rounded-2xl border border-white/10 bg-slate-950/60">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading evidence graph…
        </div>
      </div>
    ),
  }
)

interface EvidenceGraphPanelProps {
  analysis: AnalysisResponse
}

function getBackendLabel(backend: ProductGraphResponse["graph_backend"]): string {
  if (backend === "neo4j") return "Neo4j Aura"
  if (backend === "neo4j_fallback") return "In-memory (Neo4j unavailable)"
  return "In-memory"
}

function pathsForNode(
  graph: ProductGraphResponse | null,
  node: GraphNode | null
): ProductGraphResponse["evidence_paths"] {
  if (!graph || !node) return []
  return graph.evidence_paths.filter((path) =>
    path.steps.some((step) => step.node_id === node.id)
  )
}

export function EvidenceGraphPanel({ analysis }: EvidenceGraphPanelProps) {
  const [expanded, setExpanded] = useState(() => {
    if (typeof window === "undefined") return false
    return window.matchMedia("(min-width: 768px)").matches
  })
  const [graph, setGraph] = useState<ProductGraphResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)

  useEffect(() => {
    const desktop = window.matchMedia("(min-width: 768px)")
    const onChange = () => setExpanded(desktop.matches)
    desktop.addEventListener("change", onChange)
    return () => desktop.removeEventListener("change", onChange)
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    let active = true

    queueMicrotask(() => {
      if (!active) return
      setLoading(true)
      setError(null)
      setGraph(null)
      setSelectedNode(null)
    })

    fetchProductGraph(analysis, controller.signal)
      .then((response) => {
        if (!active) return
        setGraph(response)
      })
      .catch((fetchError: unknown) => {
        if (!active || controller.signal.aborted) return
        const message =
          fetchError instanceof Error
            ? fetchError.message
            : "Evidence graph unavailable."
        setError(message)
      })
      .finally(() => {
        if (active && !controller.signal.aborted) setLoading(false)
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [analysis])

  const relatedPaths = useMemo(
    () => pathsForNode(graph, selectedNode),
    [graph, selectedNode]
  )

  return (
    <section className="glass-card mt-5 overflow-hidden">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-3 p-5 text-left"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-2">
          <GitBranch className="h-4 w-4 text-violet-300" />
          <h3 className="text-sm font-semibold text-foreground">Evidence Graph</h3>
          {graph && (
            <span className="rounded-full border border-white/10 bg-slate-800/70 px-2 py-0.5 text-[10px] text-muted-foreground">
              {getBackendLabel(graph.graph_backend)}
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        )}
      </button>

      {expanded && (
        <div className="space-y-4 border-t border-white/5 px-5 pb-5">
          {loading && (
            <div className="flex h-[320px] items-center justify-center rounded-2xl border border-white/10 bg-slate-950/60">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Building evidence graph…
              </div>
            </div>
          )}

          {!loading && error && (
            <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-200">
              {error}
            </div>
          )}

          {!loading && !error && graph && graph.nodes.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No graph nodes available for this analysis yet.
            </p>
          )}

          {!loading && !error && graph && graph.nodes.length > 0 && (
            <>
              <EvidenceGraphFlow
                graph={graph}
                selectedNodeId={selectedNode?.id ?? null}
                onSelectNode={setSelectedNode}
              />

              {graph.evidence_paths.length > 0 && (
                <div className="rounded-2xl border border-white/5 bg-slate-800/40 p-3">
                  <p className="mono-label mb-2 text-muted-foreground">
                    GraphRAG evidence paths
                  </p>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    {graph.evidence_paths.slice(0, 4).map((path) => (
                      <li
                        key={path.id}
                        className="rounded-xl bg-slate-900/50 px-3 py-2 text-foreground/90"
                      >
                        {path.summary}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedNode && (
                <div className="rounded-2xl border border-violet-500/25 bg-violet-500/10 p-4">
                  <p className="mono-label mb-1 text-violet-200">
                    {selectedNode.type}
                  </p>
                  <p className="text-sm font-medium text-foreground">
                    {selectedNode.label}
                  </p>
                  {selectedNode.detail && (
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                      {selectedNode.detail}
                    </p>
                  )}
                  {selectedNode.url && (
                    <a
                      href={selectedNode.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-flex text-xs font-medium text-violet-300 hover:text-violet-200"
                    >
                      View OpenFoodFacts source
                    </a>
                  )}
                  {relatedPaths.length > 0 && (
                    <div className="mt-3 space-y-2">
                      <p className="text-xs font-medium text-violet-200">
                        Linked evidence paths
                      </p>
                      {relatedPaths.map((path) => (
                        <p
                          key={path.id}
                          className="text-xs leading-relaxed text-violet-100/80"
                        >
                          {path.summary}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </section>
  )
}
