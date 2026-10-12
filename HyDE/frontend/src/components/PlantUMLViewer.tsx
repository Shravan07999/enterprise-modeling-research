'use client';
import plantumlEncoder from 'plantuml-encoder';
import { useState, useEffect } from 'react';

export default function PlantUMLViewer({ code }: { code: string }) {
  const [error, setError] = useState<string | null>(null);
  const [svgContent, setSvgContent] = useState<string | null>(null);

  useEffect(() => {
    let plantumlCode = code;
    if (!plantumlCode.trim().startsWith('@startuml')) {
      plantumlCode = '@startuml\n' + plantumlCode;
    }
    if (!plantumlCode.trim().endsWith('@enduml')) {
      plantumlCode = plantumlCode + '\n@enduml';
    }

    let encodedString = '';
    try {
      encodedString = plantumlEncoder.encode(plantumlCode);
    } catch (e) {
      setError('Failed to encode PlantUML string.');
      return;
    }

    const proxyUrl = `http://localhost:8010/render-plantuml?encoded=${encodedString}`;

    fetch(proxyUrl)
      .then((res) => {
        if (!res.ok) throw new Error('Proxy returned ' + res.status);
        return res.text();
      })
      .then((svg) => {
        setSvgContent(svg);
      })
      .catch(() => {
        setError('PlantUML render server unavailable.');
      });
  }, [code]);

  if (error) {
    return (
      <div className="p-4 bg-red-100 text-red-800 rounded border border-red-300 m-4">
        <h3 className="font-bold mb-2">PlantUML Render Error</h3>
        <pre className="text-sm overflow-auto max-h-60 p-2 bg-red-50 rounded">{code}</pre>
        <p className="mt-2 text-xs opacity-80">{error}</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full min-h-[400px] overflow-auto bg-white">
      {svgContent && <div dangerouslySetInnerHTML={{ __html: svgContent }} />}
    </div>
  );
}
