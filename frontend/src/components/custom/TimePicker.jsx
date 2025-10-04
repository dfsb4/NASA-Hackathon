import React, { useEffect, useState } from 'react'

export default function TimePicker({ isOpen, onClose, onSet, initialISO }) {
  const now = new Date()

  // initialISO expected like 'YYYY-MM-DDTHH:MM' or null
  const initDate = initialISO ? initialISO.split('T')[0] : now.toISOString().slice(0,10)
  const initTime = initialISO ? initialISO.split('T')[1].slice(0,5) : now.toTimeString().slice(0,5)

  const [dateValue, setDateValue] = useState(initDate)
  const [timeValue, setTimeValue] = useState(initTime)
  const [year, setYear] = useState(Number(initDate.slice(0,4)))

  useEffect(() => {
    setDateValue(initDate)
    setTimeValue(initTime)
    setYear(Number(initDate.slice(0,4)))
  }, [initialISO, isOpen])

  // when year select changes, update dateValue's year portion
  useEffect(() => {
    const parts = dateValue.split('-')
    if (parts.length === 3) {
      parts[0] = String(year)
      setDateValue(parts.join('-'))
    }
  }, [year])

  const handleSet = () => {
    const iso = `${dateValue}T${timeValue}`
    if (onSet) onSet(iso)
  }

  if (!isOpen) return null

  const currentYear = new Date().getFullYear()
  const years = []
  for (let y = currentYear - 20; y <= currentYear + 5; y++) years.push(y)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div onClick={onClose} className="absolute inset-0 bg-black/60 backdrop-blur-sm"></div>
      <div className="relative w-full max-w-2xl bg-[#0b1020] rounded-2xl p-6" style={{boxShadow: '0 8px 40px rgba(2,6,23,0.8)'}}>
        <div className="flex items-center justify-between mb-4">
          <button onClick={onClose} className="text-nasa-muted px-3 py-2">Cancel</button>
          <div className="text-white text-xl font-semibold">Select date & time</div>
          <button onClick={handleSet} className="text-nasa-muted px-3 py-2">Set</button>
        </div>

        <div className="flex gap-6 items-center justify-center py-6">
          <div className="flex flex-col items-center">
            <label className="text-sm text-nasa-muted mb-2">Date</label>
            <input type="date" value={dateValue} onChange={(e) => setDateValue(e.target.value)} className="bg-transparent text-white p-3 rounded text-lg" />
          </div>

          <div className="flex flex-col items-center">
            <label className="text-sm text-nasa-muted mb-2">Time</label>
            <input id="time-input" type="time" value={timeValue} onChange={(e) => setTimeValue(e.target.value)} step="60" className="bg-transparent text-white p-3 rounded text-3xl" />
          </div>

          <div className="flex flex-col items-center">
            <label className="text-sm text-nasa-muted mb-2">Year</label>
            <select value={year} onChange={(e) => setYear(Number(e.target.value))} className="bg-transparent text-white p-3 rounded text-lg">
              {years.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-2 text-sm text-nasa-muted text-center">Year will sync with selected date.</div>
      </div>
    </div>
  )
}
