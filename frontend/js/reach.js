"use strict";

(() => {
  const panel = document.querySelector("#outreach");
  if (!panel) return;

  const businessId = Number(
    new URLSearchParams(location.search).get("business")
  );

  panel.classList.add("panel", "reach-panel");

  const editor = document.createElement("div");
  editor.className = "reach-workspace";

  editor.innerHTML = `
    <div class="panel-head">
      <h3>GNOMEreach · Outreach Studio</h3>
      <span class="pill">Prospect Outreach</span>
    </div>

    <form id="reach-form">
      <label>
        Select Prospect
        <select name="lead_id" required></select>
      </label>

      <label>
        Email Subject
        <input name="subject" required maxlength="200"
          placeholder="Quick question about your business">
      </label>

      <label>
        Message
        <textarea name="body" required rows="7"
          maxlength="10000"
          placeholder="Write a personalized introduction..."></textarea>
      </label>

      <button type="submit">Save Outreach Draft</button>
      <p id="reach-message" role="status"></p>
    </form>

    <h3>Outreach History</h3>
    <div id="reach-history"></div>
  `;

  panel.replaceChildren(editor);

  const form = editor.querySelector("#reach-form");
  const select = form.querySelector("select");
  const history = editor.querySelector("#reach-history");
  const feedback = editor.querySelector("#reach-message");

  async function loadLeads() {
    const response = await fetch(
      `/api/businesses/${businessId}/leads`
    );

    if (!response.ok) throw new Error("Unable to load leads");

    const data = await response.json();
    select.replaceChildren();

    for (const lead of data.leads) {
      const option = document.createElement("option");
      option.value = lead.id;
      option.textContent =
        `${lead.company} · ${lead.contact || "No contact"}`;
      select.append(option);
    }

    if (!data.leads.length) {
      feedback.textContent =
        "Create a lead in GNOMEleads first.";
    }
  }

  async function loadHistory() {
    const response = await fetch(
      `/api/businesses/${businessId}/outreach`
    );

    if (!response.ok) throw new Error("Unable to load history");

    const data = await response.json();
    history.replaceChildren();

    if (!data.messages.length) {
      history.textContent = "No outreach drafts yet.";
      return;
    }

    for (const message of data.messages) {
      const card = document.createElement("article");
      card.className = "reach-message-card";

      const title = document.createElement("strong");
      title.textContent = message.subject;

      const recipient = document.createElement("small");
      recipient.textContent =
        `${message.company} · ${message.status}`;

      const body = document.createElement("p");
      body.textContent = message.body;

      card.append(title, recipient, body);

      if (message.status !== "sent") {
        const nextStatus =
          message.status === "draft" ? "ready" : "sent";

        const button = document.createElement("button");
        button.type = "button";
        button.textContent =
          nextStatus === "ready"
            ? "Mark Ready"
            : "Record as Sent";

        button.addEventListener("click", async () => {
          if (nextStatus === "sent" &&
              !window.confirm(
                "Confirm you already sent this message externally?"
              )) return;

          button.disabled = true;

          try {
            const response = await fetch(
              `/api/outreach/${message.id}`,
              {
                method: "PATCH",
                headers: {
                  "Content-Type": "application/json"
                },
                body: JSON.stringify({
                  status: nextStatus
                })
              }
            );

            if (!response.ok) {
              throw new Error("Status update failed");
            }

            await loadHistory();
          } catch (error) {
            feedback.textContent = error.message;
            button.disabled = false;
          }
        });

        card.append(button);
      }

      history.append(card);
    }
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();

    const button = form.querySelector('[type="submit"]');
    const values = new FormData(form);

    button.disabled = true;
    feedback.textContent = "";

    try {
      const response = await fetch("/api/outreach", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          business_id: businessId,
          lead_id: Number(values.get("lead_id")),
          subject: values.get("subject"),
          body: values.get("body")
        })
      });

      if (!response.ok) {
        throw new Error("Unable to save draft");
      }

      form.reset();
      feedback.textContent = "Draft saved.";
      await loadHistory();
    } catch (error) {
      feedback.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });

  if (Number.isSafeInteger(businessId) && businessId > 0) {
    Promise.all([loadLeads(), loadHistory()])
      .catch(error => {
        feedback.textContent = error.message;
      });
  } else {
    feedback.textContent = "Select a business first.";
  }
})();
