"use strict";

(() => {
  const main = document.querySelector("main");
  const nav = document.querySelector(".sidebar nav");

  if (!main || !nav) return;

  const report = document.createElement("section");
  report.id = "reports";
  report.className = "panel reports-panel";
  report.hidden = true;

  report.innerHTML = `
    <div class="panel-head">
      <h3>Client Results</h3>
      <span class="pill">Live Metrics</span>
    </div>

    <p class="reports-intro">
      Track prospect activity and booked meetings.
    </p>

    <div class="reports-grid" id="report-metrics"></div>

    <p class="reports-note">
      Sent messages are manually recorded, not delivery-verified.
      Conversion rate = unique leads with non-cancelled
      appointments divided by total leads.
    </p>
  `;

  main.append(report);

  const link = document.createElement("a");
  link.href = "#reports";
  link.textContent = "▤ Reports";
  link.dataset.view = "reports";
  nav.append(link);

  const metrics = report.querySelector("#report-metrics");

  const businessId = Number(
    new URLSearchParams(location.search).get("business")
  );

  async function refresh() {
    if (!Number.isSafeInteger(businessId) || businessId < 1) {
      metrics.textContent = "Select a business.";
      return;
    }

    try {
      const response = await fetch(
        `/api/businesses/${businessId}/report`
      );

      if (!response.ok) throw new Error("Report unavailable");

      const data = await response.json();

      const fields = [
        ["Total Prospects", data.total_leads],
        ["Contacted Prospects", data.contacted_prospects],
        ["Sent Messages", data.sent_messages],
        ["Active/Completed Bookings", data.appointments],
        ["Unique Booked Prospects", data.booked_leads],
        ["Completed Meetings", data.completed_appointments],
        ["Lead-to-Booking Rate", `${data.conversion_rate}%`]
      ];

      metrics.replaceChildren();

      for (const [label, value] of fields) {
        const card = document.createElement("article");
        card.className = "report-metric";

        const name = document.createElement("small");
        name.textContent = label;

        const number = document.createElement("strong");
        number.textContent = value;

        card.append(name, number);
        metrics.append(card);
      }
    } catch (error) {
      metrics.textContent = error.message;
    }
  }

  link.addEventListener("click", event => {
    event.preventDefault();

    for (const element of main.children) {
      if (!element.classList.contains("topbar")) {
        element.hidden = true;
      }
    }

    report.hidden = false;

    nav.querySelectorAll("a").forEach(item => {
      item.classList.toggle("active", item === link);
    });

    const heading = document.querySelector(".topbar h1");
    if (heading) heading.textContent = "Reports";

    history.replaceState(
      null, "", location.pathname + location.search + "#reports"
    );

    window.scrollTo(0, 0);
    refresh();
  });

  // Existing navigation remains responsible for other views.
  nav.querySelectorAll("a").forEach(item => {
    if (item === link) return;

    item.addEventListener("click", () => {
      report.hidden = true;
    });
  });

  if (location.hash === "#reports") {
    link.click();
  }
})();
