// tailwind-tables.js
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("div.overflow-x-auto table, table").forEach(tabla => {
    tabla.classList.add("min-w-full", "table-auto", "border-collapse");

    tabla.querySelectorAll("th, td").forEach(td => {
      td.classList.add("border", "border-gray-300", "px-3", "py-1");
    });

    tabla.querySelectorAll("tr:nth-child(even)").forEach(tr => {
      tr.classList.add("bg-gray-50");
    });
  });
});
