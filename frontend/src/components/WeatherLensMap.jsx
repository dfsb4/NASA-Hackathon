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
