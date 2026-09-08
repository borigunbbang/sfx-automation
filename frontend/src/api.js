const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

async function parseJsonOrThrow(res, label) {
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = body?.detail ?? res.statusText
    throw new Error(`${label} 실패 (${res.status}): ${detail}`)
  }
  return body
}

/**
 * U03에서 만든 FastAPI 백엔드의 GET /me를 호출해서
 * 로그인(JWT)이 실제로 백엔드와 연결됐는지 확인한다.
 */
export async function fetchMe(accessToken) {
  const res = await fetch(`${API_BASE_URL}/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  return parseJsonOrThrow(res, 'GET /me')
}

/**
 * U05의 POST /projects/upload로 영상을 업로드한다.
 * 성공하면 status: "pending"인 project 행을 그대로 돌려받는다.
 */
export async function uploadProjectVideo(file, accessToken) {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${API_BASE_URL}/projects/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: formData,
  })
  return parseJsonOrThrow(res, 'POST /projects/upload')
}

/**
 * U07의 GET /projects/{id}로 project 상태(대기중/처리중/완료/실패)를 조회한다.
 * U08의 상태 폴링이 이걸 반복 호출한다.
 */
export async function fetchProject(projectId, accessToken) {
  const res = await fetch(`${API_BASE_URL}/projects/${projectId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  return parseJsonOrThrow(res, 'GET /projects/{id}')
}
