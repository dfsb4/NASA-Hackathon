// src/components/WeatherLensMap.jsx
import React, { useState, useRef, useEffect } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
} from "react-simple-maps";
import * as d3 from "d3-geo";
import PredictModal from "./custom/PredictModal";

const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";
const API_BASE =
  import.meta.env.VITE_API_URL || "https://nasa-hackathon-3dwe.onrender.com";

export default function WeatherLensMap() {
  const [coords, setCoords] = useState({ lat: null, lon: null });
  const [testing, setTesting] = useState(false);
  const [testResp, setTestResp] = useState("");
  const containerRef = useRef(null);

  // Interaction state
  const rotationRef = useRef(0); // degrees (lon) applied to projection
  const [rotationLon, setRotationLon] = useState(0);
  const panYRef = useRef(0); // vertical translate in viewBox pixels
  const [panY, setPanY] = useState(0);
  const draggingRef = useRef(false);
  const geographiesRef = useRef(null);
  const [country, setCountry] = useState(null);
  const [predictOpen, setPredictOpen] = useState(false);
  const [apiError, setApiError] = useState(null);
  const pointerDownRef = useRef(null);
  const [pin, setPin] = useState(null);
  const [zoom, setZoom] = useState(1);

  // Search state (query + loading)
  const [searchQ, setSearchQ] = useState("");
  const [searching, setSearching] = useState(false);

  // Pointer drag start refs
  const startPointerViewRef = useRef({ x: 0, y: 0 }); // viewBox coords at pointer start
  const startRotationRef = useRef(0);
  const startPanYRef = useRef(0);

  // Map intrinsic viewBox size (matches ComposableMap width/height)
  const VB_W = 800;
  const VB_H = 600;

  // Helper: build a projection for a given rotation (lon)
  const makeProjection = (rotLon = rotationRef.current) =>
    d3
      .geoMercator()
      .scale(200 * zoom)
      .translate([VB_W / 2, VB_H / 2])
      .rotate([rotLon, 0]);

  // Convert client (event.clientX/Y) to SVG viewBox coordinates, honoring
  // preserveAspectRatio="xMidYMid slice" behavior.
  const clientToViewBox = (clientX, clientY) => {
    const rect = containerRef.current.getBoundingClientRect();
    const scale = Math.max(rect.width / VB_W, rect.height / VB_H); // 'slice' uses max
    const scaledW = VB_W * scale;
    const scaledH = VB_H * scale;
    const offsetX = (rect.width - scaledW) / 2;
    const offsetY = (rect.height - scaledH) / 2;
    const x = (clientX - rect.left - offsetX) / scale;
    const y = (clientY - rect.top - offsetY) / scale;
    return { x, y };
  };

  // Coordinate formatting helpers
  const fmtLat = (lat) => {
    if (lat === null || lat === undefined || Number.isNaN(lat)) return "--";
    const abs = Math.abs(Number(lat));
    const dir = lat >= 0 ? "N" : "S";
    return `${abs.toFixed(3)}°${dir}`;
  };
  const fmtLon = (lon) => {
    if (lon === null || lon === undefined || Number.isNaN(lon)) return "--";
    const abs = Math.abs(Number(lon));
    const dir = lon >= 0 ? "E" : "W";
    return `${abs.toFixed(3)}°${dir}`;
  };

  // Compute and set lat/lon for display using the current projection + panY
  const updateCoordsFromClient = (
    clientX,
    clientY,
    rotLon = rotationLon,
    currentPanY = panY
  ) => {
    if (!containerRef.current) return;
    const view = clientToViewBox(clientX, clientY);
    // Account for vertical translation applied to geographies (panY is in viewBox px)
    const adj = [view.x, view.y - currentPanY];
    const proj = makeProjection(rotLon);
    const inverted = proj.invert(adj);
    if (inverted) {
      const [lon, lat] = inverted;
      // store numeric coords for later formatting
      setCoords({ lat, lon });
      // look up country name (if geographies loaded)
      findCountryFromLonLat(lon, lat);
    }
  };

  const findCountryFromLonLat = (lon, lat) => {
    try {
      if (!geographiesRef.current) {
        setCountry(null);
        return;
      }
      for (const geo of geographiesRef.current) {
        // geo is a GeoJSON feature produced by react-simple-maps
        if (d3.geoContains(geo, [lon, lat])) {
          const name =
            geo.properties.ADMIN ||
            geo.properties.name ||
            geo.properties.NAME ||
            geo.properties.NAME_LONG ||
            geo.properties.SOVEREIGNT ||
            null;
          setCountry(name || null);
          return;
        }
      }
      setCountry(null);
    } catch (e) {
      setCountry(null);
    }
  };

  // Pointer handlers implement dragging: horizontal -> rotation, vertical -> panY
  const onPointerDown = (e) => {
    if (!containerRef.current) return;
    containerRef.current.setPointerCapture(e.pointerId);
    draggingRef.current = true;
    const v = clientToViewBox(e.clientX, e.clientY);
    // record raw client down for click detection
    pointerDownRef.current = { x: e.clientX, y: e.clientY, t: Date.now() };
    startPointerViewRef.current = { x: v.x, y: v.y };
    startRotationRef.current = rotationRef.current;
    startPanYRef.current = panYRef.current;
    // compute starting lon using a projection frozen at the start rotation
    const proj = makeProjection(startRotationRef.current);
    const startAdj = [v.x, v.y - startPanYRef.current];
    const inv = proj.invert(startAdj);
    startPointerViewRef.current.startLon = inv ? inv[0] : null;
    // UX
    containerRef.current.style.cursor = "grabbing";
  };

  const onPointerMove = (e) => {
    if (!containerRef.current) return;
    const v = clientToViewBox(e.clientX, e.clientY);
    if (!draggingRef.current) {
      // just update coords preview
      updateCoordsFromClient(e.clientX, e.clientY);
      return;
    }

    // Horizontal rotation: compute lon at current pointer in the *start* projection,
    // then compute delta against the start lon and apply to rotation.
    const projAtStart = makeProjection(startRotationRef.current);
    const curAdj = [v.x, v.y - startPanYRef.current];
    const curInv = projAtStart.invert(curAdj);
    const startLon = startPointerViewRef.current.startLon;
    if (curInv && startLon !== null && startLon !== undefined) {
      const curLon = curInv[0];
      const deltaLon = curLon - startLon;
      // flip horizontal drag: drag right -> world should move right (match pointer)
      const newRotation = startRotationRef.current + deltaLon;
      rotationRef.current = newRotation;
      setRotationLon(newRotation);
    }

    // Vertical pan: difference in viewBox y since start
    // const dy = v.y - startPointerViewRef.current.y;
    // const newPan = startPanYRef.current + dy;
    // // clamp to avoid revealing background; tweak limits as needed
    // const clamped = Math.max(Math.min(newPan, 200), -200);
    // panYRef.current = clamped;
    // setPanY(clamped);

    // Vertical pan: difference in viewBox y since start
// Vertical pan: difference in viewBox y since start
const dy = v.y - startPointerViewRef.current.y;
const newPan = startPanYRef.current + dy;
// 移除 clamp：直接無限累積，像 rotationLon
panYRef.current = newPan;
setPanY(newPan);

    // Update the coordinate display using the freshly-updated rotation and pan
    updateCoordsFromClient(e.clientX, e.clientY, rotationRef.current, clamped);
  };

  const onPointerUp = (e) => {
    if (!containerRef.current) return;
    try {
      containerRef.current.releasePointerCapture(e.pointerId);
    } catch (err) {}
    // determine if this was a click (small movement and short time)
    const down = pointerDownRef.current;
    const up = { x: e.clientX, y: e.clientY, t: Date.now() };
    let isClick = false;
    if (down) {
      const dx = up.x - down.x;
      const dy = up.y - down.y;
      const dist = Math.hypot(dx, dy);
      const dt = up.t - down.t;
      if (dist < 6 && dt < 300) isClick = true;
    }

    if (isClick) {
      // map client -> viewBox -> lon/lat (account for panY)
      const view = clientToViewBox(e.clientX, e.clientY);
      const proj = makeProjection(rotationRef.current);
      const adj = [view.x, view.y - panYRef.current];
      const inv = proj.invert(adj);
      if (inv) {
        const [lon, lat] = inv;
        // replace existing pin with the new one (only one pin at a time)
        setPin({ lon, lat });
        // also update coords and country
        setCoords({ lat: lat.toFixed(3), lon: lon.toFixed(3) });
        findCountryFromLonLat(lon, lat);
      }
    }

    draggingRef.current = false;
    containerRef.current.style.cursor = "grab";
  };

  useEffect(() => {
    // ensure cursor is grab by default
    if (containerRef.current) containerRef.current.style.cursor = "grab";
  }, []);

  // Make map fill remaining viewport below header
  const [containerHeightPx, setContainerHeightPx] = useState(null);
  useEffect(() => {
    const resize = () => {
      const header = document.getElementById("site-header");
      const headerH = header ? header.getBoundingClientRect().height : 0;
      const h = Math.max(window.innerHeight - headerH, 200);
      setContainerHeightPx(h);
    };
    resize();
    window.addEventListener("resize", resize);
    // also observe header size in case it changes dynamically
    const headerEl = document.getElementById("site-header");
    let ro;
    if (headerEl && typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(resize);
      ro.observe(headerEl);
    }
    return () => {
      window.removeEventListener("resize", resize);
      if (ro && headerEl) ro.unobserve(headerEl);
    };
  }, []);

  const handleTest = async () => {
    setTesting(true);
    try {
      const res = await fetch(`${API_BASE}/api/health`, { method: "GET" });
      const text = await res.text();
      setTestResp(`${res.status} ${res.statusText}\n${text}`);
    } catch (e) {
      setTestResp(String(e));
    } finally {
      setTesting(false);
    }
  };

  // Minimal Nominatim forward geocoding (OpenStreetMap)
  async function geocodeNominatim(query) {
    const url = new URL("https://nominatim.openstreetmap.org/search");
    url.searchParams.set("q", query);
    url.searchParams.set("format", "json");
    url.searchParams.set("limit", "1");
    url.searchParams.set("addressdetails", "0");
    url.searchParams.set("accept-language", "zh-TW"); // 讓回傳偏中文

    const res = await fetch(url.toString(), { method: "GET" });
    if (!res.ok) throw new Error("Nominatim HTTP error " + res.status);
    const arr = await res.json();
    if (!Array.isArray(arr) || arr.length === 0) return null;

    const first = arr[0];
    return {
      lat: parseFloat(first.lat),
      lon: parseFloat(first.lon),
      name: first.display_name,
    };
  }

  const handleSearch = async () => {
    const q = searchQ.trim();
    if (!q) return;
    setSearching(true);
    setApiError(null);
    try {
      // 先試著把輸入解析成經緯度
      const parsed = parseLatLon(q);
      if (parsed) {
        const { lat, lon } = parsed;
        setPin({ lon, lat });
        setCoords({ lat, lon });
        findCountryFromLonLat(lon, lat);

        // （可選）視角置中：讓該經度到中線，並把該點移到視窗中央
        const newRot = -lon;
        rotationRef.current = newRot;
        setRotationLon(newRot);
        const proj = makeProjection(newRot);
        const pt = proj([lon, lat]);
        if (pt) {
          const deltaY = (VB_H / 2) - pt[1];
          panYRef.current = panYRef.current + deltaY;
          setPanY(panYRef.current);
        }
        return; // 解析成功就不去打 OSM 了
      }

      // 經緯度解析失敗 -> 改用 Nominatim 關鍵字搜尋
      const r = await geocodeNominatim(q);
      if (!r) {
        setApiError("No result for that location");
        return;
      }
      setPin({ lon: r.lon, lat: r.lat });
      setCoords({ lat: r.lat, lon: r.lon });
      findCountryFromLonLat(r.lon, r.lat);

      const newRot = -r.lon;
      rotationRef.current = newRot;
      setRotationLon(newRot);
      const proj = makeProjection(newRot);
      const pt = proj([r.lon, r.lat]);
      if (pt) {
        const deltaY = (VB_H / 2) - pt[1];
        panYRef.current = panYRef.current + deltaY;
        setPanY(panYRef.current);
      }
    } catch (e) {
      setApiError("Geocode error: " + e.message);
    } finally {
      setSearching(false);
    }
  };


  // Enter 直接搜尋
  const onSearchKeyDown = (e) => {
    if (e.key === "Enter") handleSearch();
  };


  // 支援的格式（大小寫皆可、空白/逗號可混用）：
  // "25.033, 121.565"、"121.565 25.033"、"N25.033 E121.565"、"25.033N, 121.565E"
  // "lat=25.033 lon=121.565"、"經度121.565 緯度25.033"（只要抓到數字與NSEW就行）
  // 也接受中文全形逗號（，）
  function parseLatLon(raw) {
    if (!raw) return null;
    let s = String(raw).trim();
    s = s.replace(/，/g, ","); // 全形逗號 -> 半形
    // 移除多餘字元，保留數字/小數點/符號/字母NSEW與分隔
    // 只是為了好切割，不是嚴格清洗
    const cleaned = s.replace(/[^\d\.\-\+\s,°NSEWnsew]/g, " ");

    // 1) 嘗試 label 風格（lat=.. lon=..）
    const latLabel = /lat(?:itude)?\s*[:=]?\s*([+\-]?\d+(?:\.\d+)?)/i.exec(cleaned);
    const lonLabel = /lon(?:gitude)?\s*[:=]?\s*([+\-]?\d+(?:\.\d+)?)/i.exec(cleaned);
    if (latLabel && lonLabel) {
      const lat = parseFloat(latLabel[1]);
      const lon = parseFloat(lonLabel[1]);
      if (Number.isFinite(lat) && Number.isFinite(lon) && inRange(lat, lon)) {
        return { lat, lon };
      }
    }

    // 2) 抓出帶 NSEW 的兩個數
    // 形式如："25.033N 121.565E" 或 "N25.033, E121.565"
    const tokenRe = /([NnSsEeWw])?\s*([+\-]?\d+(?:\.\d+)?)\s*([NnSsEeWw])?/g;
    let tokens = [];
    let m;
    while ((m = tokenRe.exec(cleaned))) {
      const val = parseFloat(m[2]);
      if (!Number.isFinite(val)) continue;
      const prefix = m[1] || "";
      const suffix = m[3] || "";
      const dir = (prefix + suffix).toUpperCase(); // 可能是 "N"、"S"、"E"、"W" 或 ""
      tokens.push({ val, dir });
    }
    if (tokens.length >= 2) {
      const a = tokens[0], b = tokens[1];
      // 如果其中一個包含 N/S -> 當作緯度；另一個包含 E/W -> 當作經度
      const hasNS = (t) => /[NS]/.test(t.dir);
      const hasEW = (t) => /[EW]/.test(t.dir);
      let lat, lon;

      if (hasNS(a) && hasEW(b)) {
        lat = a.val * (a.dir === "S" ? -1 : 1);
        lon = b.val * (b.dir === "W" ? -1 : 1);
      } else if (hasNS(b) && hasEW(a)) {
        lat = b.val * (b.dir === "S" ? -1 : 1);
        lon = a.val * (a.dir === "W" ? -1 : 1);
      } else if (hasNS(a) || hasNS(b)) {
        // 只有一個有 NS，另一個沒標，則無標者視為經度（常見：25N 121.5）
        const tLat = hasNS(a) ? a : b;
        const tLon = hasNS(a) ? b : a;
        lat = tLat.val * (tLat.dir === "S" ? -1 : 1);
        lon = tLon.val; // 未指定方向，保留正負號
      } else if (hasEW(a) || hasEW(b)) {
        // 只有一個有 EW，另一個視為緯度
        const tLon = hasEW(a) ? a : b;
        const tLat = hasEW(a) ? b : a;
        lat = tLat.val;
        lon = tLon.val * (tLon.dir === "W" ? -1 : 1);
      } else {
        // 都沒有方向：用「常見順序」猜測：第一個為緯度(-90..90)，第二個為經度(-180..180)
        // 若第一個不在緯度範圍、第二個在，則互換
        let v1 = a.val, v2 = b.val;
        if (Math.abs(v1) <= 90 && Math.abs(v2) <= 180) {
          lat = v1; lon = v2;
        } else if (Math.abs(v2) <= 90 && Math.abs(v1) <= 180) {
          lat = v2; lon = v1;
        }
      }

      if (Number.isFinite(lat) && Number.isFinite(lon) && inRange(lat, lon)) {
        return { lat, lon };
      }
    }

    // 3) 簡單逗號/空白分隔兩數（不帶方向）
    const parts = cleaned.split(/[,\s]+/).filter(Boolean);
    if (parts.length >= 2) {
      const a = parseFloat(parts[0]);
      const b = parseFloat(parts[1]);
      if (Number.isFinite(a) && Number.isFinite(b)) {
        // 試兩種順序（lat,lon）或（lon,lat）
        if (inRange(a, b)) return { lat: a, lon: b };
        if (inRange(b, a)) return { lat: b, lon: a };
      }
    }

    return null;

    function inRange(lat, lon) {
      return Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
    }
  }


  return (
    <div>
      <div
        ref={containerRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onWheel={(e) => {
          e.preventDefault(); 
          const factor = e.deltaY < 0 ? 1.2 : 0.8; 
          setZoom((prev) => {
            const newZoom = prev * factor;
            return Math.max(1, Math.min(newZoom, 8)); 
          });
        }}
        className={`relative to-gray-600 rounded-none p-0 overflow-hidden ${
          predictOpen ? "pointer-events-none" : ""
        }`}
        style={{
          touchAction: "none",
          height: containerHeightPx ? `${containerHeightPx}px` : "80vh",
          width: "100vw",
        }}
      >
        {/* Overlaid label in the top-left of the map (inside the relative container). */}
        <h2
          className="absolute top-4 left-4 z-20 text-white text-2xl font-semibold bg-black/30 px-3 py-1 rounded pointer-events-none"
          style={{
            fontFamily: '"DM Serif Display", serif',
            fontWeight: "400",
            fontStyle: "normal",
            display: "inline",
            color: "var(--nasa-muted)",
            fontSize: "24px",
            letterSpacing: "0.15em",
          }}
        >
          LOCATION
        </h2>

        <ComposableMap
          projection={makeProjection(rotationLon)}
          width={VB_W}
          height={VB_H}
          style={{ width: "100%", height: "100%" }}
          preserveAspectRatio="xMidYMid slice"
        >
          {/* draw a background rect so when the geographies are translated we don't reveal the container bg */}
          <g>
            <defs>
              <linearGradient id="mapBg" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#cbc8c8ff" />
                <stop offset="50%" stopColor="#cbc8c8ff" />
                <stop offset="100%" stopColor="#cbc8c8ff" />
              </linearGradient>
            </defs>
            <rect x={0} y={0} width={VB_W} height={VB_H} fill="url(#mapBg)" />
            <g transform={`translate(0, ${panY})`}>
              <Geographies geography={geoUrl}>
                {({ geographies }) => {
                  // store geographies for country lookup later
                  geographiesRef.current = geographies;
                  return geographies.map((geo) => (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      fill="#f1efefff"
                      stroke="#939292ff"
                      tabIndex={-1}
                      focusable={false}
                      style={{
                        default: { outline: "none" },
                        hover: {
                          fill: "var(--nasa-muted)",
                          transition: "0.3s",
                        },
                      }}
                    />
                  ));
                }}
              </Geographies>
              {/* Continent labels (projected). All labels share the `region-label` class so styles live in index.css */}
              {(() => {
                try {
                  const proj = makeProjection(rotationLon);
                  const regions = [
                    { name: "NORTH AMERICA", lon: -100, lat: 35 },
                    { name: "SOUTH AMERICA", lon: -58, lat: -10 },
                    { name: "EUROPE", lon: 20, lat: 50 },
                    { name: "AFRICA", lon: 27, lat: 0 },
                    { name: "ASIA", lon: 90, lat: 46.5 },
                    { name: "OCEANIA", lon: 133.5, lat: -28 },
                  ];
                  return regions.map((r) => {
                    const pt = proj([r.lon, r.lat]);
                    if (!pt) return null;
                    return (
                      <text
                        key={r.name}
                        className="region-label"
                        x={pt[0]}
                        y={pt[1]}
                        textAnchor="middle"
                        style={{
                          pointerEvents: "none",
                          fill: "var(--nasa-emerald)",
                        }}
                      >
                        {r.name}
                      </text>
                    );
                  });
                } catch (e) {
                  return null;
                }
              })()}
              {/* single pin rendered in same transformed group so it moves with the map */}
              {pin &&
                (() => {
                  try {
                    const proj = makeProjection(rotationLon);
                    const pt = proj([pin.lon, pin.lat]);
                    if (!pt) return null;
                    // center the pin image (assume 28x28)
                    const size = 28;
                    return (
                      <g
                        key={`pin`}
                        transform={`translate(${pt[0] - size / 2}, ${
                          pt[1] - size
                        })`}
                        style={{ pointerEvents: "none" }}
                      >
                        {/* Inline pin SVG so we can style the fill using CSS variables (supports --nasa--emulate with fallback) */}
                        <svg
                          width={size}
                          height={size}
                          viewBox="0 0 28 28"
                          xmlns="http://www.w3.org/2000/svg"
                          style={{ overflow: "visible" }}
                        >
                          <path
                            d="M14 0C9.029 0 5 4.03 5 9.01 5 16.01 14 28 14 28s9-11.99 9-18.99C23 4.03 18.971 0 14 0z"
                            fill="var(--nasa-emerald)"
                          />
                          <circle cx="14" cy="9" r="3.5" fill="white" />
                        </svg>

                        {/* place label below the pin SVG (size + offset) and use CSS token for color */}
                        <text
                          x={size / 2}
                          y={size + 12}
                          textAnchor="middle"
                          fontSize={10}
                          fill="var(--nasa-deep)"
                          style={{
                            fontFamily: '"Bitter", serif',
                            fontWeight: 700,
                          }}
                        >
                          {`${fmtLon(pin.lon)} , ${fmtLat(pin.lat)}`}
                        </text>
                      </g>
                    );
                  } catch (e) {
                    return null;
                  }
                })()}
            </g>
          </g>
        </ComposableMap>
        {/* </ZoomableGroup> */}
      </div>

      {/* Footer block */}
      <div className="w-full absolute bottom-0 left-0 p-3 shadow-sm flex flex-col items-center px-5 bg-nasa-dark-gray-azure/90 ring-1 ring-white/10 text-white gap-4">
        {/* Coordinate readout */}
        <div
          className="text-sm absolute bottom-5 left-5"
          style={{
            fontFamily: '"Bitter", serif',
            fontWeight: "700",
            fontSize: "24px",
            letterSpacing: "0.08em",
          }}
        >
          {fmtLon(coords.lon)} , {fmtLat(coords.lat)}
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-3">

          {/* Search box + button */}
          <input
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            onKeyDown={onSearchKeyDown}
            placeholder="Search: 地名 或 經緯度（例：台北101 / 25.033,121.565 / N25.033 E121.565）"
            className="px-3 py-2 rounded-full text-black text-sm w-[40rem]"
            style={{ background: "white" }}
            disabled={searching}
          />
          <button
            onClick={handleSearch}
            disabled={searching || !searchQ.trim()}
            className="px-5 py-3 rounded-full font-semibold"
            style={{
              backgroundColor: "var(--nasa-emerald)",
              color: "white",
              opacity: searching || !searchQ.trim() ? 0.6 : 1,
            }}
          >
            {searching ? "Searching…" : "Search"}
          </button>


          {testResp !== "" && (
            <pre className="text-white/90 text-xs px-3 py-2 rounded-lg whitespace-pre-wrap break-all">
              {testResp}
            </pre>
          )}

          <button
            style={{ backgroundColor: "var(--nasa-deep)" }}
            onClick={() => setPredictOpen(true)}
            className="text-white px-6 py-3 rounded-full font-semibold justify-center"
          >
            Predict
          </button>
        </div>

        {/* Predict modal */}
        <PredictModal
          isOpen={predictOpen}
          onClose={() => setPredictOpen(false)}
          pin={pin}
          datetime={(() => {
            const tEl = document.querySelector("#site-header time");
            if (tEl && tEl.getAttribute("dateTime"))
              return tEl.getAttribute("dateTime");
            return new Date().toISOString();
          })()}
          onApiError={setApiError}
        />

        {/* bottom-right: country name determined from current coords */}
        <div
          className="absolute bottom-5 right-5 text-white text-sm text-right z-20"
          style={{
            fontFamily: '"Bitter", serif',
            fontWeight: "700",
            fontSize: "24px",
            padding: "8px",
            letterSpacing: "0.08em",
          }}
        >
          {country ? country : "—"}
        </div>
        {/* API error banner (shows at very bottom) */}
        {apiError && (
          <div
            className="absolute bottom-0 left-0 w-full text-center py-1 text-sm text-red-300"
            style={{ background: "rgba(255,0,0,0.06)" }}
          >
            API calling error
          </div>
        )}
      </div>
    </div>
  );
}
