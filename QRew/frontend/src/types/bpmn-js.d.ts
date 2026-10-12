declare module "bpmn-js/lib/NavigatedViewer" {
  interface NavigatorViewerInstance {
    importXML(xml: string): Promise<{ warnings: any[] }>;
    saveSVG(options: { format: boolean }): Promise<{ svg: SVGSVGElement }>;
    get(name: string): any;
    on(event: string, callback: (...args: any[]) => void): void;
    destroy(): void;
  }
  const NavigatedViewer: new (options?: any) => NavigatorViewerInstance;
  export default NavigatedViewer;
}
