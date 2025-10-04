// src/components/WeatherLensMap.jsx
import React, { useState, useRef } from "react";
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
  const mapRef = useRef();

  const projection = d3.geoMercator().scale(200).translate([400, 300]);

  const handleMouseMove = (event) => {
    const rect = mapRef.current.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const inverted = projection.invert([x, y]);
    if (inverted) {
      const [lon, lat] = inverted;
      setCoords({ lat: lat.toFixed(3), lon: lon.toFixed(3) });
    }
  };

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
      ref={mapRef}
      onMouseMove={handleMouseMove}
      className="relative w-full h-[500px] sm:h-[600px] md:h-[700px] bg-gradient-to-r from-gray-700 to-gray-600 rounded-2xl p-4 overflow-hidden"
    >
      <h2 className="text-white text-2xl mb-2 font-semibold">Location</h2>

      <ComposableMap
        projection={projection}
        width={800}
        height={600}
        style={{ width: "100%", height: "100%" }}
        preserveAspectRatio="xMidYMid slice"
      >
        <ZoomableGroup zoom={1}>
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
                    hover: { fill: "#4E7", transition: "0.3s" },
                  }}
                />
              ))
            }
          </Geographies>
        </ZoomableGroup>
      </ComposableMap>

      <div className="absolute bottom-3 left-4 text-white text-sm">
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
