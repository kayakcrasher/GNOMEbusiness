(() => {
  const $ = id => document.getElementById(id);

  function message(value) {
    $("job-message").textContent = value;
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      }
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "HTTP " + response.status
      );
    }

    return data;
  }

  function element(tag, value) {
    const node = document.createElement(tag);
    node.textContent = String(value ?? "");
    return node;
  }

  async function loadAgents() {
    const select = $("job-agent");
    select.replaceChildren();

    const data = await api("/api/connectors/manage");

    const eligible = data.connectors.filter(
      agent => agent.scopes.includes("jobs:work")
    );

    for (const agent of eligible) {
      const option = document.createElement("option");
      option.value = agent.id;
      option.textContent = agent.name;
      select.append(option);
    }

    $("launch-job").disabled = eligible.length === 0;

    if (!eligible.length) {
      message(
        "Connect an agent with jobs:work permission first."
      );
    }
  }

  async function loadJobs() {
    const list = $("job-list");
    list.replaceChildren();

    const data = await api("/api/customer/jobs");

    if (!data.jobs.length) {
      list.append(element("p", "No jobs queued yet."));
      return;
    }

    for (const job of data.jobs) {
      const entry = document.createElement("div");
      entry.className = "job-entry";

      entry.append(
        element("strong", "#" + job.id + " · " + job.kind),
        element("small", "Status: " + job.status),
        element(
          "p",
          job.instructions.request ||
          JSON.stringify(job.instructions)
        )
      );

      if (job.status === "completed" && job.result) {
        const result = document.createElement("pre");
        result.textContent = JSON.stringify(
          job.result, null, 2
        );
        entry.append(result);
      }

      list.append(entry);
    }
  }

  async function refresh() {
    try {
      await Promise.all([
        loadAgents(),
        loadJobs()
      ]);
    } catch (error) {
      message(error.message);
    }
  }

  $("launch-job").addEventListener("click", async () => {
    const button = $("launch-job");
    const agentId = Number($("job-agent").value);
    const kind = $("job-kind").value;
    const instructions = $("job-instructions").value.trim();

    if (!agentId || !instructions) {
      message("Choose an agent and enter instructions.");
      return;
    }

    button.disabled = true;
    message("");

    try {
      const data = await api(
        "/api/customer/jobs",
        {
          method: "POST",
          body: JSON.stringify({
            agent_id: agentId,
            kind,
            instructions
          })
        }
      );

      $("job-instructions").value = "";
      message("Job #" + data.id + " queued.");
      await loadJobs();
    } catch (error) {
      message(error.message);
    } finally {
      button.disabled = false;
    }
  });

  $("refresh-jobs").addEventListener("click", refresh);

  refresh();
})();
