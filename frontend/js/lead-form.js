"use strict";

(() => {
  const businessId = Number(
    new URLSearchParams(location.search).get("business")
  );

  const validBusiness =
    Number.isSafeInteger(businessId) && businessId > 0;

  const panel = document.querySelector(".leads-panel");
  const heading = panel?.querySelector(".panel-head");

  if (!panel || !heading) return;

  const button = document.createElement("button");
  button.className = "add-lead-btn";
  button.type = "button";
  button.textContent = "+ Add Lead";
  button.disabled = !validBusiness;

  const dialog = document.createElement("dialog");
  dialog.className = "lead-dialog";

  dialog.innerHTML = `
    <form id="new-lead-form">
      <div class="form-heading">
        <div>
          <span class="form-eyebrow">GNOMELEADS</span>
          <h2>New Lead</h2>
          <p>Add a prospect to your pipeline.</p>
        </div>
        <button type="button"
          class="close-dialog"
          aria-label="Close">×</button>
      </div>

      <label>
        Company *
        <input name="company" required
          maxlength="200"
          placeholder="Company name">
      </label>

      <label>
        Contact
        <input name="contact"
          placeholder="Contact name">
      </label>

      <label>
        Email
        <input name="email" type="email"
          placeholder="name@company.com">
      </label>

      <p class="form-message" role="status"></p>

      <button class="save-lead" type="submit">
        Save Lead
      </button>
    </form>
  `;

  heading.append(button);
  document.body.append(dialog);

  const form = dialog.querySelector("form");
  const message = dialog.querySelector(".form-message");
  const save = dialog.querySelector(".save-lead");

  button.addEventListener("click", () => {
    form.reset();
    message.textContent = "";
    dialog.showModal();
  });

  dialog.querySelector(".close-dialog")
    .addEventListener("click", () => dialog.close());

  dialog.addEventListener("click", event => {
    if (event.target === dialog) dialog.close();
  });

  form.addEventListener("submit", async event => {
    event.preventDefault();

    if (!validBusiness) return;

    const fields = new FormData(form);

    const payload = {
      business_id: businessId,
      company: String(fields.get("company")).trim(),
      contact: String(fields.get("contact")).trim(),
      email: String(fields.get("email")).trim()
    };

    if (!payload.company) {
      message.textContent = "Company is required.";
      return;
    }

    save.disabled = true;
    save.textContent = "Saving...";
    message.textContent = "";

    try {
      const response = await fetch("/api/leads", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(
          `Unable to save lead (${response.status})`
        );
      }

      dialog.close();
      form.reset();

      if (typeof loadDashboard === "function") {
        await loadDashboard();
      }

    } catch (error) {
      message.textContent = error.message;
    } finally {
      save.disabled = false;
      save.textContent = "Save Lead";
    }
  });
})();
