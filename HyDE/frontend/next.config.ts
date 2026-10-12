import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  transpilePackages: ['mermaid', 'bpmn-js', 'reactflow'],
};

export default nextConfig;
