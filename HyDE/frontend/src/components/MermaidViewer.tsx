'use client';
import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

export default function MermaidViewer({ code }: { code: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const initialized = useRef(false);

  useEffect(() => {
    if (!initialized.current) {
      mermaid.initialize({ theme: 'default' });
      initialized.current = true;
    }
    const renderDiagram = async () => {
      if (containerRef.current) {
        try {
          setError(null);
          const { svg } = await mermaid.render(`mermaid-${Date.now()}`, code);
          containerRef.current.innerHTML = svg;
        } catch (err: any) {
          setError(err.message || "Failed to render Mermaid diagram.");
        }
      }
    };
    if (code) {
      renderDiagram();
    }
  }, [code]);

  if (error) {
    return (
      <div className="p-4 bg-red-100 text-red-800 rounded border border-red-300 w-full">
        <h3 className="font-bold mb-2">Mermaid Syntax Error</h3>
        <pre className="text-sm overflow-auto max-h-60 p-2 bg-red-50 rounded">{code}</pre>
        <p className="mt-2 text-xs opacity-80">{error}</p>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef} 
      className="w-full h-full min-h-[400px] overflow-auto"
    />
  );
}
