import { Dispatch, SetStateAction } from 'react';
const tabs = ['metrics', 'comparison', 'violation'] as const;
type Tab = (typeof tabs)[number];

export default function Navbar({
  active, setActive,
}: { active: Tab; setActive: Dispatch<SetStateAction<Tab>> }) {
  return (
    <nav className="sticky top-0 z-20 backdrop-blur bg-white/70 dark:bg-gray-900/70 shadow-sm">
      <ul className="flex gap-6 px-8 py-3">
        {tabs.map(t => (
          <li key={t}>
            <button
              onClick={() => setActive(t)}
              className={`uppercase tracking-wide relative
                ${active===t
                  ? 'text-signal-blue after:w-full'
                  : 'text-gray-500 hover:text-signal-blue after:w-0'
                }
                after:absolute after:-bottom-1 after:left-0 after:h-0.5
                after:bg-signal-blue after:transition-[width] after:duration-300`}
            >
              {t}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
