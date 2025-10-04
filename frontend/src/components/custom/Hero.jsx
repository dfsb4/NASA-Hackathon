import React from 'react'
import {Button} from '@/components/ui/button'
import {Link} from 'react-router-dom'

function Hero() {
  return (
    // <div className='flex flex-col items-center mx-56 gap-9'>
    //     <h1 className='font-extrabold text-[50px] text-center mt-16'>
    //         <span className='text-[#0000ff]'>NASA-HACKATHON: </span><br />Slowly
    //     </h1>
    //     <p className='text-xl test-gray-500 text-center'>DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4</p>
    //     <Link to='/create-trip'>
    //         <Button>Get Started</Button>
    //     </Link>
        
    // </div>
    <div className="relative mx-0 w-full px-4 md:px-16 mt-10 overflow-hidden rounded-3xl p-10 md:p-16
      flex flex-col items-center gap-10 text-slate-100
      bg-[radial-gradient(1200px_600px_at_50%_-20%,#1e3a8a_0%,#0b1020_60%,#000000_100%)]
      ring-1 ring-white/10 shadow-2xl">

      {/* 星光微粒（幾個 twinkle 點） */}
      <span className="pointer-events-none absolute left-[10%] top-[18%] h-1 w-1 rounded-full bg-white/80 animate-pulse" />
      <span className="pointer-events-none absolute left-[35%] top-[40%] h-1 w-1 rounded-full bg-white/60 animate-pulse [animation-delay:200ms]" />
      <span className="pointer-events-none absolute left-[70%] top-[25%] h-1 w-1 rounded-full bg-white/70 animate-pulse [animation-delay:400ms]" />
      <span className="pointer-events-none absolute left-[82%] top-[55%] h-1 w-1 rounded-full bg-white/80 animate-pulse [animation-delay:600ms]" />
      <span className="pointer-events-none absolute left-[20%] top-[70%] h-1 w-1 rounded-full bg-white/50 animate-pulse [animation-delay:800ms]" />

      {/* 霧光星雲 */}
      <div className="pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full blur-3xl
        bg-[conic-gradient(from_180deg_at_50%_50%,#60a5fa_0%,#a78bfa_30%,#22d3ee_60%,transparent_60%)] opacity-30" />
      <div className="pointer-events-none absolute -right-16 top-20 h-64 w-64 rounded-full blur-3xl
        bg-[conic-gradient(from_90deg_at_50%_50%,#f472b6_0%,#818cf8_35%,#22d3ee_65%,transparent_65%)] opacity-25" />

      {/* 行星（柔和漸層球） */}
      <div className="pointer-events-none absolute -right-8 -bottom-8 h-52 w-52 rounded-full
        bg-[radial-gradient(circle_at_30%_30%,#93c5fd_0%,#1e3a8a_60%,#0b1020_100%)]
        shadow-[0_0_60px_10px_rgba(59,130,246,0.35)] opacity-70" />

      {/* 標題 */}
      <h1 className="text-center font-extrabold leading-tight">
        <span className="block text-[14px] tracking-[0.4em] text-blue-300/80 uppercase mb-2">
          NASA • HACKATHON
        </span>
        <span className="block text-transparent bg-clip-text
          bg-[linear-gradient(90deg,#60a5fa,40%,#a78bfa,80%,#22d3ee)]
          drop-shadow-[0_0_25px_rgba(96,165,250,0.35)]
          text-4xl md:text-6xl">
          Mission: Slowly
        </span>
      </h1>

      {/* 副標（修正原本的 test-gray-500 → text-gray-400） */}
      <p className="w-full text-center text-gray-300/80 text-base md:text-lg leading-relaxed">
        DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4DFSB4
      </p>

      {/* CTA */}
      <div className="flex items-center gap-4">
        <Link to="/create-trip">
          <Button
            className="px-6 py-5 text-base font-semibold
            bg-white/10 hover:bg-white/20 border border-white/20
            rounded-xl shadow-lg backdrop-blur
            transition-all duration-300 hover:shadow-[0_10px_35px_rgba(59,130,246,0.45)]">
            Get Started
          </Button>
        </Link>

        {/* 額外資訊小標籤（可移除） */}
        <span className="hidden md:inline-block text-xs tracking-widest text-blue-200/70 uppercase">
          T-MINUS READY ✅
        </span>
      </div>

      {/* 下緣星際飾條 */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1
        bg-[repeating-linear-gradient(135deg,#3b82f6_0_14px,#22d3ee_14px_28px,#0ea5e9_28px_42px,#0000_42px_56px)]
        opacity-30" />
    </div>

  )
}

export default Hero