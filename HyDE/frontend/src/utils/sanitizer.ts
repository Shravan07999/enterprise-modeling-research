export function extractMarkdownBlock(text: string, language: string): string {
    // Attempt to find the specific language block (e.g. ```mermaid ... ```)
    // Supports content on the same line as the language tag or on the next line
    const regex = new RegExp(`\`\`\`${language}\\s*(\\n)?([\\s\\S]*?)\`\`\``, 'i');
    const match = text.match(regex);
    const content = match && match[2] ? match[2] : null;
    if (content) {
        return content.trim();
    }
    
    // If no specific language block, try to find ANY markdown code block as a fallback
    const genericRegex = /```[\w]*\s*(\n)?([\s\S]*?)```/i;
    const genericMatch = text.match(genericRegex);
    const genericContent = genericMatch && genericMatch[2] ? genericMatch[2] : null;
    if (genericContent) {
        return genericContent.trim();
    }
    
    // Specific fallback for BPMN XML if the block fences were omitted
    if (language.toLowerCase() === 'xml') {
        const xmlRegex = /<bpmn:definitions[\s\S]*<\/bpmn:definitions>/i;
        const xmlMatch = text.match(xmlRegex);
        if (xmlMatch) return xmlMatch[0];
    }
    
    // Ultimate fallback: strip any surrounding loose text manually if possible, or return raw
    return text.trim();
}
