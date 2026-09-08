import { useEffect, useRef, useState } from 'react'
import { supabase } from './supabaseClient'
import { fetchEventSfxAudioUrl, fetchProjectEvents } from './api'

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
 * 오디오 미리듣기: matched_sfx_path가 아직 Storage가 아니라 로컬 파일 경로라(U06 이슈),
 * 백엔드의 간이 서빙 엔드포인트(GET /events/{id}/sfx-audio)로 받아 재생한다.
 * <audio src>는 Authorization 헤더를 못 보내므로, fetch로 인증된 요청 → Blob → object URL로 변환.
 */
export default function ResultView({ project, session }) {
  const [events, setEvents] = useState([])
  const [videoUrl, setVideoUrl] = useState(null)
  const [duration, setDuration] = useState(0)
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [error, setError] = useState(null)
  const videoRef = useRef(null)
  const audioRef = useRef(null)
  const previewUrlRef = useRef(null) // 직전 object URL — 교체/언마운트 시 해제

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

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
    }
  }, [])

  function handleMarkerClick(ev) {
    setSelectedEvent(ev)
    if (videoRef.current) {
      videoRef.current.currentTime = ev.start_ms / 1000
    }
  }

  async function handlePreview() {
    if (!selectedEvent?.matched_sfx_path) return

    setPreviewLoading(true)
    setError(null)
    try {
      const url = await fetchEventSfxAudioUrl(selectedEvent.id, session.access_token)
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
      previewUrlRef.current = url
      if (audioRef.current) {
        audioRef.current.src = url
        await audioRef.current.play()
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setPreviewLoading(false)
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
          <button
            type="button"
            onClick={handlePreview}
            disabled={!selectedEvent.matched_sfx_path || previewLoading}
          >
            {previewLoading ? '불러오는 중...' : '미리듣기'}
          </button>
        </div>
      )}

      <audio ref={audioRef} hidden />

      <button type="button" onClick={handleDownloadCsv} style={{ marginTop: '1rem' }}>
        CSV 다운로드
      </button>
    </div>
  )
}
