"use strict";

(() => {
  const panel = document.querySelector("#outreach");
  if (!panel) return;

  const businessId = Number(
    new URLSearchParams(location.search).get("business")
  );

  const section = document.createElement("section");
  section.className = "conversion-section";

  section.innerHTML = `
    <h3>Convert Prospect to Appointment</h3>
    <p>Book a meeting and move the lead to Booked.</p>

    <form id="conversion-form">
      <label>
        Prospect
        <select name="lead_id" required></select>
      </label>

      <label>
        Meeting Title
        <input name="title" required maxlength="200"
          placeholder="Discovery call">
      </label>

      <label>
        Meeting Date & Time
        <input name="starts_at"
          type="datetime-local" required>
      </label>

      <button type="submit">Book Meeting</button>
      <p id="conversion-message" role="status"></p>
    </form>
  `;

  panel.append(section);

  const form = section.querySelector("form");
  const select = form.querySelector("select");
  const message = section.querySelector("#conversion-message");

  async function loadProspects() {
    const response = await fetch(
      `/api/businesses/${businessId}/leads`
    );

    if (!response.ok) {
      throw new Error("Unable to load prospects");
    }

    const data = await response.json();
    select.replaceChildren();

    for (const lead of data.leads) {
      if (lead.status === "closed") continue;

      const option = document.createElement("option");
      option.value = lead.id;
      option.textContent =
        `${lead.company} (${lead.status})`;

      select.append(option);
    }

    if (!select.options.length) {
      message.textContent = "No active prospects available.";
    }
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();

    const button = form.querySelector("button");
    const values = new FormData(form);
    const timestamp = new Date(values.get("starts_at"));

    if (Number.isNaN(timestamp.getTime())) {
      message.textContent = "Choose a valid meeting time.";
      return;
    }

    button.disabled = true;
    message.textContent = "Booking meeting...";

    try {
      const response = await fetch(
        "/api/conversions/book",
        {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            business_id: businessId,
            lead_id: Number(values.get("lead_id")),
            title: values.get("title"),
            starts_at: timestamp.toISOString()
          })
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(
          typeof error.detail === "string"
            ? error.detail
            : "Booking failed"
        );
      }

      message.textContent =
        "Meeting booked! Lead moved to Booked.";

      form.reset();
      await loadProspects();

      if (typeof loadDashboard === "function") {
        await loadDashboard();
      }

      window.dispatchEvent(
        new Event("gnome:appointment-booked")
      );
    } catch (error) {
      message.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });

  if (Number.isSafeInteger(businessId) && businessId > 0) {
    loadProspects().catch(error => {
      message.textContent = error.message;
    });
  } else {
    message.textContent = "Select a business first.";
  }
})();
