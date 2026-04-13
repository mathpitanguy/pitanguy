---
title: Ficha de Projeto
description: Formulário padronizado de registro e acompanhamento de projetos da Unidade.
hide:
  - toc
---

# Ficha de Projeto

<div class="ficha-wrapper">
  <iframe
    src="/pitanguy/assets/ficha_projeto.html"
    title="Ficha de Projeto"
    id="ficha-frame"
    scrolling="no"
    frameborder="0"
    style="width:100%; min-height:400px; border:none; display:block;">
  </iframe>
</div>

<script>
(function () {
  const frame = document.getElementById('ficha-frame');
  frame.addEventListener('load', function () {
    try {
      const h = frame.contentDocument.body.scrollHeight;
      frame.style.height = (h + 32) + 'px';
    } catch(e) {}
  });
})();
</script>

