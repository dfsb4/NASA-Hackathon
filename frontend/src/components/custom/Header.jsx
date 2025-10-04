import React, { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'

function Header() {
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    // update every minute on the minute
    const tick = () => setNow(new Date())
    const msUntilNextMinute = 60000 - (now.getSeconds() * 1000 + now.getMilliseconds())
    const timeoutId = setTimeout(() => {
      tick()
      const intervalId = setInterval(tick, 60000)
      // store on window so we can clear in cleanup via closure
      window.__header_time_interval = intervalId
    }, msUntilNextMinute)
    return () => {
      clearTimeout(timeoutId)
      if (window.__header_time_interval) {
        clearInterval(window.__header_time_interval)
        window.__header_time_interval = undefined
      }
    }
  }, [now])

  const ordinal = (d) => {
    const j = d % 10,
      k = d % 100
    if (j === 1 && k !== 11) return 'st'
    if (j === 2 && k !== 12) return 'nd'
    if (j === 3 && k !== 13) return 'rd'
    return 'th'
  }

  const formatNow = (date) => {
    const year = date.getFullYear()
    const month = date.toLocaleString('en', { month: 'short' }) // e.g., Oct
    const day = date.getDate()
    const hours = String(date.getHours()).padStart(2, '0')
    const mins = String(date.getMinutes()).padStart(2, '0')
    return `${year} ${month} ${day}${ordinal(day)} ${hours}:${mins}`
  }

  return (
    <div className='p-3 shadow-sm flex justify-between items-center px-5 background: dark-gray-800 bg-nasa-dark-gray-azure/90 ring-1 ring-white/10'>
      <div className="flex items-center gap-1">
        <img src="/weatherlens.svg" className="w-16 h-12" alt="WeatherLens logo" />
        <span className="text-sm font-semibold text-nasa-muted" style={{fontFamily: '"DM Serif Display", serif', fontWeight: '400', fontStyle: 'normal', display: "inline", color: "var(--nasa-muted)", fontSize: "32px", letterSpacing: '0.1em'}}>WeatherLens</span>
      </div>

      <time className="time text-sm font-semibold text-nasa-muted" dateTime={now.toISOString()} style={{fontFamily: '"Bitter", serif', fontWeight: '700', fontSize: '24px', paddingRight: '10px', letterSpacing: '0.15em'}}>
        {formatNow(now)}
      </time>
    </div>
  )
}

export default Header