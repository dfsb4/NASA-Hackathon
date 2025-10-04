import React, { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import TimePicker from './TimePicker'

function Header() {
  const [now, setNow] = useState(new Date())
  const [pickerOpen, setPickerOpen] = useState(false)
  const [userTime, setUserTime] = useState(null)

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

  // prevent background scrolling when picker is open
  useEffect(() => {
    if (pickerOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [pickerOpen])

  const openPicker = () => setPickerOpen(true)
  const closePicker = () => setPickerOpen(false)

  const onSetTime = (isoISO) => {
    // isoISO is like 'YYYY-MM-DDTHH:MM'
    setUserTime(isoISO)
    closePicker()
  }

  const formatISO = (iso) => {
    try {
      const [d, t] = iso.split('T')
      const [y, m, day] = d.split('-').map((s) => Number(s))
      const [hh, mm] = t.split(':').map((s) => Number(s))
      const dt = new Date(y, m - 1, day, hh, mm)
      return formatNow(dt)
    } catch (e) {
      return iso
    }
  }

  return (
    <>
      <div id="site-header" className='p-3 shadow-sm flex justify-between items-center px-5 background: dark-gray-800 bg-nasa-dark-gray-azure/90 ring-1 ring-white/10'>
        <div className="flex items-center gap-1">
          <img src="/weatherlens.svg" className="w-16 h-12" alt="WeatherLens logo" />
          <span className="text-sm font-semibold text-nasa-muted" style={{background: "var(--nasa-dark-gray-azure)", fontFamily: '"DM Serif Display", serif', fontWeight: '400', fontStyle: 'normal', display: "inline", color: "var(--nasa-muted)", fontSize: "32px", letterSpacing: '0.1em'}}>WeatherLens</span>
        </div>
        <div className="flex items-center gap-3 ml-auto pr-1">
          <button onClick={openPicker} className="text-white px-4 py-2 rounded-full font-semibold">Time</button>
          <time className="time text-sm font-semibold text-nasa-muted" dateTime={(userTime || now.toISOString())} style={{fontFamily: '"Bitter", serif', fontWeight: '700', fontSize: '24px', letterSpacing: '0.15em'}}>
            {userTime ? formatISO(userTime) : formatNow(now)}
          </time>
        </div>
      </div>

      <TimePicker isOpen={pickerOpen} onClose={closePicker} onSet={onSetTime} initialISO={userTime} />
    </>
  )
}

export default Header