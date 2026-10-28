"use strict";

const params = new URLSearchParams(location.search);
const businessId = Number(params.get("business"));

const statusNames = [
  "new",
  "contacted",
  "interested",
  "booked",
  "closed",
];

function makeElement(tag, text, className) {
  const el = document.createElement(tag);
  el.textContent = text;

  if (className) el.className = className;

  return el;
}

function showEmpty(message) {
  document.querySelector("#pipeline-bars")
    .replaceChildren(
      makeElement("p", message, "empty-message")
    );

  document.querySelector("#lead-rows")
    .replaceChildren();
}

async function loadDashboard() {
  if (!Number.isSafeInteger(businessId) || businessId < 1) {
    showEmpty("Select a business to view live data.");
    return;
  }

  try {
    const response = await fetch(
      `/api/businesses/${businessId}/dashboard`
    );

    if (!response.ok) {
      throw new Error("Dashboard unavailable");
    }

    const data = await response.json();

    const cards = document.querySelectorAll(".stat strong");

    cards[0].textContent = data.total_leads;
    cards[1].textContent = data.pipeline.booked;

    // Replies and follow-ups aren't tracked yet.
    cards[2].textContent = "—";
    cards[3].textContent = "—";

    const bars = document.querySelector("#pipeline-bars");
    bars.replaceChildren();

    const maximum = Math.max(
      1,
      ...Object.values(data.pipeline)
    );

    for (const status of statusNames) {
      const count = data.pipeline[status] || 0;

      const row = makeElement("div", "", "pipeline-row");
      const label = makeElement("div", "", "pipeline-label");

      label.append(
        makeElement("span", status.toUpperCase()),
        makeElement("span", String(count))
      );

      const track = makeElement("div", "", "track");
      const fill = makeElement("div", "", "fill");

      fill.style.width = `${count / maximum * 100}%`;

      track.append(fill);
      row.append(label, track);
      bars.append(row);
    }

    const table = document.querySelector("#lead-rows");
    table.replaceChildren();

    for (const lead of data.recent_leads) {
      const row = document.createElement("tr");
      row.dataset.leadId = String(lead.id);
      row.classList.add("clickable-lead");
      row.tabIndex = 0;
      row.setAttribute("role", "button");
      row.setAttribute(
        "aria-label",
        `View ${lead.company}`
      );

      row.append(
        makeElement("td", lead.company),
        makeElement("td", lead.contact || "—")
      );

      const cell = document.createElement("td");
      cell.append(
        makeElement("span", lead.status, "status")
      );

      row.append(cell);
      table.append(row);
    }

    if (!data.recent_leads.length) {
      const row = document.createElement("tr");
      const cell = makeElement(
        "td",
        "No leads yet. Ready for your first prospect."
      );
      cell.colSpan = 3;
      row.append(cell);
      table.append(row);
    }

  } catch (error) {
    showEmpty("Unable to load business dashboard.");
    console.error(error);
  }
}

loadDashboard();
