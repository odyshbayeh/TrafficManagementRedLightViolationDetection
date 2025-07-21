/* src/components/Violations.tsx **************************************** */
import { useEffect, useState } from 'react'
import { API_URL } from '../config'
import Card from './Card'

export interface Violation {
  _id: string
  car_ID: string
  plate_text: string
  plate_detected: string   // base-64 JPEG (no data: prefix)
}

/* video lives in /public/violations/car_<ID>_violation_h264.mp4 */
const videoURL = (carId: string) =>
  `/violations/car_${carId}_violation_h264.mp4`

/* deterministic dummy person ------------------------------------------------ */
const firstNames = ['Nafe','Abood','Ody','Dana','Mohammad','Basel',
                    'Mahmoud','Alaa','Sadeel','Kareem']
const lastNames  = ['Abubaker','Abed','Shbayeh','Sbaih','Fares',
                    'Khater','Shahwan','Ajouly','Rimawi','Taweel']

function personFor(carId: string) {
  const n = parseInt(carId, 10) || 0
  return {
    first : firstNames[n % firstNames.length],
    last  : lastNames [n % lastNames.length],
    phone : `555-01${carId.padStart(2,'0')}`,
  }
}

/* ------------------------------------------------------------------ */
/*  Main component                                                    */
/* ------------------------------------------------------------------ */
export default function Violations() {
  const [violations, setViolations] = useState<Violation[]>([])
  const [selected , setSelected ]   = useState<Violation | null>(null)
  const [loading  , setLoading  ]   = useState(true)

  /* fetch once ------------------------------------------------------ */
  useEffect(() => {
    ;(async () => {
      try {
        const res  = await fetch(`${API_URL}/violations`)
        const data = (await res.json()) as Violation[]
        data.sort((a,b)=>a.car_ID.localeCompare(b.car_ID))
        setViolations(data)
        setSelected(data[0] ?? null)
      } finally { setLoading(false) }
    })()
  }, [])

  /* loader ---------------------------------------------------------- */
  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <svg className="w-10 h-10 animate-spin text-signal-blue"
             viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10"
                  stroke="currentColor" strokeWidth="4"
                  className="opacity-25"/>
          <path d="M4 12a8 8 0 0 1 8-8v4"
                fill="currentColor" className="opacity-75"/>
        </svg>
      </div>
    )
  }

  /* empty-state ----------------------------------------------------- */
  if (!violations.length) {
    return (
      <Card title="Violations" className="text-center">
        <p className="text-gray-500">No violations recorded.</p>
      </Card>
    )
  }

  /* UI -------------------------------------------------------------- */
  return (
    <div className="flex flex-col lg:flex-row gap-8">
      {/* ░░░ sidebar ░░░ */}
      <Card title="Cars"
            className="lg:w-80 lg:max-h-[80vh] overflow-y-auto sticky top-20">
        <ul className="space-y-3">
          {violations.map(v => (
            <li key={v._id || v.car_ID}>
              <button
                onClick={() => setSelected(v)}
                className={`flex items-center gap-3 w-full px-3 py-2 rounded-lg
                  transition-colors
                  ${selected?._id === v._id
                    ? 'bg-signal-blue/15 text-signal-blue ring-2 ring-signal-blue/40'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-800'}`}
              >
                <img
                  src={`data:image/jpeg;base64,${v.plate_detected}`}
                  alt="preview"
                  className="w-10 h-6 object-cover rounded border"
                />
                <span className="font-medium tracking-wide">
                  Car&nbsp;{v.car_ID}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </Card>

      {/* ░░░ details ░░░ */}
      <Card title="Violation Details" className="flex-1 space-y-10">
        {selected && (
          <>
            {/* plate hero */}
            <div className="relative mx-auto max-w-xs">
              <img
                src={`data:image/jpeg;base64,${selected.plate_detected}`}
                alt={`Plate ${selected.plate_text}`}
                className="rounded-xl shadow-2xl ring-4 ring-gray-900/80"
              />
              <span
                className="absolute bottom-2 left-1/2 -translate-x-1/2
                           px-3 py-1 rounded bg-black/70 text-white
                           text-lg font-semibold tracking-widest"
              >
                {selected.plate_text}
              </span>
            </div>

            {/* meta & auto-ticket badge */}
            <div className="flex flex-col items-center gap-4">
              <p className="text-sm text-gray-500">
                Car&nbsp;ID:&nbsp;<strong>{selected.car_ID}</strong>
              </p>
              <span
                className="inline-block px-4 py-1 rounded-full
                           bg-red-600/10 text-red-700 dark:text-red-400
                           text-sm font-medium"
              >
                Ticket issued automatically
              </span>
            </div>

            {/* driver info (dummy) */}
            {(() => {
              const p = personFor(selected.car_ID)
              return (
                <div className="mx-auto max-w-md w-full rounded-xl
                                bg-gray-50 dark:bg-gray-800/40 p-6 shadow">
                  <dl className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-gray-500">First name</dt><dd>{p.first}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Last name</dt><dd>{p.last}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Phone</dt><dd>{p.phone}</dd>
                    </div>
                  </dl>
                </div>
              )
            })()}

            {/* video */}
            <video
              key={selected.car_ID}
              controls
              className="w-full aspect-video rounded-xl shadow-lg bg-black/80"
            >
              <source src={videoURL(selected.car_ID)} type="video/mp4" />
              Sorry, your browser doesn’t support embedded videos.
            </video>
          </>
        )}
      </Card>
    </div>
  )
}
