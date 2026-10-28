"use strict";

(() => {
  const panel = document.querySelector("#appointments");
  if (!panel) return;

  const existing = panel.querySelector("#live-tasks");
  if (existing) existing.remove();

  panel.querySelectorAll(".task").forEach(
    item => item.hidden = true
  );

  const container = document.createElement("div");
  container.id = "live-tasks";
  panel.append(container);

  async function refreshTasks() {
    const businessId = Number(
      new URLSearchParams(location.search)
        .get("business")
    );

    if (!Number.isSafeInteger(businessId) || businessId < 1) {
      container.textContent = "Select a business.";
      return;
    }

    try {
      const response = await fetch(
        `/api/businesses/${businessId}/tasks`
      );

      if (!response.ok) {
        throw new Error("Unable to load tasks");
      }

      const data = await response.json();
      container.replaceChildren();

      const summary = document.createElement("div");
      summary.className = "task-summary";

      for (const type of ["overdue", "today", "upcoming"]) {
        const item = document.createElement("div");
        item.className = `task-count ${type}`;

        const number = document.createElement("strong");
        number.textContent = data.summary[type];

        const label = document.createElement("small");
        label.textContent = type.toUpperCase();

        item.append(number, label);
        summary.append(item);
      }

      container.append(summary);

      if (!data.tasks.length) {
        const empty = document.createElement("p");
        empty.textContent = "All caught up. No active follow-ups.";
        container.append(empty);
        return;
      }

      for (const task of data.tasks) {
        const row = document.createElement("div");
        row.className = `task live-task ${task.due}`;

        const content = document.createElement("div");

        const title = document.createElement("strong");
        title.textContent = task.company;

        const detail = document.createElement("small");
        detail.textContent =
          `${task.follow_up} · ${task.notes || "Follow up"}`;

        content.append(title, detail);

        const done = document.createElement("button");
        done.type = "button";
        done.className = "complete-task";
        done.textContent = "Done";
        done.setAttribute(
          "aria-label",
          `Complete follow-up for ${task.company}`
        );

        done.addEventListener("click", async () => {
          done.disabled = true;

          try {
            const response = await fetch(
              `/api/leads/${task.id}/complete-followup`,
              {method: "PATCH"}
            );

            if (!response.ok) {
              throw new Error("Completion failed");
            }

            await refreshTasks();
          } catch (error) {
            done.disabled = false;
            done.textContent = "Retry";
            console.error(error);
          }
        });

        row.append(content, done);
        container.append(row);
      }
    } catch (error) {
      container.textContent = error.message;
    }
  }

  window.addEventListener(
    "gnome:followups-changed",
    refreshTasks
  );

  refreshTasks();
})();
