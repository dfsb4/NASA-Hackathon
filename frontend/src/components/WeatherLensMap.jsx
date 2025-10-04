// src/components/WeatherLensMap.jsx
import React, { useState, useRef, useEffect } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
} from "react-simple-maps";
import * as d3 from "d3-geo";

const geoUrl =
  "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";
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

  // Pointer drag start refs
  const startPointerViewRef = useRef({ x: 0, y: 0 }); // viewBox coords at pointer start
  const startRotationRef = useRef(0);
  const startPanYRef = useRef(0);

  // Map intrinsic viewBox size (matches ComposableMap width/height)
  const VB_W = 800;
  const VB_H = 600;

  // Helper: build a projection for a given rotation (lon)
  const makeProjection = (rotLon = rotationRef.current) =>
    d3.geoMercator().scale(200).translate([VB_W / 2, VB_H / 2]).rotate([rotLon, 0]);

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

  // Compute and set lat/lon for display using the current projection + panY
  const updateCoordsFromClient = (clientX, clientY, rotLon = rotationLon, currentPanY = panY) => {
    if (!containerRef.current) return;
    const view = clientToViewBox(clientX, clientY);
    // Account for vertical translation applied to geographies (panY is in viewBox px)
    const adj = [view.x, view.y - currentPanY];
    const proj = makeProjection(rotLon);
    const inverted = proj.invert(adj);
    if (inverted) {
      const [lon, lat] = inverted;
      setCoords({ lat: lat.toFixed(3), lon: lon.toFixed(3) });
    }
  };

  // Pointer handlers implement dragging: horizontal -> rotation, vertical -> panY
  const onPointerDown = (e) => {
    if (!containerRef.current) return;
    containerRef.current.setPointerCapture(e.pointerId);
    draggingRef.current = true;
    const v = clientToViewBox(e.clientX, e.clientY);
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
      // drag right -> world should move left: subtract delta from start rotation
      const newRotation = startRotationRef.current - deltaLon;
      rotationRef.current = newRotation;
      setRotationLon(newRotation);
    }

    // Vertical pan: difference in viewBox y since start
    const dy = v.y - startPointerViewRef.current.y;
    const newPan = startPanYRef.current + dy;
    // clamp to avoid revealing background; tweak limits as needed
    const clamped = Math.max(Math.min(newPan, 200), -200);
    panYRef.current = clamped;
    setPanY(clamped);

    // Update the coordinate display using the freshly-updated rotation and pan
    updateCoordsFromClient(e.clientX, e.clientY, rotationRef.current, clamped);
  };

  const onPointerUp = (e) => {
    if (!containerRef.current) return;
    try {
      containerRef.current.releasePointerCapture(e.pointerId);
    } catch (err) {}
    draggingRef.current = false;
    containerRef.current.style.cursor = "grab";
  };

  useEffect(() => {
    // ensure cursor is grab by default
    if (containerRef.current) containerRef.current.style.cursor = "grab";
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
    <div
      ref={containerRef}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      className="relative w-full h-[500px] sm:h-[600px] md:h-[700px] bg-gradient-to-r from-gray-700 to-gray-600 rounded-2xl p-0 overflow-hidden"
      style={{ touchAction: "none" }}
    >
      {/* Overlaid label in the top-left of the map (inside the relative container). */}
      <h2 className="absolute top-4 left-4 z-20 text-white text-2xl font-semibold bg-black/30 px-3 py-1 rounded pointer-events-none" style={{fontFamily: '"DM Serif Display", serif', fontWeight: '400', fontStyle: 'normal', display: "inline", color: "var(--nasa-muted)", fontSize: "24px", letterSpacing: '0.15em'}}>
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
          <rect x={0} y={0} width={VB_W} height={VB_H} fill="#111" />
          <g transform={`translate(0, ${panY})`}>
            <Geographies geography={geoUrl}>
              {({ geographies }) =>
                geographies.map((geo) => (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill="#444"
                    stroke="#777"
                    style={{
                      default: { outline: "none" },
                      hover: { fill: "var(--nasa-muted)", transition: "0.3s" },
                    }}
                  />
                ))
              }
            </Geographies>
          </g>
        </g>
      </ComposableMap>

      <div className="absolute bottom-3 left-4 text-white text-sm" style={{fontFamily: '"Bitter", serif', fontWeight: '700', fontSize: '24px', padding: '10px', letterSpacing: '0.15em'}}>
        Lon: {coords.lon || "--"}°E, Lat: {coords.lat || "--"}°N
      </div>

      <div className="absolute bottom-3 right-4 flex items-center gap-3 max-w-[60%]">
        {testResp !== "" && (
          <pre className="text-white/90 text-xs bg-black/40 px-3 py-2 rounded-lg whitespace-pre-wrap break-all">
            {testResp}
          </pre>
        )}

        <button
          onClick={handleTest}
          disabled={testing}
          className="bg-stone-800 hover:bg-stone-600 disabled:opacity-60 disabled:cursor-not-allowed text-white px-5 py-2 rounded-full font-semibold"
        >
          {testing ? "Testing..." : "Test"}
        </button>

        <button className="bg-blue-800 hover:bg-blue-600 text-white px-6 py-2 rounded-full font-semibold">
          Predict
        </button>

      </div>
    </div>
  );
}
