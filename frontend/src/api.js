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

/**
 * U07의 GET /projects/{id}/events로 이벤트 목록(타임라인 마커용)을 가져온다.
 */
export async function fetchProjectEvents(projectId, accessToken) {
  const res = await fetch(`${API_BASE_URL}/projects/${projectId}/events`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  return parseJsonOrThrow(res, 'GET /projects/{id}/events')
}

/**
 * U11: 이벤트 보정(타입 변경/효과음 교체/시간 수정)을 저장한다.
 * body는 EventUpdate의 부분집합만 보내면 됨 — 예: { effect_type } 또는 { sfx_filename }.
 * sfx_filename에 빈 문자열을 보내면 매칭 해제(matched_sfx_path=null).
 * 저장된 이벤트 행(전체 필드)을 그대로 돌려받는다.
 */
export async function updateProjectEvent(projectId, eventId, patch, accessToken) {
  const res = await fetch(`${API_BASE_URL}/projects/${projectId}/events/${eventId}`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(patch),
  })
  return parseJsonOrThrow(res, 'PATCH /projects/{id}/events/{eid}')
}

/**
 * U11: 이벤트 수동 추가를 저장한다 (U10에서는 화면에만 있던 local-* 이벤트).
 * 생성된 이벤트 행(실제 서버 id 포함)을 돌려받는다.
 */
export async function createProjectEvent(projectId, { startMs, endMs, effectType }, accessToken) {
  const res = await fetch(`${API_BASE_URL}/projects/${projectId}/events`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ start_ms: startMs, end_ms: endMs, effect_type: effectType }),
  })
  return parseJsonOrThrow(res, 'POST /projects/{id}/events')
}

/**
 * U11: 이벤트를 삭제한다.
 */
export async function deleteProjectEvent(projectId, eventId, accessToken) {
  const res = await fetch(`${API_BASE_URL}/projects/${projectId}/events/${eventId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  return parseJsonOrThrow(res, 'DELETE /projects/{id}/events/{eid}')
}

/**
 * U09(재추가)/U10: 매칭된 효과음 미리듣기.
 * <audio src>는 커스텀 헤더(Authorization)를 못 보내서, fetch로 인증된 요청을 보낸 뒤
 * Blob → object URL로 변환해서 재생한다.
 *
 * `filename`을 넘기면 DB의 matched_sfx_path 대신 그 파일명으로 미리듣는다 —
 * U10 보정 UI의 "효과음 교체"는 화면(mock)에만 반영되고 서버에는 저장되지 않으므로,
 * 교체 직후 바뀐 소리를 들으려면 이 파라미터가 필요하다.
 */
export async function fetchEventSfxAudioUrl(eventId, accessToken, filename) {
  const query = filename ? `?filename=${encodeURIComponent(filename)}` : ''
  const res = await fetch(`${API_BASE_URL}/events/${eventId}/sfx-audio${query}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(`효과음 불러오기 실패 (${res.status}): ${body?.detail ?? res.statusText}`)
  }
  const blob = await res.blob()
  return URL.createObjectURL(blob)
}
