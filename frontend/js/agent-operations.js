(() => {
  const $ = id => document.getElementById(id);

  function item(tag, value) {
    const node = document.createElement(tag);
    node.textContent = String(value ?? "");
    return node;
  }

  async function refresh() {
    $("operations-message").textContent = "Loading...";

    try {
      const response = await fetch(
        "/api/customer/operations",
        {
          credentials: "same-origin",
          cache: "no-store"
        }
      );

      if (!response.ok) {
        throw new Error("HTTP " + response.status);
      }

      const data = await response.json();

      for (const status of [
        "queued", "working", "completed"
      ]) {
        $("jobs-" + status).textContent =
          data.summary[status] ?? 0;
      }

      const agents = $("operations-agents");
      agents.replaceChildren();

      if (!data.agents.length) {
        agents.append(
          item("p", "No connected agents.")
        );
      }

      for (const agent of data.agents) {
        const card = document.createElement("div");
        card.className = "agent-entry";

        const state = {
          online: "🟢 Online",
          offline: "🔴 Offline",
          never_connected: "⚪ Never connected"
        }[agent.connection_status] || "Unknown";

        card.append(
          item("strong", agent.name),
          item("small", state),
          item(
            "p",
            "Permissions: " + agent.scopes.join(", ")
          ),
          item(
            "small",
            "Last seen: " +
            (agent.last_seen || "Never")
          )
        );

        agents.append(card);
      }

      const activity = $("operations-activity");
      activity.replaceChildren();

      if (!data.jobs.length) {
        activity.append(
          item("p", "No recent activity.")
        );
      }

      for (const job of data.jobs) {
        const card = document.createElement("div");
        card.className = "job-entry";

        card.append(
          item("strong", "#" + job.id + " · " + job.kind),
          item("small", "Status: " + job.status),
          item(
            "small",
            "Submitted by: " +
            (job.created_by_name || "Unknown")
          ),
          item(
            "small",
            "Claimed by: " +
            (job.claimed_by_name || "Not claimed")
          )
        );

        activity.append(card);
      }

      $("operations-message").textContent =
        "Operations updated.";
    } catch (error) {
      $("operations-message").textContent =
        "Unable to load operations: " + error.message;
    }
  }

  $("refresh-operations").addEventListener(
    "click",
    refresh
  );

  refresh();
})();
