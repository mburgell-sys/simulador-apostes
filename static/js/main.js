// Simulador d'apostes — interaccions del client
// Quan l'usuari clica una quota, mostrem el "ticket" per triar import
// i marquem visualment quina selecció ha fet.

document.addEventListener("DOMContentLoaded", function () {
  const botonsQuota = document.querySelectorAll(".botó-quota");

  botonsQuota.forEach(function (boto) {
    boto.addEventListener("click", function () {
      const partitId = boto.dataset.partitId;
      const seleccio = boto.dataset.seleccio;
      const quota = boto.dataset.quota;

      // Desmarquem altres botons del mateix partit.
      document
        .querySelectorAll('.botó-quota[data-partit-id="' + partitId + '"]')
        .forEach(function (b) { b.classList.remove("seleccionada"); });
      boto.classList.add("seleccionada");

      // Mostrem el ticket corresponent i hi omplim les dades ocultes.
      const ticket = document.getElementById("ticket-" + partitId);
      if (!ticket) return;

      document.querySelectorAll(".ticket-aposta").forEach(function (t) {
        if (t !== ticket) t.classList.remove("visible");
      });
      ticket.classList.add("visible");
      ticket.querySelector('input[name="seleccio"]').value = seleccio;
      ticket.querySelector(".quota-elegida").textContent = quota;

      const inputImport = ticket.querySelector('input[name="import_apostat"]');
      inputImport.focus();
      actualitzarGuanyPotencial(ticket);
    });
  });

  document.querySelectorAll(".ticket-aposta input[name='import_apostat']").forEach(function (input) {
    input.addEventListener("input", function () {
      actualitzarGuanyPotencial(input.closest(".ticket-aposta"));
    });
  });
});

function actualitzarGuanyPotencial(ticket) {
  const quota = parseFloat(ticket.querySelector(".quota-elegida").textContent) || 0;
  const import_ = parseFloat(ticket.querySelector('input[name="import_apostat"]').value) || 0;
  const resultat = Math.round(quota * import_);
  ticket.querySelector(".guany-potencial").textContent = resultat;
}
