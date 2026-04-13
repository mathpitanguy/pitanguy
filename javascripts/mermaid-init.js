document.addEventListener('DOMContentLoaded', function() {
    if (typeof mermaid !== 'undefined') {
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose', // Necessário para alguns diagramas
            flowchart: { useMaxWidth: true, htmlLabels: true },
            timeline: { useMaxWidth: true } // Configuração específica para timeline
        });
        mermaid.init();
    }
});
