"use strict";

(() => {
  const params = new URLSearchParams(location.search);
  const businessId = Number(params.get("business"));

  const panel = document.querySelector("#appointments");

  if (!panel) return;

  const tasks = document.createElement("div");
  tasks.id = "live-tasks";

  panel.querySelectorAll(".task").forEach(
    element => element.hidden = true
  );

  panel.append(tasks);

  async function refresh() {
    if (!Number.isSafeInteger(businessId) || businessId < 1) {
      tasks.textContent = "Select a business.";
      return;
    }

    try {
      const response = await fetch(
        `/api/businesses/${businessId}/followups`
      );

      if (!response.ok) throw new Error("Tasks unavailable");

      const data = await response.json();
      tasks.replaceChildren();

      if (!data.followups.length) {
        tasks.textContent = "No follow-ups scheduled.";
        return;
      }

      for (const item of data.followups) {
        const row = document.createElement("div");
        row.className = "task";

        const title = document.createElement("strong");
        title.textContent = item.company;

        const detail = document.createElement("small");
        detail.textContent =
          `${item.follow_up} · ${item.notes || "Follow up"}`;

        row.append(title, detail);
        tasks.append(row);
      }

    } catch (error) {
      tasks.textContent = error.message;
    }
  }

  window.addEventListener(
    "gnome:followups-changed",
    refresh
  );

  refresh();
})();
