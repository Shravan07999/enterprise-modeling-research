"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import mermaid from "mermaid";
import plantumlEncoder from "plantuml-encoder";
import BpmnViewer from "bpmn-js/lib/NavigatedViewer";

mermaid.initialize({ theme: "dark", startOnLoad: false });

interface Props {
  code: string;
}

const MERMAID_KEYWORDS = [
  "graph", "flowchart", "sequenceDiagram", "classDiagram",
  "stateDiagram", "erDiagram", "gantt", "pie", "gitGraph",
  "mindmap", "timeline", "xychart", "block", "quadrantChart",
  "requirementDiagram", "journey", "C4Context", "C4Container",
  "C4Component", "C4Dynamic", "C4Deployment",
];

function detectFormat(code: string): string {
  if (!code) return "";
  const trimmed = code.trim();
  // PlantUML checked first for backward compat with older stored output
  if (trimmed.startsWith("@startuml") || trimmed.startsWith("@startmindmap") || code.includes("@startuml")) return "plantuml";
  const first = trimmed.split("\n")[0];
  for (const kw of MERMAID_KEYWORDS) {
    if (code.includes(kw)) return "mermaid";
  }
  if (code.startsWith("{") || code.startsWith("[")) return "json";
  if (first.includes("|") && first.includes("---")) return "markdown";
  return "text";
}

const MIN_ZOOM = 0.1;
const MAX_ZOOM = 10;
const ZOOM_STEP = 0.25;

export default function QRewCanvas({ code }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const diagramRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const bpmnViewerRef = useRef<any>(null);
  const [view, setView] = useState<"diagram" | "code">("code");
  const [diagramError, setDiagramError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  // Zoom & pan state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const isPanning = useRef(false);
  const panStart = useRef({ x: 0, y: 0 });
  const panOrigin = useRef({ x: 0, y: 0 });

  const format = detectFormat(code);
  const isDiagramSupported = format === "mermaid" || format === "plantuml" || format === "bpmn";

  // Reset zoom/pan when code or view changes
  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, [code, view]);

  useEffect(() => {
    setDiagramError(null);
    if (view !== "diagram" || !diagramRef.current || !isDiagramSupported) return;

    diagramRef.current.innerHTML = "";
    
    if (format === "mermaid") {
      const pre = document.createElement("pre");
      pre.className = "mermaid flex justify-center";
      pre.textContent = code;
      diagramRef.current.appendChild(pre);

      mermaid.run({ nodes: [pre] }).catch((err) => {
        setDiagramError(err?.message || "Mermaid could not render this diagram");
      });
    } else if (format === "plantuml") {
      const encoded = plantumlEncoder.encode(code);
      const img = document.createElement("img");
      img.src = `http://www.plantuml.com/plantuml/svg/${encoded}`;
      img.alt = "PlantUML Diagram";
      img.className = "mx-auto bg-white p-4 rounded-lg";
      img.onerror = () => setDiagramError("Failed to load PlantUML diagram from server");
      diagramRef.current.appendChild(img);
    } else if (format === "bpmn") {
      const viewer = new BpmnViewer({ container: diagramRef.current });
      bpmnViewerRef.current = viewer;
      // bpmn-js requires explicit height to be visible
      diagramRef.current.style.height = "600px";
      diagramRef.current.style.backgroundColor = "white";
      diagramRef.current.className = "rounded-lg overflow-hidden relative";
      viewer.importXML(code).then(() => {
        const canvas = viewer.get('canvas');
        canvas.zoom('fit-viewport');
      }).catch((err: any) => {
        setDiagramError(err?.message || "BPMN could not render this XML");
      });
    }
    
    return () => {
      if (diagramRef.current) {
        diagramRef.current.style.height = "";
        diagramRef.current.style.backgroundColor = "";
        diagramRef.current.className = "";
      }
    };
  }, [code, view, format, isDiagramSupported]);

  // Mouse-wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((prev) => {
      const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
      return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, prev + delta));
    });
  }, []);

  // Drag-to-pan handlers
  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    if (e.button !== 0) return;
    isPanning.current = true;
    panStart.current = { x: e.clientX, y: e.clientY };
    panOrigin.current = { ...pan };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }, [pan]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!isPanning.current) return;
    setPan({
      x: panOrigin.current.x + (e.clientX - panStart.current.x),
      y: panOrigin.current.y + (e.clientY - panStart.current.y),
    });
  }, []);

  const handlePointerUp = useCallback(() => {
    isPanning.current = false;
  }, []);

  const inlineSvgStyles = (svg: SVGSVGElement): string => {
    const clone = svg.cloneNode(true) as SVGSVGElement;
    const walk = (el: Element) => {
      if (!el.getAttribute) return;
      const computed = window.getComputedStyle(el);
      const styleStr: string[] = [];
      for (let i = 0; i < computed.length; i++) {
        const name = computed[i];
        const value = computed.getPropertyValue(name);
        if (value) styleStr.push(`${name}:${value}`);
      }
      if (styleStr.length) {
        el.setAttribute("style", styleStr.join(";"));
      }
      for (let i = 0; i < el.children.length; i++) walk(el.children[i]);
    };
    walk(clone);
    return new XMLSerializer().serializeToString(clone);
  };

  const serializeSvg = (svg: SVGSVGElement): string => {
    const clone = svg.cloneNode(true) as SVGSVGElement;
    const { width: w, height: h } = svgDim(svg);
    clone.setAttribute("width", String(w));
    clone.setAttribute("height", String(h));
    const walk = (el: Element) => {
      const computed = window.getComputedStyle(el);
      const styleStr: string[] = [];
      for (let i = 0; i < computed.length; i++) {
        const name = computed[i];
        const value = computed.getPropertyValue(name);
        if (value) styleStr.push(`${name}:${value}`);
      }
      if (styleStr.length) el.setAttribute("style", styleStr.join(";"));
      for (let i = 0; i < el.children.length; i++) walk(el.children[i]);
    };
    walk(clone);
    return new XMLSerializer().serializeToString(clone);
  };

  const svgDim = (svg: SVGSVGElement): { width: number; height: number } => {
    const vb = svg.getAttribute("viewBox");
    if (vb) {
      const p = vb.trim().split(/\s+/).map(Number);
      if (p.length === 4 && p[2] > 0 && p[3] > 0) return { width: p[2], height: p[3] };
    }
    try {
      const bbox = svg.getBBox();
      if (bbox.width > 0 && bbox.height > 0) return { width: bbox.width, height: bbox.height };
    } catch {}
    const rect = svg.getBoundingClientRect();
    return { width: rect.width || 800, height: rect.height || 600 };
  };

  const svgToCanvas = async (svg: SVGSVGElement, bg: string): Promise<HTMLCanvasElement> => {
    const { width: w, height: h } = svgDim(svg);
    const svgString = serializeSvg(svg);
    const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svgString);
    const img = new Image();
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error("SVG could not be rasterized"));
      img.src = url;
    });
    const scale = 2;
    const canvas = document.createElement("canvas");
    canvas.width = w * scale;
    canvas.height = h * scale;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Could not get canvas context");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.scale(scale, scale);
    ctx.drawImage(img, 0, 0);
    return canvas;
  };

  const generateCanvas = useCallback(async (): Promise<HTMLCanvasElement> => {
    if (!diagramRef.current) throw new Error("Diagram not rendered");

    if (format === "bpmn" && bpmnViewerRef.current) {
      const { svg } = await bpmnViewerRef.current.saveSVG({ format: true });
      return await svgToCanvas(svg, "#ffffff");
    }

    if (format === "plantuml") {
      const imgNode = diagramRef.current.querySelector("img");
      if (!imgNode) throw new Error("No PlantUML image found");
      const encoded = plantumlEncoder.encode(code);
      const res = await fetch(`http://www.plantuml.com/plantuml/svg/${encoded}`);
      const svgText = await res.text();
      const encodedData = encodeURIComponent(svgText);
      const url = "data:image/svg+xml;charset=utf-8," + encodedData;
      const img = new Image();
      await new Promise<void>((resolve, reject) => {
        img.onload = () => resolve();
        img.onerror = () => reject(new Error("SVG could not be rasterized"));
        img.src = url;
      });
      const w = imgNode.clientWidth || 800;
      const h = imgNode.clientHeight || 600;
      const scale = 2;
      const canvas = document.createElement("canvas");
      canvas.width = w * scale;
      canvas.height = h * scale;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Could not get canvas context");
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.scale(scale, scale);
      ctx.drawImage(img, 0, 0);
      return canvas;
    }

    const svg = diagramRef.current.querySelector("svg");
    if (!svg) throw new Error("No SVG diagram found to export");
    return await svgToCanvas(svg, "#111827");
  }, [format, code]);

  const handleExport = useCallback(async (type: "png" | "pdf") => {
    if (view !== "diagram") {
      alert("Switch to Diagram view before exporting");
      return;
    }
    setExporting(true);
    try {
      const canvas = await generateCanvas();
      if (type === "png") {
        const link = document.createElement("a");
        link.download = "qrew-diagram.png";
        link.href = canvas.toDataURL("image/png");
        link.click();
      } else {
        const { default: jsPDF } = await import("jspdf");
        const imgData = canvas.toDataURL("image/png");
        const pdf = new jsPDF("l", "mm", "a4");
        const pdfW = pdf.internal.pageSize.getWidth();
        const pdfH = (canvas.height * pdfW) / canvas.width;
        pdf.addImage(imgData, "PNG", 0, 0, pdfW, pdfH);
        pdf.save("qrew-diagram.pdf");
      }
    } catch (err) {
      console.error(err);
      alert(`Failed to export ${type.toUpperCase()}: ${(err as Error).message}`);
    } finally {
      setExporting(false);
    }
  }, [view, format, code]);

  const handleExportPNG = useCallback(() => handleExport("png"), [handleExport]);
  const handleExportPDF = useCallback(() => handleExport("pdf"), [handleExport]);

  const zoomIn = () => setZoom((z) => Math.min(MAX_ZOOM, z + ZOOM_STEP));
  const zoomOut = () => setZoom((z) => Math.max(MIN_ZOOM, z - ZOOM_STEP));
  const zoomReset = () => { setZoom(1); setPan({ x: 0, y: 0 }); };

  const showZoomControls = view === "diagram" && isDiagramSupported;

  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="flex items-center gap-2">
        <button
          onClick={() => setView("code")}
          className={`px-3 py-1 text-sm rounded transition-colors ${
            view === "code" ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700"
          }`}
        >
          Code
        </button>
        <button
          onClick={() => setView("diagram")}
          disabled={!isDiagramSupported}
          className={`px-3 py-1 text-sm rounded transition-colors ${
            view === "diagram" ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700"
          } ${!isDiagramSupported ? "opacity-40 cursor-not-allowed" : ""}`}
          title={!isDiagramSupported ? `Diagram view requires Mermaid, PlantUML, or BPMN (detected: ${format})` : ""}
        >
          Diagram
        </button>

        <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-500 uppercase font-mono">
          {format}
        </span>

        {showZoomControls && (
          <div className="flex items-center gap-1 ml-2">
            <button
              onClick={zoomOut}
              className="w-7 h-7 flex items-center justify-center text-sm rounded bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
              title="Zoom out"
            >
              −
            </button>
            <span className="text-xs text-gray-400 font-mono w-12 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={zoomIn}
              className="w-7 h-7 flex items-center justify-center text-sm rounded bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
              title="Zoom in"
            >
              +
            </button>
            <button
              onClick={zoomReset}
              className="px-2 py-1 text-xs rounded bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200 transition-colors ml-1"
              title="Reset zoom and position"
            >
              Reset
            </button>
          </div>
        )}

        <div className="flex-1" />
        <button
          onClick={handleExportPNG}
          disabled={exporting || view !== "diagram"}
          className="px-3 py-1 text-sm rounded bg-gray-800 text-gray-300 hover:bg-gray-700 disabled:opacity-50"
        >
          PNG
        </button>
        <button
          onClick={handleExportPDF}
          disabled={exporting || view !== "diagram"}
          className="px-3 py-1 text-sm rounded bg-gray-800 text-gray-300 hover:bg-gray-700 disabled:opacity-50"
        >
          PDF
        </button>
      </div>

      <motion.div
        ref={containerRef}
        layout
        className="rounded-lg border border-gray-700 bg-gray-900 min-h-[500px] flex-1 overflow-hidden relative"
      >
        {view === "diagram" ? (
          <div
            ref={viewportRef}
            className="w-full h-full min-h-[500px] cursor-grab active:cursor-grabbing select-none"
            onWheel={handleWheel}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
          >
            <div
              className="flex justify-center items-start p-4 origin-center"
              style={{
                transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                transformOrigin: "center top",
                transition: isPanning.current ? "none" : "transform 0.15s ease-out",
                minHeight: "100%",
              }}
            >
              <div ref={diagramRef} />
            </div>
            {diagramError && (
              <p className="text-red-400 text-sm mt-3 text-center absolute bottom-4 left-0 right-0">
                {diagramError}
              </p>
            )}
          </div>
        ) : (
          <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono leading-relaxed p-4 overflow-auto h-full min-h-[500px]">{code}</pre>
        )}
      </motion.div>
    </div>
  );
}
