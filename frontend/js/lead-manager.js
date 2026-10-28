"use strict";

(() => {
  const statuses = [
    "new",
    "contacted",
    "interested",
    "booked",
    "closed"
  ];

  const table = document.querySelector("#lead-rows");
  if (!table) return;

  const dialog = document.createElement("dialog");
  dialog.className = "lead-dialog";

  dialog.innerHTML = `
    <div class="form-heading">
      <div>
        <span class="form-eyebrow">GNOMELEADS</span>
        <h2 id="detail-company">Lead Details</h2>
        <p id="detail-contact"></p>
      </div>
      <button class="close-dialog"
        type="button" aria-label="Close">×</button>
    </div>

    <label for="detail-status">Pipeline Status</label>
    <select id="detail-status"></select>

    <p class="form-message" role="status"></p>

    <button class="save-lead" type="button">
      Update Lead
    </button>
  `;

  document.body.append(dialog);

  const selector = dialog.querySelector("#detail-status");
  const save = dialog.querySelector(".save-lead");
  const message = dialog.querySelector(".form-message");

  let activeLead = null;

  statuses.forEach(status => {
    const option = document.createElement("option");
    option.value = status;
    option.textContent =
      status.charAt(0).toUpperCase() + status.slice(1);
    selector.append(option);
  });

  dialog.querySelector(".close-dialog")
    .addEventListener("click", () => dialog.close());

  table.addEventListener("click", async event => {
    const row = event.target.closest("tr[data-lead-id]");
    if (!row) return;

    const id = Number(row.dataset.leadId);

    try {
      const response = await fetch(`/api/leads/${id}`);
      if (!response.ok) throw new Error("Lead unavailable");

      activeLead = await response.json();

      dialog.querySelector("#detail-company")
        .textContent = activeLead.company;

      dialog.querySelector("#detail-contact")
        .textContent = activeLead.contact || "No contact assigned";

      selector.value = activeLead.status;
      message.textContent = "";
      dialog.showModal();
    } catch (error) {
      console.error(error);
    }
  });

  save.addEventListener("click", async () => {
    if (!activeLead) return;

    save.disabled = true;
    save.textContent = "Updating...";
    message.textContent = "";

    try {
      const response = await fetch(
        `/api/leads/${activeLead.id}`,
        {
          method: "PATCH",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            status: selector.value
          })
        }
      );

      if (!response.ok) throw new Error("Update failed");

      dialog.close();

      if (typeof loadDashboard === "function") {
        await loadDashboard();
      }
    } catch (error) {
      message.textContent = error.message;
    } finally {
      save.disabled = false;
      save.textContent = "Update Lead";
    }
  });
})();
