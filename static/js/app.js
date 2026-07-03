document.addEventListener("change", (e) => {
  if (e.target.matches(".task-toggle")) {
    const id = e.target.dataset.taskId;
    fetch(`/tasks/${id}/toggle`, { method: "POST" }).then(() => {
      const label = e.target.parentElement.querySelector("div > div");
      if (label) label.classList.toggle("line-through");
      if (label) label.classList.toggle("text-slate-400");
    });
  }
});

// Kanban drag-and-drop
let draggedId = null;

document.addEventListener("dragstart", (e) => {
  const card = e.target.closest(".kanban-card");
  if (!card) return;
  draggedId = card.dataset.oppId;
  e.dataTransfer.effectAllowed = "move";
});

document.querySelectorAll(".kanban-column").forEach((col) => {
  col.addEventListener("dragover", (e) => {
    e.preventDefault();
    col.classList.add("drag-over");
  });
  col.addEventListener("dragleave", () => col.classList.remove("drag-over"));
  col.addEventListener("drop", (e) => {
    e.preventDefault();
    col.classList.remove("drag-over");
    if (!draggedId) return;
    const stage = col.dataset.stage;
    fetch(`/opportunities/${draggedId}/stage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stage }),
    }).then((res) => {
      if (res.ok) location.reload();
    });
  });
});
