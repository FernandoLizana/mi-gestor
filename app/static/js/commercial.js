(function () {
  const board = document.getElementById('pipelineBoard');
  if (!board) return;

  let dragged = null;

  board.querySelectorAll('.pipeline-card').forEach((card) => {
    card.addEventListener('dragstart', () => {
      dragged = card;
      card.classList.add('dragging');
    });
    card.addEventListener('dragend', () => {
      card.classList.remove('dragging');
      dragged = null;
    });
  });

  board.querySelectorAll('.pipeline-col-body').forEach((col) => {
    col.addEventListener('dragover', (e) => {
      e.preventDefault();
      col.classList.add('drag-over');
    });
    col.addEventListener('dragleave', () => col.classList.remove('drag-over'));
    col.addEventListener('drop', async (e) => {
      e.preventDefault();
      col.classList.remove('drag-over');
      if (!dragged) return;
      const estado = col.closest('.pipeline-col').dataset.estado;
      const id = dragged.dataset.id;
      col.appendChild(dragged);
      try {
        const res = await fetch(board.dataset.moveUrl || '/pipeline/mover', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cliente_id: parseInt(id, 10), estado: estado }),
        });
        if (!res.ok) throw new Error('Error al mover');
      } catch (err) {
        alert('No se pudo actualizar el estado');
        location.reload();
      }
    });
  });
})();
