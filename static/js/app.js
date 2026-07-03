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

// Notifications dropdown
const notifBtn = document.getElementById("notif-btn");
const notifPanel = document.getElementById("notif-panel");
if (notifBtn) {
  notifBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    notifPanel.classList.toggle("hidden");
  });
  document.addEventListener("click", () => notifPanel.classList.add("hidden"));
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
// Edit-record triggers: populate the matching hidden edit form from data-*
// attributes (data-account_id maps straight to a form field named account_id —
// underscores pass through the dataset API unchanged, only hyphens camelCase).
const ENTITY_PATHS = {
  lead: "leads",
  contact: "contacts",
  account: "accounts",
  opportunity: "opportunities",
  case: "cases",
  task: "tasks",
};

// Dependent "Related To" picker (New/Edit Task modals): only the select
// matching the chosen related_type is visible + enabled, so only its value
// is submitted under its own field name (related_id_<type>).
function updateRelatedPickers(form, type) {
  form.querySelectorAll(".related-picker").forEach((sel) => {
    if (sel.dataset.type === type) {
      sel.classList.remove("hidden");
      sel.disabled = false;
    } else {
      sel.classList.add("hidden");
      sel.disabled = true;
    }
  });
}
document.querySelectorAll(".related-type-select").forEach((sel) => {
  sel.addEventListener("change", () => updateRelatedPickers(sel.closest("form"), sel.value));
});

document.querySelectorAll(".edit-trigger").forEach((btn) => {
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const entity = btn.dataset.entity;
    const id = btn.dataset.id;
    const form = document.getElementById(`form-edit-${entity}`);
    if (!form) return;
    form.action = `/${ENTITY_PATHS[entity]}/${id}/edit`;
    Object.entries(btn.dataset).forEach(([key, val]) => {
      if (key === "entity" || key === "id") return;
      const field = form.querySelector(`[name="${key}"]`);
      if (field) field.value = val;
    });
    if (entity === "task") {
      const relType = btn.dataset.related_type || "";
      updateRelatedPickers(form, relType);
      if (relType) {
        const picker = form.querySelector(`.related-picker[data-type="${relType}"]`);
        if (picker) picker.value = btn.dataset.related_id || "";
      }
    }
    openModal(`modal-edit-${entity}`);
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
