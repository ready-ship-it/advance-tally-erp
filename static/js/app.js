// Lightweight enhancements (form confirmations etc.)
document.querySelectorAll('form[data-confirm]').forEach(f => {
  f.addEventListener('submit', e => {
    if(!confirm(f.dataset.confirm)) e.preventDefault();
  });
});
