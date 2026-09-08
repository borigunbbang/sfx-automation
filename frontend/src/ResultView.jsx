import { useEffect, useRef, useState } from 'react'
import { supabase } from './supabaseClient'
import { fetchProjectEvents } from './api'

const VIDEOS_BUCKET = import.meta.env.VITE_SUPABASE_VIDEOS_BUCKET
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

const MARKER_COLOR = {
  unknown: '#999',
}
const DEFAULT_MARKER_COLOR = '#e0662b' // 분류된 효과 타입

function videoPathToStoragePath(videoPath) {
  const prefix = `${VIDEOS_BUCKET}/`
  return videoPath.startsWith(prefix) ? videoPath.slice(prefix.length) : videoPath
}

/**
 * U09: 결과 확인 화면.
 * 영상 재생 + 타임라인 마커(U07의 이벤트 목록) — 마커 클릭 시 해당 시점으로 이동하고 상세 정보를 보여준다.
 *
 * 오디오 미리듣기는 이번 Unit에서는 생략한다 (사용자 결정) — matched_sfx_path가 아직
 * 로컬 파일 경로라 브라우저가 접근할 수 없기 때문. SFX를 Storage로 옮기는 작업은
 * 별도 Unit에서 다룰 예정 (handoff/U06_summary.md 참고).
 */
export default function ResultView({ project, session }) {
  const [events, setEvents] = useState([])
  const [videoUrl, setVideoUrl] = useState(null)
  const [duration, setDuration] = useState(0)
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [error, setError] = useState(null)
  const videoRef = useRef(null)

  useEffect(() => {
    let cancelled = false

    fetchProjectEvents(project.id, session.access_token)
      .then((data) => {
        if (!cancelled) setEvents(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })

    const storagePath = videoPathToStoragePath(project.video_path)
    supabase.storage
      .from(VIDEOS_BUCKET)
      .createSignedUrl(storagePath, 3600)
      .then(({ data, error: signError }) => {
        if (cancelled) return
        if (signError) setError(signError.message)
        else setVideoUrl(data.signedUrl)
      })

    return () => {
      cancelled = true
    }
  }, [project.id, project.video_path, session.access_token])

  function handleMarkerClick(ev) {
    setSelectedEvent(ev)
    if (videoRef.current) {
      videoRef.current.currentTime = ev.start_ms / 1000
    }
  }

  async function handleDownloadCsv() {
    try {
      const res = await fetch(`${API_BASE_URL}/projects/${project.id}/export.csv`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      })
      if (!res.ok) throw new Error(`CSV 다운로드 실패 (${res.status})`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `project_${project.id}_events.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div style={{ marginTop: '1.5rem' }}>
      <h3>결과 확인</h3>
      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      {videoUrl && (
        <video
          ref={videoRef}
          src={videoUrl}
          controls
          style={{ width: '100%', borderRadius: 8 }}
          onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
        />
      )}

      {duration > 0 && (
        <div
          style={{
            position: 'relative',
            height: 32,
            marginTop: '0.75rem',
            background: '#8883',
            borderRadius: 4,
          }}
        >
          {events.map((ev) => (
            <button
              key={ev.id}
              type="button"
              title={`${(ev.start_ms / 1000).toFixed(2)}s - ${ev.effect_type}`}
              onClick={() => handleMarkerClick(ev)}
              style={{
                position: 'absolute',
                left: `${(ev.start_ms / 1000 / duration) * 100}%`,
                top: 0,
                width: 10,
                height: '100%',
                border: 'none',
                borderRadius: 2,
                cursor: 'pointer',
                background: MARKER_COLOR[ev.effect_type] ?? DEFAULT_MARKER_COLOR,
              }}
            />
          ))}
        </div>
      )}

      <p style={{ opacity: 0.7, fontSize: '0.85rem' }}>
        이벤트 {events.length}건 감지됨 — 마커를 클릭하면 해당 시점으로 이동합니다.
      </p>

      {selectedEvent && (
        <div style={{ background: '#8882', padding: '0.75rem', borderRadius: 8 }}>
          <p>
            {(selectedEvent.start_ms / 1000).toFixed(2)}s ~ {(selectedEvent.end_ms / 1000).toFixed(2)}s
            &nbsp;— 효과 타입: <strong>{selectedEvent.effect_type}</strong>
          </p>
          <p>
            매칭된 효과음:{' '}
            {selectedEvent.matched_sfx_path
              ? selectedEvent.matched_sfx_path.split('/').pop()
              : '없음 (미분류)'}
          </p>
          <button type="button" disabled title="SFX를 Storage로 옮기는 작업은 이후 Unit에서 진행 예정">
            미리듣기 (준비 중)
          </button>
        </div>
      )}

      <button type="button" onClick={handleDownloadCsv} style={{ marginTop: '1rem' }}>
        CSV 다운로드
      </button>
    </div>
  )
}
