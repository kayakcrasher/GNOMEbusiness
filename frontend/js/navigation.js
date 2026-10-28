"use strict";

(() => {
  const main = document.querySelector("main");
  const nav = document.querySelector(".sidebar nav");

  if (!main || !nav) return;

  const routes = {
    dashboard: {
      title: "Dashboard",
      target: null
    },
    leads: {
      title: "Leads",
      target: "#leads"
    },
    pipeline: {
      title: "Pipeline",
      target: "#pipeline"
    },
    appointments: {
      title: "Appointments",
      target: "#appointments"
    },
    outreach: {
      title: "Outreach",
      target: "#outreach"
    },
    settings: {
      title: "Settings",
      target: "#settings"
    }
  };

  const heading = document.querySelector(".topbar h1");
  const eyebrow = document.querySelector(".topbar .eyebrow");

  const outreach = document.querySelector("#outreach");

  if (outreach && !outreach.hasChildNodes()) {
    outreach.classList.add("panel", "module-panel");

    outreach.innerHTML = `
      <div class="panel-head">
        <h3>GNOMEreach</h3>
        <span class="pill">Coming Next</span>
      </div>
      <p>
        Your outreach command center will manage
        prospect messages, drafts, and campaigns.
      </p>
    `;
  }

  let settings = document.querySelector("#settings");

  if (!settings) {
    settings = document.createElement("section");
    settings.id = "settings";
    settings.className = "panel module-panel";
    settings.innerHTML = `
      <div class="panel-head">
        <h3>Workspace Settings</h3>
      </div>
      <p>Local development workspace.</p>
      <p id="workspace-number"></p>
    `;
    main.append(settings);
  }

  const workspaceNumber =
    settings.querySelector("#workspace-number");

  if (workspaceNumber) {
    workspaceNumber.textContent =
      "Business ID: " +
      (new URLSearchParams(location.search)
        .get("business") || "Not selected");
  }

  const dashboardSections = [
    ...main.children
  ].filter(element =>
    element !== settings &&
    element !== outreach
  );

  const views = {
    dashboard: dashboardSections,
    leads: [document.querySelector("#leads")],
    pipeline: [document.querySelector("#pipeline")],
    appointments: [document.querySelector("#appointments")],
    outreach: [outreach],
    settings: [settings]
  };

  function navigate(view) {
    if (!routes[view]) view = "dashboard";

    for (const element of main.children) {
      if (element === document.querySelector(".topbar")) {
        continue;
      }
      element.hidden = true;
    }

    for (const element of views[view]) {
      if (element) element.hidden = false;
    }

    if (heading) {
      heading.textContent = routes[view].title;
    }

    if (eyebrow) {
      eyebrow.textContent =
        view === "dashboard"
          ? "WORKSPACE OVERVIEW"
          : "GNOMEBUSINESS / " + view.toUpperCase();
    }

    nav.querySelectorAll("a").forEach(link => {
      const name = link.dataset.view;

      link.classList.toggle("active", name === view);

      if (name === view) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    });

    history.replaceState(
      null,
      "",
      location.pathname + location.search + "#" + view
    );

    window.scrollTo(0, 0);
  }

  nav.querySelectorAll("a").forEach(link => {
    const label = link.textContent.toLowerCase();

    const view =
      label.includes("dashboard") ? "dashboard" :
      label.includes("leads") ? "leads" :
      label.includes("pipeline") ? "pipeline" :
      label.includes("appointments") ? "appointments" :
      label.includes("outreach") ? "outreach" :
      null;

    if (!view) return;

    link.dataset.view = view;

    link.addEventListener("click", event => {
      event.preventDefault();
      navigate(view);
    });
  });

  // Add Settings to the existing sidebar.
  if (!nav.querySelector('[data-view="settings"]')) {
    const link = document.createElement("a");
    link.href = "#settings";
    link.dataset.view = "settings";
    link.textContent = "⚙ Settings";

    link.addEventListener("click", event => {
      event.preventDefault();
      navigate("settings");
    });

    nav.append(link);
  }

  // Connect the existing hero CTA.
  document.querySelectorAll('a[href="#leads"]')
    .forEach(link => {
      if (nav.contains(link)) return;

      link.addEventListener("click", event => {
        event.preventDefault();
        navigate("leads");
      });
    });

  window.addEventListener("hashchange", () => {
    navigate(location.hash.slice(1));
  });

  navigate(location.hash.slice(1) || "dashboard");
})();
