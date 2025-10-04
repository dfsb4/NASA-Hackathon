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

export default function WeatherLensMap() {
  const [coords, setCoords] = useState({ lat: null, lon: null });
  const mapRef = useRef();
  // Larger projection so the map appears bigger inside the container.
  // translate values approximate the center for a 800x600 viewport used below.
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

  return (
    <div
      ref={mapRef}
      onMouseMove={handleMouseMove}
      // increase the height so the map + outer box are larger; responsive sizes
      className="relative w-full h-[500px] sm:h-[600px] md:h-[700px] bg-gradient-to-r from-gray-700 to-gray-600 rounded-2xl p-4 overflow-hidden"
    >
      <h2 className="text-white text-2xl mb-2 font-semibold">Location</h2>

      <ComposableMap
        // use the d3 projection (bigger scale above) and make the svg fill the
        // container so the visual area is larger
        projection={projection}
        width={800}
        height={600}
        style={{ width: "100%", height: "100%" }}
        // Use 'slice' so the SVG scales to fill the container and any overflow
        // is cropped; this ensures only the center of the map is shown.
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
      <button className="absolute bottom-3 right-4 bg-blue-800 hover:bg-blue-600 text-white px-6 py-2 rounded-full font-semibold">
        Predict
      </button>
    </div>
  );
}
