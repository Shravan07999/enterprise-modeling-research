# Enterprise Modelling Tool — Frontend

Visual workbench for enterprise architecture modeling, pipeline configuration, and blueprint inspection.

## Technology Stack

- **Framework**: Next.js 16 (App Router, React 19)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **Diagram Export**: dom-to-image-more, jsPDF

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run the local development server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

- `src/app`: App Router pages (workbench, prompts, chains, analytics, login)
- `src/components`: UI components (`BlueprintDiagram.tsx`, `Sidebar.tsx`, `TelemetryPanel.tsx`)
- `src/services`: Axios API client definitions (`api.ts`)
- `src/context`: Authentication session state (`AuthContext.tsx`)

