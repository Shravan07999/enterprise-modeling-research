'use client';

import React, { useState, useRef } from 'react';
import dynamic from 'next/dynamic';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';
import { extractMarkdownBlock } from '../utils/sanitizer';

const PlantUMLViewer = dynamic(() => import('./PlantUMLViewer'), { ssr: false });
const MermaidViewer = dynamic(() => import('./MermaidViewer'), { ssr: false });
const FlowViewer = dynamic(() => import('./FlowViewer'), { ssr: false });
const BPMNViewer = dynamic(() => import('./BPMNViewer'), { ssr: false });

interface Props {
  rawText: string;
  framework: string;
  narrative?: string;
  stage1Blueprint: string;
  modelName: string;
}

export default function DiagramRenderer({ rawText, framework, narrative, stage1Blueprint, modelName }: Props) {
  const [view, setView] = useState<'narrative' | 'diagram'>('diagram');
  const [exportError, setExportError] = useState<string | null>(null);
  const exportRef = useRef<HTMLDivElement>(null);

  const MAX_CANVAS = 8192;

  function isCanvasClean(canvas: HTMLCanvasElement): boolean {
    try {
      canvas.toDataURL('image/png');
      return true;
    } catch {
      return false;
    }
  }

  function inlineComputedStyles(source: Node, target: Node): void {
    if (
      (source instanceof HTMLElement || source instanceof SVGElement) &&
      (target instanceof HTMLElement || target instanceof SVGElement)
    ) {
      const cs = getComputedStyle(source);
      for (let i = 0; i < cs.length; i++) {
        const p = cs[i];
        target.style.setProperty(p, cs.getPropertyValue(p), cs.getPropertyPriority(p));
      }
    }
    for (let i = 0; i < source.childNodes.length && i < target.childNodes.length; i++) {
      inlineComputedStyles(source.childNodes[i], target.childNodes[i]);
    }
  }

  async function domToCanvas(container: HTMLElement): Promise<HTMLCanvasElement | null> {
    // Clone the element and inline all computed styles before rendering — this
    // resolves lab()/lch()/oklch() color functions that html2canvas can't parse.
    const clone = container.cloneNode(true) as HTMLElement;
    clone.querySelectorAll('canvas, video, iframe').forEach(el => el.remove());
    inlineComputedStyles(container, clone);
    clone.querySelectorAll('style').forEach(el => el.remove());

    const w = container.scrollWidth;
    const h = container.scrollHeight;
    if (!w || !h) return null;

    // Render in a hidden iframe so no external stylesheets can reintroduce
    // unsupported color functions into the html2canvas parse context.
    const iframe = document.createElement('iframe');
    iframe.style.cssText = `position:fixed;left:-9999px;top:0;width:${w}px;height:${h}px;border:none`;
    document.body.appendChild(iframe);

    const doc = iframe.contentDocument!;
    doc.open();
    doc.write('<!DOCTYPE html><html><head></head><body></body></html>');
    doc.close();
    doc.body.appendChild(clone);
    await new Promise(r => setTimeout(r, 120));

    try {
      return await html2canvas(doc.body, {
        useCORS: true,
        width: w,
        height: h,
        windowWidth: w,
        windowHeight: h,
      });
    } catch {
      return null;
    } finally {
      document.body.removeChild(iframe);
    }
  }

  async function waitForSvg(container: HTMLElement, timeout = 5000): Promise<SVGElement | null> {
    const existing = container.querySelector('svg');
    if (existing) return existing;
    return new Promise((resolve) => {
      const observer = new MutationObserver(() => {
        const svg = container.querySelector('svg');
        if (svg) { observer.disconnect(); resolve(svg); }
      });
      observer.observe(container, { childList: true, subtree: true });
      setTimeout(() => { observer.disconnect(); resolve(null); }, timeout);
    });
  }

  async function svgToCanvas(container: HTMLElement): Promise<HTMLCanvasElement | null> {
    const svgEl = await waitForSvg(container);
    if (!svgEl) return null;

    const clone = svgEl.cloneNode(true) as SVGElement;

    const viewBox = clone.getAttribute('viewBox');
    let w: number, h: number;
    if (viewBox) {
      const p = viewBox.split(/\s+/).map(Number);
      w = Math.min(p[2] || 800, MAX_CANVAS);
      h = Math.min(p[3] || 600, MAX_CANVAS);
    } else {
      const rect = svgEl.getBoundingClientRect();
      w = Math.min(rect.width || 800, MAX_CANVAS);
      h = Math.min(rect.height || 600, MAX_CANVAS);
    }

    clone.setAttribute('width', String(w));
    clone.setAttribute('height', String(h));
    clone.removeAttribute('style');

    const svgData = new XMLSerializer().serializeToString(clone);
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        canvas.getContext('2d')!.drawImage(img, 0, 0);
        URL.revokeObjectURL(url);
        resolve(isCanvasClean(canvas) ? canvas : null);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        resolve(null);
      };
      img.src = url;
    });
  }

  async function captureCanvas(container: HTMLElement): Promise<HTMLCanvasElement | null> {
    const canvasEl = container.querySelector('canvas');
    if (!canvasEl) return null;
    try {
      const c = document.createElement('canvas');
      c.width = Math.min(canvasEl.width, MAX_CANVAS);
      c.height = Math.min(canvasEl.height, MAX_CANVAS);
      const ctx = c.getContext('2d');
      if (!ctx) return null;
      ctx.drawImage(canvasEl, 0, 0);
      return isCanvasClean(c) ? c : null;
    } catch {
      return null;
    }
  }

  async function captureContainer(container: HTMLElement): Promise<HTMLCanvasElement> {
    // ReactFlow nodes use <foreignObject> inside SVG, so svgToCanvas would drop
    // their content when loaded as <img>. Skip straight to domToCanvas instead.
    if (container.querySelector('.react-flow')) {
      const rf = await domToCanvas(container);
      if (rf) return rf;
    }

    const fromSvg = await svgToCanvas(container);
    if (fromSvg) return fromSvg;

    const fromCanvas = await captureCanvas(container);
    if (fromCanvas) return fromCanvas;

    const fromDom = await domToCanvas(container);
    if (fromDom) return fromDom;

    throw new Error('Canvas tainted — cross-origin content blocked the export');
  }

  const exportPNG = async () => {
    if (!exportRef.current) return;
    setExportError(null);
    try {
      const canvas = await captureContainer(exportRef.current);
      const link = document.createElement('a');
      link.download = 'diagram.png';
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (err: any) {
      setExportError(err.message || 'Export failed');
    }
  };

  const exportPDF = async () => {
    if (!exportRef.current) return;
    setExportError(null);
    try {
      const canvas = await captureContainer(exportRef.current);
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF({
        orientation: canvas.width > canvas.height ? 'landscape' : 'portrait',
        unit: 'px',
        format: [canvas.width, canvas.height]
      });
      pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);
      pdf.save('diagram.pdf');
    } catch (err: any) {
      setExportError(err.message || 'Export failed');
    }
  };

  const exportEnterpriseModel = async (format: 'adl' | 'archimate', extension: string) => {
    setExportError(null);
    try {
      const response = await fetch(`http://localhost:8010/export/${format}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          framework_selected: framework,
          model_name: modelName,
          stage1_blueprint: stage1Blueprint,
          final_output: rawText,
        }),
      });
      
      if (!response.ok) {
        const errData = await response.json().catch(() => null);
        throw new Error(errData?.detail || `Failed to export ${extension}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const cd = response.headers.get('content-disposition');
      let filename = cd?.split('filename=')?.[1]?.replace(/"/g, '') || `export.${extension}`;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setExportError(err.message || 'Export failed');
    }
  };

  let content = '';
  let badgeName = '';
  let ViewerComponent: React.ReactNode = null;
  
  if (framework === 'BPMN' || rawText.toLowerCase().includes('```xml')) {
    content = extractMarkdownBlock(rawText, 'xml');
    badgeName = 'XML';
    ViewerComponent = <BPMNViewer code={content} />;
  } else if (framework === 'TOGAF' || rawText.toLowerCase().includes('```plantuml')) {
    content = extractMarkdownBlock(rawText, 'plantuml');
    badgeName = 'PLANTUML';
    ViewerComponent = <PlantUMLViewer code={content} />;
  } else if (framework === 'Zachman' || rawText.toLowerCase().includes('```mermaid')) {
    content = extractMarkdownBlock(rawText, 'mermaid');
    badgeName = 'MERMAID';
    ViewerComponent = <MermaidViewer code={content} />;
  } else {
    content = extractMarkdownBlock(rawText, 'json');
    badgeName = 'JSON';
    ViewerComponent = <FlowViewer code={content} />;
  }

  return (
    <div className="flex flex-col flex-1 w-full bg-[#111827]">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-[#0a0e17]">
        <div className="flex items-center gap-4">
          <div className="flex bg-gray-900 rounded-lg p-1 border border-gray-800">
            <button
              onClick={() => setView('narrative')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                view === 'narrative' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              Narrative
            </button>
            <button
              onClick={() => setView('diagram')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                view === 'diagram' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              Diagram
            </button>
          </div>
          <span className="bg-gray-800 text-gray-400 px-3 py-1 rounded text-xs font-bold tracking-widest border border-gray-700">
            {badgeName}
          </span>
        </div>

        <div className="flex gap-2">
          {framework === '4EM' && (
            <button
              onClick={() => exportEnterpriseModel('adl', 'adl')}
              className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-1.5 rounded text-sm font-medium border border-gray-700 transition"
            >
              4EM (.adl)
            </button>
          )}
          {framework === 'BPMN' && (
            <button
              onClick={() => exportEnterpriseModel('archimate', 'archimate')}
              className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-1.5 rounded text-sm font-medium border border-gray-700 transition"
            >
              Archi (.archimate)
            </button>
          )}
          <button
            onClick={exportPNG}
            className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-1.5 rounded text-sm font-medium border border-gray-700 transition"
          >
            PNG
          </button>
          <button
            onClick={exportPDF}
            className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-1.5 rounded text-sm font-medium border border-gray-700 transition"
          >
            PDF
          </button>
          {exportError && (
            <span className="text-red-400 text-xs self-center ml-2 max-w-[200px] truncate" title={exportError}>
              {exportError}
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 relative min-h-0 bg-[#0a0e17]">
        {view === 'narrative' ? (
          <div className="absolute inset-0 overflow-auto p-8">
            <div className="text-gray-200 leading-relaxed text-base whitespace-pre-wrap max-w-4xl">
              {narrative || "No narrative available."}
            </div>
          </div>
        ) : (
          <div ref={exportRef} className="absolute inset-0 bg-white text-black">
            {ViewerComponent}
          </div>
        )}
      </div>
    </div>
  );
}
