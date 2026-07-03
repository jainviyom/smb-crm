// "+ New" dropdown menu
const newMenuBtn = document.getElementById("new-menu-btn");
const newMenu = document.getElementById("new-menu");
if (newMenuBtn) {
  newMenuBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    newMenu.classList.toggle("hidden");
  });
  document.addEventListener("click", () => newMenu.classList.add("hidden"));
}

// New-record modals
const modalOverlay = document.getElementById("modal-overlay");
function openModal(id) {
  document.querySelectorAll(".modal-panel").forEach((p) => p.classList.add("hidden"));
  document.getElementById(id).classList.remove("hidden");
  modalOverlay.classList.remove("hidden");
}
function closeModal() {
  modalOverlay.classList.add("hidden");
}
document.querySelectorAll("[data-open-modal]").forEach((btn) => {
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    newMenu.classList.add("hidden");
    openModal(btn.dataset.openModal);
  });
});
document.querySelectorAll(".modal-close").forEach((btn) => btn.addEventListener("click", closeModal));
if (modalOverlay) {
  modalOverlay.addEventListener("click", (e) => {
    if (e.target === modalOverlay) closeModal();
  });
}
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && modalOverlay && !modalOverlay.classList.contains("hidden")) closeModal();
});

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
