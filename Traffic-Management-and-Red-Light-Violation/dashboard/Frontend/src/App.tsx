import { useState } from 'react'
import Login from './components/Login'
import Dashboard from './components/Dashboard'

function App() {
  const [user, setUser] = useState<string | null>(null)

  return (
    <div className={user ? 'container mx-auto p-4' : ''}>
      {!user ? (
        <Login onLogin={setUser} />
      ) : (
        <>
          <Dashboard />
        </>
      )}
    </div>
  )
}

export default App