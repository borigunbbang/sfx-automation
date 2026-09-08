import { useEffect, useState } from 'react'
import { supabase } from './supabaseClient'
import { fetchMe } from './api'

/**
 * 로그인 성공 후, U03의 GET /me를 호출해서
 * "프론트엔드 로그인 → 백엔드 인증"이 실제로 연결됐는지 화면에 보여준다.
 */
export default function MePanel({ session }) {
  const [me, setMe] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    setLoading(true)
    setError(null)

    fetchMe(session.access_token)
      .then((data) => {
        if (!cancelled) setMe(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [session.access_token])

  return (
    <div style={{ maxWidth: 480, margin: '4rem auto', textAlign: 'left' }}>
      <h2>로그인 완료</h2>
      <p>Supabase 세션 이메일: {session.user.email}</p>

      <h3>GET /me 응답 (FastAPI 백엔드, U03)</h3>
      {loading && <p>불러오는 중...</p>}
      {error && <p style={{ color: 'crimson' }}>백엔드 연결 실패: {error}</p>}
      {me && (
        <pre style={{ background: '#1115', padding: '1rem', borderRadius: 8, overflowX: 'auto' }}>
          {JSON.stringify(me, null, 2)}
        </pre>
      )}

      <button type="button" onClick={() => supabase.auth.signOut()}>
        로그아웃
      </button>
    </div>
  )
}
