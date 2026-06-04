/**
 * Leaflet map: draggable center marker + two WGS84 rectangles matching
 * app.services.miss.bounding_box (km "radius" → axis-aligned lat/lon box).
 *
 * Root: [data-coord-radius-map]
 *   data-lat-input, data-lon-input, data-near-input, data-far-input — CSS selectors
 *   data-initial-zoom (optional, default 8)
 *   data-max-bounds (optional) — "south,west,north,east" WGS84
 *
 * Child: .coord-radius-map__viewport (map container)
 */
(function () {
  var DEBOUNCE_MS = 150;

  function toRadians(deg) {
    return (deg * Math.PI) / 180;
  }

  function toDegrees(rad) {
    return (rad * 180) / Math.PI;
  }

  /**
   * Must match `bounding_box` in app/services/miss.py.
   */
  function boundingBox(lat, lon, boxSizeKm) {
    var R = 6371.0;
    var latRad = toRadians(lat);
    var angularDistance = boxSizeKm / R;
    var latMin = lat - toDegrees(angularDistance);
    var latMax = lat + toDegrees(angularDistance);
    var deltaLon = toDegrees(angularDistance / Math.cos(latRad));
    var lonMin = lon - deltaLon;
    var lonMax = lon + deltaLon;
    return [
      Math.round(latMin * 1e4) / 1e4,
      Math.round(latMax * 1e4) / 1e4,
      Math.round(lonMin * 1e4) / 1e4,
      Math.round(lonMax * 1e4) / 1e4,
    ];
  }

  function parseFloatInput(el) {
    if (!el) return NaN;
    return parseFloat(String(el.value).replace(",", ".").trim());
  }

  function normalizeInnerKm(raw) {
    var s = String(raw == null ? "" : raw).trim();
    if (!s || !/^\d+$/.test(s)) return 10;
    var n = parseInt(s, 10);
    return Math.max(0, Math.min(50, n));
  }

  function normalizeOuterKm(raw) {
    var s = String(raw == null ? "" : raw).trim();
    if (!s || !/^\d+$/.test(s)) return 30;
    var n = parseInt(s, 10);
    return Math.max(0, Math.min(100, n));
  }

  function applyRadiusDefaults(nearInput, farInput) {
    if (nearInput) nearInput.value = String(normalizeInnerKm(nearInput.value));
    if (farInput) farInput.value = String(normalizeOuterKm(farInput.value));
  }

  /** Two decimals — canonical form for GET query (cache key). */
  function roundLatLonForQueryUrl(x) {
    if (typeof x !== "number" || isNaN(x)) return x;
    return Math.round(x * 1e2) / 1e2;
  }

  function applyLatLonQueryParams(latInput, lonInput) {
    if (!latInput || !lonInput) return;
    var lat = parseFloatInput(latInput);
    var lon = parseFloatInput(lonInput);
    if (isNaN(lat) || isNaN(lon)) return;
    latInput.value = String(roundLatLonForQueryUrl(lat));
    lonInput.value = String(roundLatLonForQueryUrl(lon));
  }

  function querySel(root, attr) {
    var sel = root.getAttribute(attr);
    if (!sel) return null;
    try {
      return document.querySelector(sel);
    } catch (e) {
      return null;
    }
  }

  function fixLeafletIcons() {
    if (typeof L === "undefined" || !L.Icon || !L.Icon.Default) return;
    delete L.Icon.Default.prototype._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
      iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
      shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
    });
  }

  function parseMaxBounds(root) {
    var raw = root.getAttribute("data-max-bounds");
    if (!raw || !raw.trim()) return null;
    var parts = raw.split(",").map(function (s) {
      return parseFloat(s.trim());
    });
    if (parts.length !== 4 || parts.some(function (x) { return isNaN(x); })) return null;
    return L.latLngBounds(
      [parts[0], parts[1]],
      [parts[2], parts[3]]
    );
  }

  function init(root) {
    if (typeof L === "undefined") return;

    var viewport = root.querySelector(".coord-radius-map__viewport");
    if (!viewport) return;

    var latInput = querySel(root, "data-lat-input");
    var lonInput = querySel(root, "data-lon-input");
    var nearInput = querySel(root, "data-near-input");
    var farInput = querySel(root, "data-far-input");
    if (!latInput || !lonInput || !nearInput || !farInput) return;

    var hint = root.querySelector(".coord-radius-map__hint");
    var zoom = parseInt(root.getAttribute("data-initial-zoom") || "8", 10);
    if (isNaN(zoom) || zoom < 1) zoom = 8;

    fixLeafletIcons();

    var maxBounds = parseMaxBounds(root);

    var lat0 = parseFloatInput(latInput);
    var lon0 = parseFloatInput(lonInput);
    if (isNaN(lat0) || isNaN(lon0)) {
      lat0 = 60.6267;
      lon0 = 25.2862;
    }

    var map = L.map(viewport, {
      maxBounds: maxBounds || undefined,
      maxBoundsViscosity: maxBounds ? 0.85 : undefined,
    }).setView([lat0, lon0], zoom);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);

    var marker = L.marker([lat0, lon0], { draggable: true }).addTo(map);

    var tiny = 0.02;
    var outerRect = L.rectangle(
      [
        [lat0 - tiny, lon0 - tiny],
        [lat0 + tiny, lon0 + tiny],
      ],
      { color: "#2d6a4f", weight: 2, fillColor: "#2d6a4f", fillOpacity: 0.12 }
    ).addTo(map);

    var innerRect = L.rectangle(
      [
        [lat0 - tiny / 2, lon0 - tiny / 2],
        [lat0 + tiny / 2, lon0 + tiny / 2],
      ],
      { color: "#bc6c25", weight: 2, fillColor: "#fff", fillOpacity: 0.35 }
    ).addTo(map);

    var timer = null;

    function setHint(msg) {
      if (!hint) return;
      if (msg) {
        hint.textContent = msg;
        hint.hidden = false;
      } else {
        hint.textContent = "";
        hint.hidden = true;
      }
    }

    function readRadii() {
      return {
        near: normalizeInnerKm(nearInput.value),
        far: normalizeOuterKm(farInput.value),
      };
    }

    function redraw() {
      var lat = parseFloatInput(latInput);
      var lon = parseFloatInput(lonInput);
      if (isNaN(lat) || isNaN(lon)) {
        setHint("Anna kelvolliset leveys- ja pituusasteet.");
        return;
      }

      var r = readRadii();
      if (r.far <= r.near) {
        setHint("Ulomman säteen (km) pitää olla suurempi kuin sisemmän.");
      } else {
        setHint("");
      }

      var latR = roundLatLonForQueryUrl(lat);
      var lonR = roundLatLonForQueryUrl(lon);

      var outerB = boundingBox(latR, lonR, r.far);
      var innerB = boundingBox(latR, lonR, r.near);

      if (r.far > r.near) {
        outerRect.setBounds([
          [outerB[0], outerB[2]],
          [outerB[1], outerB[3]],
        ]);
        innerRect.setBounds([
          [innerB[0], innerB[2]],
          [innerB[1], innerB[3]],
        ]);
      }

      marker.setLatLng([latR, lonR]);
    }

    function syncMarkerFromInputs() {
      var lat = parseFloatInput(latInput);
      var lon = parseFloatInput(lonInput);
      if (isNaN(lat) || isNaN(lon)) return;
      var latR = roundLatLonForQueryUrl(lat);
      var lonR = roundLatLonForQueryUrl(lon);
      latInput.value = String(latR);
      lonInput.value = String(lonR);
      marker.setLatLng([latR, lonR]);
      redraw();
    }

    function scheduleSyncFromInputs() {
      if (timer) clearTimeout(timer);
      timer = setTimeout(syncMarkerFromInputs, DEBOUNCE_MS);
    }

    marker.on("dragend", function () {
      var ll = marker.getLatLng();
      var latR = roundLatLonForQueryUrl(ll.lat);
      var lonR = roundLatLonForQueryUrl(ll.lng);
      latInput.value = String(latR);
      lonInput.value = String(lonR);
      redraw();
    });

    ["input", "change"].forEach(function (ev) {
      latInput.addEventListener(ev, scheduleSyncFromInputs);
      lonInput.addEventListener(ev, scheduleSyncFromInputs);
      nearInput.addEventListener(ev, redraw);
      farInput.addEventListener(ev, redraw);
    });

    function onRadiusBlur() {
      applyRadiusDefaults(nearInput, farInput);
      redraw();
    }
    nearInput.addEventListener("blur", onRadiusBlur);
    farInput.addEventListener("blur", onRadiusBlur);

    var form = nearInput.closest("form");
    if (form) {
      form.addEventListener(
        "submit",
        function () {
          applyLatLonQueryParams(latInput, lonInput);
          applyRadiusDefaults(nearInput, farInput);
        },
        true
      );
    }

    map.whenReady(function () {
      applyLatLonQueryParams(latInput, lonInput);
      applyRadiusDefaults(nearInput, farInput);
      redraw();
      try {
        var b = outerRect.getBounds();
        if (b.isValid()) {
          map.fitBounds(b, { padding: [18, 18], maxZoom: 12 });
        } else {
          map.setView([lat0, lon0], zoom);
        }
      } catch (e) {
        map.setView([lat0, lon0], zoom);
      }
      setTimeout(function () {
        map.invalidateSize();
      }, 0);
      setTimeout(function () {
        map.invalidateSize();
      }, 350);
    });

    window.addEventListener("resize", function () {
      map.invalidateSize();
    });
  }

  document.querySelectorAll("[data-coord-radius-map]").forEach(init);
})();
