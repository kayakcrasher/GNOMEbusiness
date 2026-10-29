(() => {
  const $ = id => document.getElementById(id);
  const message = value => {
    $("agent-message").textContent = value;
  };

  let currentToken = "";

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

  function hideToken() {
    currentToken = "";
    $("agent-token").textContent = "";
    $("agent-secret").hidden = true;
  }

  function createText(tag, value) {
    const node = document.createElement(tag);
    node.textContent = String(value);
    return node;
  }

  async function loadConnections() {
    const list = $("agent-list");
    list.replaceChildren();

    try {
      const data = await api("/api/connectors/manage");

      if (!data.connectors.length) {
        list.append(
          createText("p", "No active agents yet.")
        );
        return;
      }

      for (const agent of data.connectors) {
        const entry = document.createElement("div");
        entry.className = "agent-entry";

        const heading = createText("strong", agent.name);
        const permissions = createText(
          "p",
          agent.scopes.join(" · ")
        );

        const revoke = document.createElement("button");
        revoke.className = "reject";
        revoke.textContent = "Revoke";

        revoke.addEventListener("click", async () => {
          if (!confirm(
            "Revoke access for " + agent.name + "?"
          )) return;

          revoke.disabled = true;

          try {
            await api(
              "/api/connectors/manage/" +
              agent.id + "/revoke",
              { method: "POST" }
            );

            message("Agent access revoked.");
            await loadConnections();
          } catch (error) {
            message(error.message);
            revoke.disabled = false;
          }
        });

        entry.append(heading, permissions, revoke);
        list.append(entry);
      }
    } catch (error) {
      message(error.message);
      list.append(
        createText(
          "p",
          "Sign in to manage your agent connections."
        )
      );
    }
  }

  $("create-agent").addEventListener("click", async () => {
    const button = $("create-agent");
    const name = $("agent-name").value.trim();

    const scopes = Array.from(
      document.querySelectorAll(
        '#agent-connections input[type="checkbox"]:checked'
      )
    ).map(input => input.value);

    if (!name || !scopes.length) {
      message("Enter a name and choose permissions.");
      return;
    }

    button.disabled = true;
    hideToken();
    message("");

    try {
      const data = await api(
        "/api/connectors/manage",
        {
          method: "POST",
          body: JSON.stringify({ name, scopes })
        }
      );

      currentToken = data.token;
      $("agent-token").textContent = currentToken;
      $("agent-secret").hidden = false;
      $("agent-name").value = "";

      message("Connection created successfully.");
      await loadConnections();
    } catch (error) {
      message(error.message);
    } finally {
      button.disabled = false;
    }
  });

  $("copy-agent-token").addEventListener(
    "click",
    async () => {
      if (!currentToken) return;

      try {
        await navigator.clipboard.writeText(
          currentToken
        );
        message("Token copied.");
      } catch {
        message("Select and copy the token manually.");
      }
    }
  );

  $("hide-agent-token").addEventListener(
    "click",
    hideToken
  );

  $("reload-agents").addEventListener(
    "click",
    loadConnections
  );

  loadConnections();
})();
