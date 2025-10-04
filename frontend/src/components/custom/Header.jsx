import React from 'react'
import { Button } from '@/components/ui/button'

function Header() {
  return (
    <div className='p-3 shadow-sm flex justify-between items-center px-5 background: dark-gray-800 bg-nasa-dark-gray-azure/90 ring-1 ring-white/10'>
      <div className="flex items-center gap-1">
        <img src="/weatherlens.svg" className="w-16 h-12" alt="WeatherLens logo" />
        <span className="text-sm font-semibold text-nasa-muted" style={{fontFamily: '"DM Serif Display", serif', fontWeight: '400', fontStyle: 'normal', display: "inline", color: "var(--nasa-muted)", fontSize: "32px"}}>WeatherLens</span>
      </div>
        {/* <div className="h1" style={{fontFamily: '"DM Serif Display", serif', fontWeight: '400', fontStyle: 'normal', display: "inline", color: "var(--nasa-muted)"}}>
          WeatherLens
        </div> */}
    </div>
  )
}

export default Header