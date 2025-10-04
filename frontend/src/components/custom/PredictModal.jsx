import React, { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'https://nasa-hackathon-3dwe.onrender.com'

function simulateForecast(lat, lon, datetime) {
  // produce 8 hourly steps of mock precipitation (mm/h)
  const base = (Math.abs(lat) + Math.abs(lon)) % 10
  const start = datetime ? new Date(datetime) : new Date()
  const hours = []
  for (let i = 0; i < 8; i++) {
    const t = new Date(start.getTime() + i * 3600 * 1000)
    // mock precipitation pattern using a pseudo-random deterministic function
    const seed = Math.sin((lat + lon + i) * 0.12345)
    const precip = Math.max(0, Math.round(((seed + 1) * 5 + (base % 3)) * 10) / 10) // 0-~20mm
    hours.push({ time: t.toISOString(), precip })
  }
  const total = hours.reduce((s, h) => s + h.precip, 0)
  const summary = total > 20 ? 'Heavy precipitation expected' : total > 5 ? 'Moderate rain expected' : 'Light or no rain expected'
  return { hours, total: Math.round(total * 10) / 10, summary }
}

export default function PredictModal({ isOpen, onClose, pin, datetime }) {
  const [loading, setLoading] = useState(false)
  const [forecast, setForecast] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!isOpen) return
    setLoading(true)
    setError(null)
    setForecast(null)

    // attempt to call backend predict API; fall back to simulated data on failure
    const doFetch = async () => {
      try {
        const resp = await fetch(`${API_BASE}/predict`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lat: pin?.lat, lon: pin?.lon, datetime }),
        })
        if (!resp.ok) throw new Error(`server ${resp.status}`)
        const json = await resp.json()
        setForecast(json)
      } catch (e) {
        // fallback to simulated forecast
        const lat = pin?.lat ?? 0
        const lon = pin?.lon ?? 0
        const sim = simulateForecast(lat, lon, datetime)
        // small delay to simulate network
        setTimeout(() => {
          setForecast(sim)
          setLoading(false)
        }, 600)
        return
      }
      setLoading(false)
    }

    doFetch()
  }, [isOpen, pin, datetime])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-60 flex items-center justify-center">
      <div onClick={onClose} className="absolute inset-0 bg-black/60"></div>
      <div className="relative w-11/12 max-w-3xl bg-[#071122] rounded-2xl p-6 text-white" style={{ boxShadow: '0 10px 40px rgba(0,0,0,0.6)' }}>
        <div className="flex items-center justify-between mb-4">
          <div className="text-lg font-semibold">Predict Weather</div>
          <div className="flex items-center gap-2">
            <button onClick={onClose} className="text-sm text-nasa-muted px-3 py-1 rounded">Close</button>
          </div>
        </div>

        {!pin && (
          <div className="p-4 bg-red-900 rounded">Please place a pin on the map before predicting.</div>
        )}

        {loading && <div className="py-8">Loading forecast…</div>}

        {error && <div className="p-3 bg-red-900 rounded">{String(error)}</div>}

        {forecast && (
          <div>
            <div className="mb-3 text-sm text-nasa-muted">Location: {pin ? `${pin.lat.toFixed(3)}, ${pin.lon.toFixed(3)}` : '—'}</div>
            <div className="mb-6 font-semibold">Summary: {forecast.summary} — total {forecast.total} mm</div>

            <div className="w-full h-36 bg-black/20 rounded p-3 flex items-end gap-2">
              {/* simple bar chart for hourly precipitation */}
              {forecast.hours.map((h, i) => {
                const max = Math.max(...forecast.hours.map((x) => x.precip), 1)
                const height = Math.round((h.precip / max) * 100)
                const label = new Date(h.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                return (
                  <div key={i} className="flex flex-col items-center" style={{ width: '10%' }}>
                    <div style={{ height: `${height}%`, width: '100%', background: 'linear-gradient(180deg,#60a5fa,#0ea5e9)', borderRadius: 4 }} title={`${h.precip} mm`} />
                    <div className="text-xs text-nasa-muted mt-1">{label}</div>
                  </div>
                )
              })}
            </div>

            <div className="mt-4 text-sm text-nasa-muted">This forecast is simulated when the backend is unavailable.</div>
          </div>
        )}
      </div>
    </div>
  )
}
