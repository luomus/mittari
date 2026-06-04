/**
 * Intercept form submit: build URL from a template and navigate (full page).
 *
 * Use on forms where the taxon id must be substituted into a path, e.g.
 * `/stats/observers/taxa/_TAXON_/2020`.
 *
 *   <form
 *     method="get"
 *     action="#"
 *     data-taxon-submit-url-template="/stats/observers/taxa/_TAXON_"
 *     data-taxon-id-field="taxon_id"
 *     data-taxon-append-path-selector="#year-select"
 *   >
 *     … taxon autocomplete + optional extra control …
 *     <button type="submit">Siirry</button>
 *   </form>
 *
 * Attributes (all on `<form>`):
 *   - data-taxon-submit-url-template (required): URL string containing literal `_TAXON_`
 *   - data-taxon-id-field (optional): name of hidden input holding taxon id (default `taxon_id`)
 *   - data-taxon-append-path-selector (optional): form.querySelector; if element has a
 *     non-empty `.value`, it is appended as `"/" + value` after template substitution
 */
(function () {
  document.querySelectorAll("form[data-taxon-submit-url-template]").forEach(function (form) {
    var template = form.getAttribute("data-taxon-submit-url-template");
    if (!template) return;

    var idField = form.getAttribute("data-taxon-id-field") || "taxon_id";
    var appendSel = form.getAttribute("data-taxon-append-path-selector");

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var idInput = form.querySelector('input[name="' + idField + '"]');
      var id = idInput && idInput.value.trim();
      if (!id) return;

      var href = template.replace("_TAXON_", id);

      if (appendSel) {
        var el = form.querySelector(appendSel);
        var extra = el && el.value != null && String(el.value).trim();
        if (extra) href = href + "/" + extra;
      }

      var submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Ladataan…";
      }
      form.setAttribute("aria-busy", "true");
      window.location.href = href;
    });
  });
})();
