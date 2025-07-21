/* src/components/Dashboard.tsx **************************************** */
import React, { useEffect, useRef, useState } from 'react'
import { PlayIcon, PauseIcon } from '@heroicons/react/24/solid'

import { API_URL } from '../config'
import { TrafficRecord } from '../types'

import Card       from './Card'
import Navbar     from './Navbar'
import DarkToggle from './DarkToggle'
import Violations from './Violations';
import { V } from 'framer-motion/dist/types.d-BSoEx4Ea'


/* ── constants ───────────────────────────────────────────────────────── */
const REAL_WORLD_TIMES: Record<number, number> = {
  0: 100, 1: 100, 2: 100, 3: 100, 4: 100,
  5: 101.67, 6: 98.33, 7: 103.33, 8: 91.73,
}
type Tab = 'metrics' | 'comparison' | 'violation'

/* helper to format seconds → mm:ss ------------------------------------ */
const fmt = (sec: number) =>
  `${String(Math.floor(sec / 60)).padStart(2, '0')}:${String(Math.floor(sec % 60)).padStart(2, '0')}`

/* ── dashboard component ─────────────────────────────────────────────── */
export default function Dashboard () {
  /* --------------- state --------------------------------------------- */
  const [tab , setTab ]            = useState<Tab>('metrics')
  const [chunks, setChunks]        = useState<number[]>([])
  const [selectedChunk, setChunk]  = useState(0)
  const [record, setRecord]        = useState<TrafficRecord | null>(null)

  /* video refs + elapsed-time states ---------------------------------- */
  const videoReal = useRef<HTMLVideoElement>(null)
  const videoSim  = useRef<HTMLVideoElement>(null)
  const [tReal, setTReal]   = useState(0)
  const [tSim , setTSim ]   = useState(0)
  const [isPlaying, setPlaying] = useState(false)

  /* --------------- fetch chunk list once ----------------------------- */
  // useEffect(() => {
  //   (async () => {
  //     const res  = await fetch(`${API_URL}/`)
  //     const data = (await res.json()) as TrafficRecord[]
  //     const uniq = [...new Set(data.map(r => r.chunk))].sort((a, b) => a - b)
  //     setChunks(uniq)
  //     if (uniq.length) setChunk(uniq[0])
  //   })()
  // }, [])

  /* --------------- fetch chunk list once ----------------------------- */
  useEffect(() => {
    (async () => {
      const res  = await fetch(`${API_URL}/chunks`);
      const uniq = (await res.json()) as number[];   // already sorted by backend
      setChunks(uniq);
      if (uniq.length) setChunk(uniq[0]);
    })();
  }, []);


  /* --------------- fetch record when chunk changes ------------------- */
  useEffect(() => {
    if (!chunks.length) return
    setRecord(null)
    ;(async () => {
      const res = await fetch(`${API_URL}/${selectedChunk}`)
      if (res.ok) setRecord(await res.json())
    })()
  }, [selectedChunk, chunks])

  /* --------------- wire up video events (only on comparison tab) ----- */
  useEffect(() => {
    if (tab !== 'comparison') { setPlaying(false); return }

    const v1 = videoReal.current
    const v2 = videoSim.current
    if (!v1 || !v2) return

    const onTime  = () => { setTReal(v1.currentTime); setTSim(v2.currentTime) }
    const onPlay  = () => setPlaying(true)
    const onPause = () => { if (v1.paused && v2.paused) setPlaying(false) }

    v1.addEventListener('timeupdate', onTime)
    v2.addEventListener('timeupdate', onTime)
    v1.addEventListener('play',  onPlay)
    v2.addEventListener('play',  onPlay)
    v1.addEventListener('pause', onPause)
    v2.addEventListener('pause', onPause)

    return () => {
      v1.removeEventListener('timeupdate', onTime)
      v2.removeEventListener('timeupdate', onTime)
      v1.removeEventListener('play',  onPlay)
      v2.removeEventListener('play',  onPlay)
      v1.removeEventListener('pause', onPause)
      v2.removeEventListener('pause', onPause)
    }
  }, [tab])

  /* --------------- derived figures for metrics ----------------------- */
  const recommendedTime = record ? record.recommendations.reduce((s, r) => s + r.duration_sec, 0): 0

  // const improvement = record && recommendedTime
  //   ? (REAL_WORLD_TIMES[selectedChunk] / recommendedTime - 1) * 100
  //   : 0

  /* totals for cars passed ------------------------------------------- */
  const totalCarsReal = record ? record.real_world.reduce((s, r) => s + r.cars_passed_in_real, 0): 0

  const totalCarsRecommended = record ? record.recommendations.reduce(
        (s, r) => s + (r.all_counts[r.recommended] ?? 0), 0): 0

    /*effectiveness (cars / sec) */
  const effReal        = REAL_WORLD_TIMES[selectedChunk]  ? totalCarsReal        / REAL_WORLD_TIMES[selectedChunk]  : 0;
  const effRecommended = recommendedTime                  ? totalCarsRecommended / recommendedTime: 0;

  const improvement = effRecommended - effReal 


  /* --------------- loader while chunk list arrives ------------------- */
  if (!chunks.length) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-white dark:bg-gray-900">
        <svg className="w-12 h-12 animate-spin text-signal-blue" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
          <path d="M4 12a8 8 0 018-8v4" fill="currentColor" className="opacity-75" />
        </svg>
      </div>
    )
  }

  /* --------------- play / pause both videos -------------------------- */
  const togglePlay = () => {
    const v1 = videoReal.current
    const v2 = videoSim.current
    if (!v1 || !v2) return
    if (isPlaying) { v1.pause(); v2.pause() }
    else           { v1.play();  v2.play()  }
  }

  /* --------------- UI ------------------------------------------------ */
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar active={tab} setActive={setTab} />

      <main className="flex-1 p-8 space-y-8">
        {/* ░░░ METRICS TAB ░░░ ------------------------------------------------ */}
        {tab === 'metrics' && (
          <>
            {/* chunk slider */}
            <Card>
              <label className="block mb-3 font-medium">
                Select Chunk:&nbsp;
                <span className="font-semibold text-signal-blue">{selectedChunk}</span>
              </label>
              <input
                type="range"
                min={chunks[0]}
                max={chunks[chunks.length - 1]}
                value={selectedChunk}
                onChange={e => setChunk(Number(e.target.value))}
                className="w-full accent-signal-blue"
              />
            </Card>

            {/* loader while record coming */}
            {!record ? (
              <Card className="flex flex-col items-center py-16">
                <svg className="w-8 h-8 animate-spin text-signal-blue" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
                  <path d="M4 12a8 8 0 018-8v4" fill="currentColor" className="opacity-75" />
                </svg>
                <p className="mt-3 text-sm">Loading data …</p>
              </Card>
            ) : (
              <>
                {/* ── Performance Summary ─────────────────────────────────────────── */}
                <Card title="Performance Summary">
                  <div
                    className="
                      flex flex-col items-center          /* centred on mobile  */
                      sm:flex-row sm:justify-center       /* centred row ≥ 640px */
                      gap-y-6 sm:gap-y-0 sm:gap-x-12      /* roomy spacing       */
                      text-center                         /* always centre text  */
                    "
                  >
                    {/* ── Real-world ─────────────────────────────────────────────── */}
                    <div className="min-w-[9rem]">
                      <p className="text-xs uppercase tracking-wide text-gray-500">
                        Real-world&nbsp;time
                      </p>
                      <p className="text-3xl font-semibold mt-1">
                        {REAL_WORLD_TIMES[selectedChunk].toFixed(2)}&nbsp;
                        <span className="text-base font-medium">s</span>
                      </p>
                      <p className="mt-2 text-sm text-gray-500">
                        Cars:&nbsp;<strong>{totalCarsReal}</strong>
                      </p>
                      <p className="text-sm text-gray-500">
                        Eff:&nbsp;<strong>{effReal.toFixed(2)}</strong>&nbsp;cars/s
                      </p>
                    </div>

                    {/* ── Improvement badge (sits in the middle on large screens) ── */}
                    <div className="flex flex-col items-center gap-2">
                      <p className="text-sm text-gray-500">Improvement</p>

                      {/* colour-code: green when the new plan is better */}
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-sm font-medium
                          ${improvement >= 0
                            ? 'bg-signal-green/20 text-signal-green'
                            : 'bg-signal-red/20 text-signal-red'}`}
                      >
                        {improvement.toFixed(2)}&nbsp;cars/s
                      </span>
                    </div>

                    {/* ── Recommended ────────────────────────────────────────────── */}
                    <div className="min-w-[9rem]">
                      <p className="text-xs uppercase tracking-wide text-gray-500">
                        Recommended&nbsp;time
                      </p>
                      <p className="text-3xl font-semibold mt-1">
                        {recommendedTime.toFixed(2)}&nbsp;
                        <span className="text-base font-medium">s</span>
                      </p>
                      <p className="mt-2 text-sm text-gray-500">
                        Cars:&nbsp;<strong>{totalCarsRecommended}</strong>
                      </p>
                      <p className="text-sm text-gray-500">
                        Eff:&nbsp;<strong>{effRecommended.toFixed(2)}</strong>&nbsp;cars/s
                      </p>
                    </div>
                  </div>
                </Card>



                {/* best frames */}
                <Card title="Best Frames">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {record.best_frames.map(f => (
                      <div key={f.id} className="space-y-2">
                        <p className="text-center font-medium">{f.id}</p>
                        <img
                          src={`data:image/jpeg;base64,${f.image}`}
                          alt={f.id}
                          className="w-full h-56 object-cover rounded-lg"
                        />
                      </div>
                    ))}
                  </div>
                </Card>

                {/* recommendations table (unchanged) */}
                <Card title="Recommendations">
                  <div className="overflow-x-auto">
                    <table className="min-w-[800px] w-full text-sm">
                      <thead>
                        <tr className="text-left bg-gray-100 dark:bg-gray-700">
                          <th className="px-4 py-2">#</th>
                          <th className="px-4 py-2">Current</th>
                          <th className="px-4 py-2">Recommended</th>
                          <th className="px-4 py-2">Duration&nbsp;(s)</th>
                          {['ID-1','ID-2','ID-3','ID-4'].map(id=>(
                            <th key={`cnt-${id}`} className="px-4 py-2">{id} Cnt</th>
                          ))}
                          {['ID-1','ID-2','ID-3','ID-4'].map(id=>(
                            <th key={`st-${id}`} className="px-4 py-2">{id} State</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {record.recommendations.map((rec,i)=>(
                          <tr key={i}
                              className={i%2 ? 'bg-gray-50 dark:bg-gray-800/40' : ''}>
                            <td className="px-4 py-2 font-medium">{i+1}</td>
                            <td className="px-4 py-2">{rec.current}</td>
                            <td className="px-4 py-2">{rec.recommended}</td>
                            <td className="px-4 py-2">{rec.duration_sec.toFixed(2)}</td>
                            {['ID-1','ID-2','ID-3','ID-4'].map(id=>(
                              <td key={`c-${i}-${id}`}
                                  className="px-4 py-2 text-center">
                                {rec.all_counts[id]}
                              </td>
                            ))}
                            {['ID-1','ID-2','ID-3','ID-4'].map(id=>{
                              const st = rec.all_states[id]
                              const color = st==='green'
                                ? 'bg-signal-green/20 text-signal-green'
                                : st==='yellow'
                                ? 'bg-signal-yellow/20 text-signal-yellow'
                                : 'bg-signal-red/20 text-signal-red'
                              return (
                                <td key={`s-${i}-${id}`}
                                    className={`px-4 py-2 text-center rounded ${color}`}>
                                  {st}
                                </td>
                              )
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </>
            )}
          </>
        )}

        {/* ░░░ COMPARISON TAB ░░░ --------------------------------------- */}
        {tab === 'comparison' && (
          <Card title="Video Comparison">
            <div className="flex flex-col lg:flex-row gap-6">
              {/* real-world video */}
              <div className="relative w-full lg:w-1/2">
                <video
                  ref={videoReal}
                  controls
                  className="aspect-video w-full rounded-lg shadow"
                >
                  <source src={`/chunk_${selectedChunk}_real_h264.mp4`} type="video/mp4" />
                </video>
                <time
                  className="absolute top-2 left-2 px-2 py-0.5 rounded
                             bg-black/60 text-white text-xs select-none">
                  {fmt(tReal)}
                </time>
              </div>

              {/* simulation video */}
              <div className="relative w-full lg:w-1/2">
                <video
                  ref={videoSim}
                  controls
                  className="aspect-video w-full rounded-lg shadow"
                >
                  <source src={`/chunk_${selectedChunk}_simulation_h264.mp4`} type="video/mp4" />
                </video>
                <time
                  className="absolute top-2 left-2 px-2 py-0.5 rounded
                             bg-black/60 text-white text-xs select-none">
                  {fmt(tSim)}
                </time>
              </div>
            </div>

            {/* play / pause toggle */}
            <div className="flex justify-center">
              <button
                onClick={togglePlay}
                className="mt-6 px-6 py-2 rounded-full bg-signal-blue text-white
                           hover:bg-signal-blue/90 flex items-center gap-3"
              >
                {isPlaying
                  ? <PauseIcon className="w-5 h-5" />
                  : <PlayIcon  className="w-5 h-5" />}
                {isPlaying ? 'Pause Both' : 'Play Both'}
              </button>
            </div>
          </Card>
        )}

        {/* ░░░ VIOLATION TAB ░░░ ---------------------------------------- */}
        {tab === 'violation' && <Violations />}
      </main>

      <DarkToggle />
    </div>
  )
}
