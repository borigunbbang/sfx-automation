const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

/**
 * U03에서 만든 FastAPI 백엔드의 GET /me를 호출해서
 * 로그인(JWT)이 실제로 백엔드와 연결됐는지 확인한다.
 */
export async function fetchMe(accessToken) {
  const res = await fetch(`${API_BASE_URL}/me`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })

  const body = await res.json().catch(() => null)

  if (!res.ok) {
    const detail = body?.detail ?? res.statusText
    throw new Error(`/me 호출 실패 (${res.status}): ${detail}`)
  }

  return body
}
