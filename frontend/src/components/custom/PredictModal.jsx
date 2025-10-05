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
  const summary = 'Persistent rainfall is expected throughout the day, with precipitation peaking in the early afternoon. \
Humidity levels will remain high, creating a damp and uncomfortable atmosphere. \
Winds are moderate but may increase near coastal areas as the system strengthens. \
Residents should prepare for occasional thunderstorms and possible flooding in low-lying regions.'
  return { hours, total: Math.round(total * 10) / 10, summary }
}

function simulateModelResults(lat, lon, hours) {
  // derive simple simulated metrics from location + hourly precip
  const avgTemp = 20 + ((lat || 0) % 10) + (Math.sin((lon || 0) * 0.1) * 5)
  const avgHumidity = 50 + (Math.abs((lon || 0) % 20) * 1)
  const avgWind = 3 + (Math.abs((lat || 0) % 5))
  const precipTotal = hours.reduce((s, h) => s + h.precip, 0)
  const airQuality = Math.max(10, Math.round(50 + (Math.abs(lat || 0) % 50)))

  // extreme weather probabilities (simple heuristics)
  const extremes = {
    typhoon_probability: +(Math.max(0, 0.01 * (Math.abs(lon) > 120 ? 1 : 0)) ).toFixed(2),
    heatwave_probability: +(Math.max(0, (avgTemp - 28) / 50)).toFixed(2),
    cold_wave_probability: +(Math.max(0, (5 - avgTemp) / 50)).toFixed(2),
    heavy_rain_probability: +Math.min(1, precipTotal / 30).toFixed(2),
    strong_wind_probability: +Math.min(1, avgWind / 20).toFixed(2),
    thunderstorm_probability: +Math.min(1, (precipTotal / 8)).toFixed(2),
  }

  // comfort probabilities
  const comfort = {
    very_hot: +(Math.max(0, (avgTemp - 30) / 10)).toFixed(2),
    very_cold: +(Math.max(0, (0 - avgTemp) / 10)).toFixed(2),
    very_windy: +(Math.max(0, (avgWind - 12) / 20)).toFixed(2),
    very_wet: +(Math.min(1, avgHumidity / 120)).toFixed(2),
    very_uncomfortable: +(Math.min(1, (avgHumidity/100 + Math.max(0,(avgTemp-28)/10)) / 2)).toFixed(2),
  }

  // description summarizing the most relevant bits
  const highExt = Object.entries(extremes).sort((a,b)=>b[1]-a[1]).filter(([k,v])=>v>0.07).map(([k,v])=>`${k.replace(/_/g,' ')} ${Math.round(v*100)}%`)
  const highComfort = Object.entries(comfort).sort((a,b)=>b[1]-a[1]).filter(([k,v])=>v>0.07).map(([k,v])=>`${k.replace(/_/g,' ')} ${Math.round(v*100)}%`)
  let description = `Forecast: ${hours.length} hourly steps, total precip ${precipTotal} mm. `
  if (highExt.length) description += `Notable extremes: ${highExt.join(', ')}. `
  if (highComfort.length) description += `Comfort concerns: ${highComfort.join(', ')}.`

  return {
    metrics: {
      temperature: +(avgTemp.toFixed(1)),
      precipitation: +(precipTotal.toFixed(1)),
      humidity: +(avgHumidity.toFixed(0)),
      windspeed: +(avgWind.toFixed(1)),
      air_quality: airQuality,
    },
    extremes,
    comfort,
    description,
  }
}

export default function PredictModal({ isOpen, onClose, pin, datetime }) {
  const [loading, setLoading] = useState(false)
  const [forecast, setForecast] = useState(null)
  const [error, setError] = useState(null)
  const [model, setModel] = useState(null)

  // helper to map metric keys to units
  const unitForMetric = (k) => {
    switch (k) {
      case 'temperature': return '°C'
      case 'precipitation': return 'mm'
      case 'humidity': return '%'
      case 'windspeed': return 'm/s'
      case 'air_quality': return 'AQI'
      default: return ''
    }
  }

  const prettyProbLabel = (k) => {
    return k.replace(/_probability$/,'').replace(/_/g,' ')
  }

  useEffect(() => {
    if (!isOpen) return
    setLoading(true)
    setError(null)
    setForecast(null)
    setModel(null)

    // attempt to call backend /api/weather; fall back to simulated data on failure
    const doFetch = async () => {
      const lat = pin?.lat ?? 0
      const lon = pin?.lon ?? 0
      try {
        const url = new URL(`${API_BASE}/api/weather`)
        url.searchParams.set('latitude', String(lat))
        url.searchParams.set('longitude', String(lon))
        if (datetime) url.searchParams.set('datetime', String(datetime))
        url.searchParams.set('units', 'metric')

        const resp = await fetch(url.toString())
        if (!resp.ok) throw new Error(`server ${resp.status}`)
        const json = await resp.json()

        // map API response to our forecast + model shapes
        const data = json.data || {}

        // build a simple hourly series if the API does not provide hours
        const baseTime = datetime ? new Date(datetime) : new Date()
        const hours = []
        const precipVal = data.precipitation?.value ?? 0
        for (let i = 0; i < 8; i++) {
          const t = new Date(baseTime.getTime() + i * 3600 * 1000)
          hours.push({ time: t.toISOString(), precip: Number(precipVal) })
        }
        const total = hours.reduce((s, h) => s + h.precip, 0)
        const summary = data.climate_description || (total > 20 ? 'Heavy precipitation expected' : total > 5 ? 'Moderate rain expected' : 'Light or no rain expected')

        const forecastFromApi = { hours, total: Math.round(total * 10) / 10, summary }

        const modelFromApi = {
          metrics: {
            temperature: Number(data.temperature?.value ?? NaN),
            precipitation: Number(data.precipitation?.value ?? NaN),
            humidity: Number(data.humidity?.value ?? NaN),
            windspeed: Number(data.windspeed?.value ?? NaN),
            air_quality: Number((data.air_quality?.value && Number(data.air_quality.value)) || (data.air_quality?.value ?? NaN)),
          },
          extremes: data.extreme_weather || {},
          comfort: data.comfort_index || data.comfort || {},
          description: data.climate_description || '',
        }

        // combine forecast summary and model description into one field
        modelFromApi.description = `${forecastFromApi.summary}${modelFromApi.description ? ' ' + modelFromApi.description : ''}`.trim()

        setForecast(forecastFromApi)
        setModel(modelFromApi)
        setLoading(false)
        return
      } catch (e) {
        // fallback to simulated forecast
        const sim = simulateForecast(lat, lon, datetime)
        const simModel = simulateModelResults(lat, lon, sim.hours)
        // small delay to simulate network
        setTimeout(() => {
          // merge simulated forecast summary into model description
          simModel.description = `${sim.summary}${simModel.description ? ' ' + simModel.description : ''}`.trim()
          setForecast(sim)
          setModel(simModel)
          setLoading(false)
        }, 600)
        return
      }
    }

    doFetch()
  }, [isOpen, pin, datetime])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ fontFamily: '"DM Serif Display", serif' }}>
      <div onClick={onClose} className="absolute inset-0 bg-black/60"></div>
      <div className="relative w-9/12 rounded-2xl p-6 text-white" style={{ boxShadow: '0 10px 40px rgba(0,0,0,0.6)', backgroundColor: 'var(--nasa-deep)' }}>
        <div className="flex items-center justify-between mb-4">
          <div className="text-lg font-semibold" style={{ fontSize: '32px' }}>Weather Prediction</div>
          <button onClick={onClose} className="text-sm text-nasa-dark px-3 py-2 rounded" style={{ fontSize: '24px' }}>Close</button>
        </div>

        {!pin && (
          <div className="p-4 bg-red-900 rounded">Please place a pin on the map before predicting.</div>
        )}

        {loading && <div className="py-8">Loading forecast…</div>}

        {error && <div className="p-3 bg-red-900 rounded">{String(error)}</div>}

        {forecast && (
          <div style={{ padding: "8px" }}>
            <div className="mb-3 flex items-start" style={{ paddingBottom: '12px' }}>
              <div className="text-sm text-nasa-muted" style={{ fontSize: '24px', paddingRight: '40px',  textAlign: 'left' }}>
                Location: {pin ? `${Math.abs(pin.lat).toFixed(3)}°${pin.lat >= 0 ? 'N' : 'S'}, ${Math.abs(pin.lon).toFixed(3)}°${pin.lon >= 0 ? 'E' : 'W'}` : '—'}
              </div>
              <div className="text-sm text-nasa-muted" style={{ fontSize: '24px', textAlign: 'left' }}>
                Date & Time: {datetime ? new Date(datetime).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '—'}
              </div>
            </div>

            <div className="text-sm text-nasa-muted mb-2 font-semibold" style={{ fontSize: '28px', padding: '20px 0px 10px 0px', textAlign: 'left' }}>Summary</div>
            <div className="mb-4 font-semibold" style={{ fontSize: '20px', textAlign: 'left',  paddingBottom: '12px', paddingLeft: '0px', fontWeight: '400' }}> {forecast.summary}</div>

            {/* Metrics tiles: temperature, precipitation, humidity, windspeed, air_quality */}
            <div className="grid grid-cols-5 gap-3 mb-4">
              {model?.metrics ? (
                Object.entries(model.metrics).map(([k,v]) => (
                  <div key={k} className="p-3 bg-black/20 rounded text-center" style={{ borderRadius: '12px' }}>
                    <div className="text-sm text-nasa-muted uppercase" style={{ fontSize: '16px', fontFamily: "Bitter", textAlign: 'left', fontWeight: '800', padding: '0px 4px 10px 4px' }}>{k.replace(/_/g,' ')}</div>
                    <div className="text-lg font-bold" style={{ fontSize: '44px', fontWeight: '900', paddingTop: '16px', paddingBottom:'8px' }}>{v} <span style={{ fontSize: '18px', fontWeight: 600 }}>{unitForMetric(k)}</span></div>
                  </div>
                ))
              ) : (
                <div className="col-span-5 text-sm text-nasa-muted">Model results not available.</div>
              )}
            </div>

            {/* Extremes: show only entries with probability > 0.07 */}
            <div className="mb-3" >
              <div className="text-sm text-nasa-muted mb-2 font-semibold" style={{ fontSize: '28px', padding: '20px 0px 16px 0px', textAlign: 'left' }}>Notable Extreme Weather Probabilities</div>
              <div className="flex gap-3 flex-wrap" >
                {model?.extremes && Object.entries(model.extremes).filter(([k,v]) => v > 0.07).map(([k,v]) => (
                  <div key={k} className="p-3 bg-black/20 rounded text-center" style={{ minWidth: 210, borderRadius: '12px' }}>
                    <div className="text-sm text-nasa-muted uppercase" style={{ fontSize: '16px', fontFamily: "Bitter", textAlign: 'left', fontWeight: '800', padding: '0px 4px 10px 4px' }}>{prettyProbLabel(k)}</div>
                    <div className="text-lg font-bold" style={{ fontSize: '44px', fontWeight: '900', paddingTop: '16px', paddingBottom:'8px' }}>{Math.round(v*100)} <span style={{ fontSize: '18px', fontWeight: 600 }}>%</span></div>
                  </div>
                ))}
                {(!model?.extremes || Object.entries(model.extremes || {}).filter(([k,v]) => v > 0.07).length === 0) && (
                  <div className="text-sm text-nasa-muted">No high-probability extremes detected.</div>
                )}
              </div>
            </div>

            {/* Comfort */}
            <div className="mb-3">
              <div className="text-sm text-nasa-muted mb-2 font-semibold" style={{ fontSize: '28px', padding: '20px 0px 16px 0px', textAlign: 'left' }}>Comfort Concerns</div>
              <div className="flex gap-3 flex-wrap">
                {model?.comfort && Object.entries(model.comfort).filter(([k,v]) => v > 0.07).map(([k,v]) => (
                  <div key={k} className="p-3 bg-black/20 rounded text-center" style={{ minWidth: 210, borderRadius: '12px' }}>
                    <div className="text-sm text-nasa-muted uppercase" style={{ fontSize: '16px', fontFamily: "Bitter", textAlign: 'left', fontWeight: '800', padding: '0px 4px 10px 4px' }}>{k.replace(/_/g,' ')}</div>
                    <div className="text-lg font-bold" style={{ fontSize: '44px', fontWeight: '900', paddingTop: '16px', paddingBottom:'8px' }}>{Math.round(v*100)} <span style={{ fontSize: '18px', fontWeight: 600 }}>%</span></div>
                  </div>
                ))}
                {(!model?.comfort || Object.entries(model.comfort || {}).filter(([k,v]) => v > 0.07).length === 0) && (
                  <div className="text-sm text-nasa-muted">No major comfort concerns.</div>
                )}
              </div>
            </div>

            {/* Export CSV button */}
            <div className="flex justify-end">
              <button
                onClick={async () => {
                  const lat = pin?.lat ?? 0
                  const lon = pin?.lon ?? 0
                  // try API CSV first
                  try {
                    const url = new URL(`${API_BASE}/api/history.csv`)
                    url.searchParams.set('latitude', String(lat))
                    url.searchParams.set('longitude', String(lon))
                    const resp = await fetch(url.toString())
                    if (resp.ok) {
                      const blob = await resp.blob()
                      const filename = `history_${lat}_${lon}_${Date.now()}.csv`
                      const urlObj = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = urlObj
                      a.download = filename
                      document.body.appendChild(a)
                      a.click()
                      a.remove()
                      URL.revokeObjectURL(urlObj)
                      return
                    }
                    throw new Error(`server ${resp.status}`)
                  } catch (e) {
                    // fallback to local CSV builder
                    const rows = []
                    rows.push(['time','precip_mm'])
                    (forecast?.hours || []).forEach(h => rows.push([h.time, h.precip]))
                    rows.push([])
                    rows.push(['metric','value'])
                    if (model?.metrics) Object.entries(model.metrics).forEach(([k,v]) => rows.push([k,v]))
                    const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g,'""')}"`).join(',')).join('\n')
                    const blob = new Blob([csv], { type: 'text/csv' })
                    const url2 = URL.createObjectURL(blob)
                    const a2 = document.createElement('a')
                    a2.href = url2
                    a2.download = `forecast_${Date.now()}.csv`
                    document.body.appendChild(a2)
                    a2.click()
                    a2.remove()
                    URL.revokeObjectURL(url2)
                  }
                }}
                className="px-4 py-2 rounded bg-white text-black font-semibold"
              >
                Export CSV
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
