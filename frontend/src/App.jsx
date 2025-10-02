import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import { Button } from '@/components/ui/button'
import Hero from '@/components/custom/Hero'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      {/*Hero*/}
      {/* <Hero/> */}
      <div className="min-h-screen w-full bg-[radial-gradient(1200px_600px_at_50%_-20%,#1e3a8a_0%,#0b1020_60%,#000_100%)]">
        <main className="container mx-auto px-4 py-10">
          <Hero />
        </main>
      </div>


    </>
  )
}

export default App
