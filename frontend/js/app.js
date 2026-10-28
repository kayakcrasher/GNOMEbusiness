const pipeline = [
  { name: "New", count: 64 },
  { name: "Contacted", count: 38 },
  { name: "Interested", count: 18 },
  { name: "Booked", count: 8 }
];

const leads = [
  { company: "Oakridge Supply", contact: "Alex Morgan", status: "Interested" },
  { company: "Pine Valley Co.", contact: "Taylor Reed", status: "Contacted" },
  { company: "Summit Works", contact: "Jordan Lee", status: "New" }
];

const bars = document.querySelector("#pipeline-bars");

pipeline.forEach(item => {
  const row = document.createElement("div");
  row.className = "pipeline-row";

  const label = document.createElement("div");
  label.className = "pipeline-label";

  const name = document.createElement("span");
  name.textContent = item.name;

  const count = document.createElement("span");
  count.textContent = item.count;

  label.append(name, count);

  const track = document.createElement("div");
  track.className = "track";

  const fill = document.createElement("div");
  fill.className = "fill";
  fill.style.width = `${item.count / 64 * 100}%`;

  track.append(fill);
  row.append(label, track);
  bars.append(row);
});

const table = document.querySelector("#lead-rows");

leads.forEach(lead => {
  const tr = document.createElement("tr");

  [lead.company, lead.contact].forEach(value => {
    const td = document.createElement("td");
    td.textContent = value;
    tr.append(td);
  });

  const statusCell = document.createElement("td");
  const badge = document.createElement("span");
  badge.className = "status";
  badge.textContent = lead.status;
  statusCell.append(badge);
  tr.append(statusCell);
  table.append(tr);
});

// GNOMEbusiness — API connectivity indicator

const indicator = document.createElement("div");
indicator.className = "api-indicator";
indicator.setAttribute("role", "status");
indicator.textContent = "Checking API...";

document.querySelector(".topbar").append(indicator);

fetch("/api/health")
  .then(response => {
    if (!response.ok) throw new Error("API unavailable");
    return response.json();
  })
  .then(data => {
    indicator.textContent =
      data.status === "operational"
        ? "● SYSTEM ONLINE"
        : "● SYSTEM WARNING";
    indicator.style.color =
      data.status === "operational" ? "#5bf5ae" : "#f0c879";
  })
  .catch(() => {
    indicator.textContent = "● API OFFLINE";
    indicator.style.color = "#ff8181";
  });
