export interface CanonicalModelMetadata {
  modelId: string;
  name: string;
  version: string;
  createdAt: string;
  toolVersion: string;
  frameworkVersion: string;
  sourceRunId: string;
}

export interface CanonicalElementAttributes {
  [key: string]: string | number | boolean | undefined;
  Position?: string;
  Criticality?: string;
  Priority?: string;
  IntermodelRelations?: string;
  Decomposition?: string;
  DefinedBy?: string;
  IsSameAs?: string;
  HiddenAttribute?: string;
  DecomposedProcess?: string;
  ExecutionTime?: number;
  Complexity?: number;
  Type?: string;
  Attributes?: string;
  Specification?: string;
  Quantity?: number;
  Location?: string;
}

export interface CanonicalElement {
  id: string;
  frameworkType: string;
  canonicalType: string;
  name: string;
  description: string;
  layer: string | null;
  submodel: string | null;
  attributes: CanonicalElementAttributes;
}

export interface CanonicalRelationshipAttributes {
  [key: string]: string | number | boolean | undefined;
}

export interface CanonicalRelationship {
  id: string;
  sourceId: string;
  targetId: string;
  frameworkType: string;
  canonicalType: string;
  name: string;
  description: string;
  attributes: CanonicalRelationshipAttributes;
}

export interface CanonicalDiagramNode {
  elementId: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface CanonicalDiagramConnection {
  relationshipId: string;
  waypoints: number[][];
}

export interface CanonicalDiagram {
  id: string;
  name: string;
  type: string;
  viewpoint: string | null;
  nodes: CanonicalDiagramNode[];
  connections: CanonicalDiagramConnection[];
}

export interface CanonicalFolder {
  id: string;
  name: string;
  type: string;
  elementIds: string[];
}

export interface CanonicalModel {
  framework: "4EM" | "BPMN" | "TOGAF" | "ZACHMAN";
  metadata: CanonicalModelMetadata;
  elements: CanonicalElement[];
  relationships: CanonicalRelationship[];
  diagrams: CanonicalDiagram[];
  folders: CanonicalFolder[];
  extensions: Record<string, unknown>;
}

export interface PipelineTraces {
  original_raw_input: string;
  stage_1_rewritten_query: string;
  final_generated_code: string;
  canonical_model?: CanonicalModel;
  canonical_model_warnings?: string[];
}

export interface PipelineMetrics {
  stage_1_latency_seconds: number;
  stage_2_latency_seconds: number;
  total_latency_seconds: number;
  stage_1_prompt_tokens: number;
  stage_1_completion_tokens: number;
  stage_2_prompt_tokens: number;
  stage_2_completion_tokens: number;
  stage_2b_latency_seconds?: number;
  stage_2b_prompt_tokens?: number;
  stage_2b_completion_tokens?: number;
}

export interface PipelineResult {
  run_id: string;
  timestamp: string;
  pipeline_strategy: string;
  framework_target: string;
  metrics: PipelineMetrics;
  traces: PipelineTraces;
}

export interface ExportRequest {
  run_id: string;
  format: "adl" | "archimate";
}

export interface ExportStatusResponse {
  run_id: string;
  framework: string;
  canonical_model_available: boolean;
  formats_available: string[];
  validation_warnings: string[];
}