import { useEffect, useState } from 'react'
import { supabase } from './supabaseClient'
import AuthForm from './AuthForm'
import MePanel from './MePanel'
import './App.css'

function App() {
  const [session, setSession] = useState(undefined) // undefined = 아직 확인 중

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])

  if (session === undefined) {
    return <p style={{ textAlign: 'center', marginTop: '4rem' }}>확인 중...</p>
  }

  return session ? <MePanel session={session} /> : <AuthForm />
}

export default App
