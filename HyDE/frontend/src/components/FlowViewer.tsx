'use client';
import React, { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
  Handle,
  Position,
  ReactFlowProvider,
  NodeProps,
} from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';

interface FlowNode {
  id: string | number;
  label: string;
  type?: string;
  next?: (string | number)[];
}

const typeColors: Record<string, string> = {
  Goal: '#EAB308',
  Process: '#3B82F6',
  Data: '#22C55E',
  Resource: '#A855F7',
};

const typeBgColors: Record<string, string> = {
  Goal: '#FEF9C3',
  Process: '#DBEAFE',
  Data: '#DCFCE7',
  Resource: '#F3E8FF',
};

function FlowCustomNode({ data }: NodeProps) {
  return (
    <div
      style={{
        background: data.bgColor || '#FFFFFF',
        border: `2px solid ${data.borderColor || '#3B82F6'}`,
        borderRadius: '8px',
        padding: '8px',
        textAlign: 'center',
        fontWeight: 700,
        color: '#1F2937',
        fontSize: '12px',
        width: 150,
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div>{data.label}</div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

const nodeTypes = {
  flowNode: FlowCustomNode,
};

export default function FlowViewer({ code }: { code: string }) {
  const { nodes, edges, error } = useMemo(() => {
    try {
      const data: FlowNode[] = JSON.parse(code);
      
      const g = new dagre.graphlib.Graph();
      g.setGraph({ rankdir: 'TB' });
      g.setDefaultEdgeLabel(() => ({}));

      const initialNodes: Node[] = [];
      const initialEdges: Edge[] = [];

      data.forEach(item => {
        const strId = String(item.id);
        g.setNode(strId, { width: 150, height: 50 });
        const nodeType = item.type || '';
        const borderColor = typeColors[nodeType] || '#3B82F6';
        const bgColor = typeBgColors[nodeType] || '#FFFFFF';
        initialNodes.push({
          id: strId,
          type: 'flowNode',
          data: {
            label: item.label,
            borderColor,
            bgColor,
          },
          position: { x: 0, y: 0 },
        });

        if (item.next && Array.isArray(item.next)) {
          item.next.forEach(nextRaw => {
            const nextId = String(nextRaw);
            g.setEdge(strId, nextId);
            initialEdges.push({
              id: `${strId}-${nextId}`,
              source: strId,
              target: nextId,
              animated: true,
              style: { stroke: '#3b82f6', strokeWidth: 2 }
            });
          });
        }
      });

      dagre.layout(g);

      const layoutedNodes = initialNodes.map(node => {
        const nodeWithPosition = g.node(node.id);
        return {
          ...node,
          position: {
            x: (nodeWithPosition?.x || 75) - 75,
            y: (nodeWithPosition?.y || 25) - 25,
          },
        };
      });

      return { nodes: layoutedNodes, edges: initialEdges, error: null };
    } catch (e: any) {
      return { nodes: [], edges: [], error: e.message || "Failed to parse JSON" };
    }
  }, [code]);

  if (error || nodes.length === 0) {
    return (
      <div className="p-4 bg-red-100 text-red-800 rounded border border-red-300 m-4 w-auto">
        <h3 className="font-bold mb-2">React Flow Data Error</h3>
        <pre className="text-sm overflow-auto max-h-60 p-2 bg-red-50 rounded">{code}</pre>
        <p className="mt-2 text-xs opacity-80">{error || "Empty data."}</p>
      </div>
    );
  }
  
  return (
    <div className="w-full h-full min-h-[500px] relative">
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
        >
          <Background />
          <Controls />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}
