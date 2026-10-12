'use client';
import React, { useEffect, useRef, useState } from 'react';

export default function BPMNViewer({ code }: { code: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let viewer: any = null;
    
    const renderBPMN = async () => {
      if (!containerRef.current) return;
      
      // Dynamic import inside useEffect ensures this only runs client-side.
      // bpmn-js relies on DOM APIs and its CSS imports break SSR.
      const { default: NavigatedViewer } = await import('bpmn-js/lib/NavigatedViewer');
      
      viewer = new NavigatedViewer({
        container: containerRef.current,
      });

      let xml = code.trim();
      
      // If the LLM output a raw XML declaration but missed the definitions tag, strip the declaration first
      if (xml.startsWith('<?xml')) {
        xml = xml.replace(/<\?xml.*?\?>/i, '').trim();
      }

      // Prepend standard XML boilerplate dynamically if the response string arrives truncated per spec 4.4.
      // We check for both <bpmn:definitions> and standard <definitions> to prevent double-wrapping.
      if (!xml.includes('<bpmn:definitions') && !xml.includes('<definitions')) {
        xml = `<?xml version="1.0" encoding="UTF-8"?>\n<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn">\n${xml}\n</bpmn:definitions>`;
      } else {
        // If it already has definitions, just ensure it has the xml header
        xml = `<?xml version="1.0" encoding="UTF-8"?>\n${xml}`;
      }

      try {
        // Automatically inject layout coordinates to fix missing or broken <bpmndi:BPMNDiagram> from LLM
        const { layoutProcess } = await import('bpmn-auto-layout');
        const layoutedXml = await layoutProcess(xml);

        await viewer.importXML(layoutedXml);
        viewer.get('canvas').zoom('fit-viewport');
      } catch (err: any) {
        setError(err.message || 'Failed to render BPMN XML structure.');
      }
    };

    if (code) {
      renderBPMN();
    }

    return () => {
      if (viewer) viewer.destroy();
    };
  }, [code]);

  if (error) {
    return (
      <div className="p-4 bg-red-100 text-red-800 rounded border border-red-300 w-full">
        <h3 className="font-bold mb-2">BPMN Syntax Error</h3>
        <pre className="text-sm overflow-auto max-h-60 p-2 bg-red-50 rounded">{code}</pre>
        <p className="mt-2 text-xs opacity-80">{error}</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="w-full h-full min-h-[500px]" />
  );
}
