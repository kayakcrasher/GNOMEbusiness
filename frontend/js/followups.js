"use strict";

(() => {
  const dialog = document.querySelectorAll(
    ".lead-dialog"
  )[1];

  if (!dialog) return;

  const saveButton = dialog.querySelector(".save-lead");

  const section = document.createElement("section");
  section.className = "followup-editor";

  section.innerHTML = `
    <label>
      Follow-up Date
      <input type="date" id="followup-date">
    </label>

    <label>
      Notes
      <textarea id="followup-notes"
        rows="4"
        maxlength="5000"
        placeholder="What happens next?"></textarea>
    </label>

    <button type="button" class="save-followup">
      Save Follow-up
    </button>

    <p class="followup-message" role="status"></p>
  `;

  saveButton.after(section);

  const dateInput = section.querySelector("#followup-date");
  const notesInput = section.querySelector("#followup-notes");
  const message = section.querySelector(".followup-message");
  const save = section.querySelector(".save-followup");

  let currentLead = null;

  const table = document.querySelector("#lead-rows");

  table.addEventListener("click", async event => {
    const row = event.target.closest("tr[data-lead-id]");
    if (!row) return;

    const response = await fetch(
      `/api/leads/${row.dataset.leadId}`
    );

    if (!response.ok) return;

    currentLead = await response.json();

    dateInput.value = currentLead.follow_up || "";
    notesInput.value = currentLead.notes || "";
    message.textContent = "";
  });

  save.addEventListener("click", async () => {
    if (!currentLead) return;

    save.disabled = true;
    message.textContent = "";

    try {
      const response = await fetch(
        `/api/leads/${currentLead.id}/followup`,
        {
          method: "PATCH",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            follow_up: dateInput.value || null,
            notes: notesInput.value
          })
        }
      );

      if (!response.ok) {
        throw new Error("Unable to save follow-up");
      }

      message.textContent = "Follow-up saved.";

      window.dispatchEvent(
        new Event("gnome:followups-changed")
      );

    } catch (error) {
      message.textContent = error.message;
    } finally {
      save.disabled = false;
    }
  });
})();
