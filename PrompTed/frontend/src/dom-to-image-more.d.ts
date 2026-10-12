declare module 'dom-to-image-more' {
    export function toPng(
        node: HTMLElement,
        options?: {
            quality?: number;
            width?: number;
            height?: number;
            bgcolor?: string;
            style?: Record<string, any>;
        }
    ): Promise<string>;

    export function toJpeg(
        node: HTMLElement,
        options?: {
            quality?: number;
            width?: number;
            height?: number;
            bgcolor?: string;
            style?: Record<string, any>;
        }
    ): Promise<string>;

    export function toBlob(
        node: HTMLElement,
        options?: {
            quality?: number;
            width?: number;
            height?: number;
            bgcolor?: string;
            style?: Record<string, any>;
        }
    ): Promise<Blob>;
}
