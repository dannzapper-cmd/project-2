"use client"

import { useCallback, useMemo } from "react"
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
  Handle,
  Position,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

import type { GraphNode, GraphNodeType, ProductGraphResponse } from "@/lib/snapinsight-api"

type EvidenceNodeData = GraphNode & Record<string, unknown>

const NODE_COLORS: Record<GraphNodeType, { border: string; bg: string; text: string }> = {
  product: {
    border: "border-violet-400/50",
    bg: "bg-violet-500/20",
    text: "text-violet-100",
  },
  brand: {
    border: "border-sky-400/40",
    bg: "bg-sky-500/15",
    text: "text-sky-100",
  },
  category: {
    border: "border-cyan-400/40",
    bg: "bg-cyan-500/15",
    text: "text-cyan-100",
  },
  nutrition: {
    border: "border-lime-400/40",
    bg: "bg-lime-500/15",
    text: "text-lime-100",
  },
  ingredient: {
    border: "border-emerald-400/40",
    bg: "bg-emerald-500/15",
    text: "text-emerald-100",
  },
  additive: {
    border: "border-amber-400/40",
    bg: "bg-amber-500/15",
    text: "text-amber-100",
  },
  warning: {
    border: "border-orange-400/50",
    bg: "bg-orange-500/20",
    text: "text-orange-100",
  },
  citation: {
    border: "border-fuchsia-400/40",
    bg: "bg-fuchsia-500/15",
    text: "text-fuchsia-100",
  },
  alternative: {
    border: "border-indigo-400/40",
    bg: "bg-indigo-500/15",
    text: "text-indigo-100",
  },
}

const LAYER_ORDER: GraphNodeType[] = [
  "product",
  "brand",
  "category",
  "alternative",
  "nutrition",
  "ingredient",
  "additive",
  "warning",
  "citation",
]

function layoutNodes(graphNodes: GraphNode[]): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>()
  const byLayer = new Map<GraphNodeType, GraphNode[]>()

  for (const node of graphNodes) {
    const layer = byLayer.get(node.type) ?? []
    layer.push(node)
    byLayer.set(node.type, layer)
  }

  const layerGapY = 110
  const nodeGapX = 170
  const startX = 20

  LAYER_ORDER.forEach((layerType, layerIndex) => {
    const nodesInLayer = byLayer.get(layerType) ?? []
    nodesInLayer.forEach((node, index) => {
      positions.set(node.id, {
        x: startX + index * nodeGapX,
        y: 20 + layerIndex * layerGapY,
      })
    })
  })

  return positions
}

function EvidenceNode({ data, selected }: NodeProps<Node<EvidenceNodeData>>) {
  const palette = NODE_COLORS[data.type]
  return (
    <div
      className={`min-w-[120px] max-w-[168px] rounded-2xl border px-3 py-2 shadow-lg backdrop-blur-sm ${palette.border} ${palette.bg} ${selected ? "ring-2 ring-violet-300/70" : ""}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-400" />
      <p className={`text-[10px] font-semibold uppercase tracking-wide ${palette.text}`}>
        {data.type}
      </p>
      <p className="mt-1 text-xs font-medium leading-snug text-foreground">
        {data.label}
      </p>
      <Handle type="source" position={Position.Bottom} className="!bg-slate-400" />
    </div>
  )
}

const nodeTypes = {
  evidence: EvidenceNode,
}

interface EvidenceGraphFlowProps {
  graph: ProductGraphResponse
  selectedNodeId: string | null
  onSelectNode: (node: GraphNode | null) => void
}

export function EvidenceGraphFlow({
  graph,
  selectedNodeId,
  onSelectNode,
}: EvidenceGraphFlowProps) {
  const positions = useMemo(() => layoutNodes(graph.nodes), [graph.nodes])

  const nodes: Node<EvidenceNodeData>[] = useMemo(
    () =>
      graph.nodes.map((node) => {
        const position = positions.get(node.id) ?? { x: 0, y: 0 }
        return {
          id: node.id,
          type: "evidence",
          position,
          data: { ...node } as EvidenceNodeData,
          selected: node.id === selectedNodeId,
        }
      }),
    [graph.nodes, positions, selectedNodeId]
  )

  const edges: Edge[] = useMemo(
    () =>
      graph.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label ?? edge.relationship,
        animated: edge.relationship === "grounded_in",
        style: { stroke: "rgba(167, 139, 250, 0.55)", strokeWidth: 1.5 },
        labelStyle: { fill: "#cbd5e1", fontSize: 10 },
      })),
    [graph.edges]
  )

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node<EvidenceNodeData>) => {
      onSelectNode(node.data)
    },
    [onSelectNode]
  )

  const handlePaneClick = useCallback(() => {
    onSelectNode(null)
  }, [onSelectNode])

  return (
    <div className="h-[min(62vh,520px)] min-h-[320px] w-full rounded-2xl border border-white/10 bg-slate-950/60">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        fitView
        fitViewOptions={{ padding: 0.2, minZoom: 0.35, maxZoom: 1.2 }}
        minZoom={0.25}
        maxZoom={1.5}
        panOnDrag
        panOnScroll
        zoomOnPinch
        zoomOnScroll={false}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(148, 163, 184, 0.15)" gap={18} />
        <Controls
          showInteractive={false}
          className="!rounded-xl !border-white/10 !bg-slate-900/90 !shadow-lg"
        />
        <MiniMap
          pannable
          zoomable
          className="!rounded-xl !border-white/10 !bg-slate-900/80"
          nodeColor={() => "#8b5cf6"}
        />
      </ReactFlow>
    </div>
  )
}
