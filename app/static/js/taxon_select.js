/**
 * Taxon name autocomplete (FinBIF /autocomplete/taxa via same-origin proxy).
 *
 *   <div data-taxon-select data-autocomplete-url="...">
 *     …
 *     <input type="hidden" name="taxon_id" value="" />
 *     <ul class="taxon-select__suggestions" hidden></ul>
 *   </div>
 *
 * Optional `data-taxon-id-name` on the root (default `taxon_id`) sets which hidden
 * input receives the selected taxon id — use e.g. `taxon` for GET query param names.
 */
(function () {
  var DEBOUNCE_MS = 300;

  function labelFor(item) {
    var sci = item.scientificName || item.value || item.matchingName || "";
    var vern = item.vernacularName;
    if (vern && sci && vern.toLowerCase() !== sci.toLowerCase()) {
      return sci + " (" + vern + ")";
    }
    return sci || item.matchingName || item.value || item.id;
  }

  function closeList(ul) {
    ul.hidden = true;
    ul.innerHTML = "";
  }

  function init(root) {
    var endpoint =
      root.getAttribute("data-autocomplete-url") || "/api/finbif/autocomplete/taxa";
    var idInputName = root.getAttribute("data-taxon-id-name") || "taxon_id";
    var queryInput = root.querySelector(".taxon-select__query");
    var idInput = root.querySelector('input[name="' + idInputName + '"]');
    var ul = root.querySelector(".taxon-select__suggestions");
    if (!queryInput || !idInput || !ul) return;

    var timer = null;
    var lastController = null;
    var seq = 0;

    function runFetch() {
      timer = null;
      var q = queryInput.value.trim();
      if (lastController) {
        lastController.abort();
        lastController = null;
      }
      if (!q) {
        seq++;
        root.classList.remove("taxon-select--loading");
        closeList(ul);
        return;
      }

      var mySeq = ++seq;
      root.classList.add("taxon-select--loading");
      lastController = new AbortController();
      var params = new URLSearchParams({ query: q });
      fetch(endpoint + "?" + params.toString(), {
        signal: lastController.signal,
        headers: { Accept: "application/json" },
      })
        .then(function (res) {
          if (!res.ok) throw new Error("http");
          return res.json();
        })
        .then(function (data) {
          if (mySeq !== seq) return;
          var results = data.results;
          if (!Array.isArray(results) || results.length === 0) {
            closeList(ul);
            return;
          }
          ul.innerHTML = "";
          results.forEach(function (item) {
            var id = item.id;
            if (!id) return;
            var li = document.createElement("li");
            li.className = "taxon-select__suggestion";
            var btn = document.createElement("button");
            btn.type = "button";
            btn.textContent = labelFor(item);
            btn.addEventListener("click", function () {
              idInput.value = id;
              queryInput.value = labelFor(item);
              closeList(ul);
            });
            li.appendChild(btn);
            ul.appendChild(li);
          });
          ul.hidden = ul.childElementCount === 0;
        })
        .catch(function (err) {
          if (err.name === "AbortError" || mySeq !== seq) return;
          closeList(ul);
        })
        .finally(function () {
          if (mySeq !== seq) return;
          root.classList.remove("taxon-select--loading");
        });
    }

    queryInput.addEventListener("input", function () {
      if (timer) clearTimeout(timer);
      timer = setTimeout(runFetch, DEBOUNCE_MS);
    });

    queryInput.addEventListener("focus", function () {
      if (ul.childElementCount) ul.hidden = false;
    });

    document.addEventListener("click", function (ev) {
      if (!root.contains(ev.target)) closeList(ul);
    });
  }

  document.querySelectorAll("[data-taxon-select]").forEach(init);
})();
