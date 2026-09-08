import { useState } from 'react'
import { supabase } from './supabaseClient'

/**
 * 가입/로그인 화면.
 * - U02에서 설정한 비밀번호 정책: 8자 이상 + 대문자/소문자/숫자 각 1개 이상
 * - U02에서 Confirm email이 켜져 있으므로, 가입 후에는 확인 메일의 링크를 눌러야 로그인 가능
 */
export default function AuthForm() {
  const [mode, setMode] = useState('login') // 'login' | 'signup'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null) // { type: 'error' | 'info', text }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setMessage(null)

    try {
      if (mode === 'signup') {
        const { error } = await supabase.auth.signUp({ email, password })
        if (error) throw error
        setMessage({
          type: 'info',
          text: '가입 요청 완료. 받은 확인 이메일의 링크를 클릭한 뒤 로그인해주세요.',
        })
        setMode('login')
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) throw error
        // 로그인 성공 시 App.jsx의 onAuthStateChange가 세션을 감지해서 화면을 전환한다.
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 360, margin: '4rem auto', textAlign: 'left' }}>
      <h2>{mode === 'signup' ? '회원가입' : '로그인'}</h2>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <label>
          이메일
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </label>

        <label>
          비밀번호
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ width: '100%', padding: '0.5rem' }}
          />
          {mode === 'signup' && (
            <small style={{ display: 'block', opacity: 0.7 }}>
              8자 이상, 대문자/소문자/숫자를 각각 최소 1개 포함해야 합니다.
            </small>
          )}
        </label>

        <button type="submit" disabled={loading}>
          {loading ? '처리 중...' : mode === 'signup' ? '가입하기' : '로그인'}
        </button>
      </form>

      {message && (
        <p style={{ color: message.type === 'error' ? 'crimson' : 'inherit' }}>{message.text}</p>
      )}

      <button
        type="button"
        onClick={() => {
          setMode(mode === 'signup' ? 'login' : 'signup')
          setMessage(null)
        }}
        style={{ marginTop: '1rem', background: 'none', border: 'none', textDecoration: 'underline', cursor: 'pointer' }}
      >
        {mode === 'signup' ? '이미 계정이 있으신가요? 로그인' : '계정이 없으신가요? 회원가입'}
      </button>
    </div>
  )
}
