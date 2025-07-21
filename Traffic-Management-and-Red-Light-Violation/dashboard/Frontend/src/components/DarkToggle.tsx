export default function DarkToggle() {
  return (
    <button
      onClick={() => document.documentElement.classList.toggle('dark')}
      className="fixed bottom-6 right-6 bg-gray-800 text-white dark:bg-gray-200 dark:text-gray-900 rounded-full p-3 shadow-card"
      title="Toggle dark mode"
    >
      🌓
    </button>
  );
}
