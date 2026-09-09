import { useEffect, useRef, useState } from 'react'
import { supabase } from './supabaseClient'
import {
  createProjectEvent,
  deleteProjectEvent,
  fetchEventSfxAudioUrl,
  fetchProjectEvents,
  updateProjectEvent,
} from './api'
import CorrectionPanel from './CorrectionPanel'

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
 *
 * U11: U10에서 화면(mock)에만 반영되던 보정(타입 변경/효과음 교체/삭제/추가)이 이제
 * 실제로 서버에 저장된다 (PATCH/POST/DELETE /projects/{id}/events...). 각 조작은 API 호출 →
 * 성공 시 서버가 돌려준 최신 행으로 로컬 state를 갱신하는 방식이라, 실패하면 화면이 바뀌지 않는다.
 */
export default function ResultView({ project, session }) {
  const [events, setEvents] = useState([])
  const [videoUrl, setVideoUrl] = useState(null)
  const [duration, setDuration] = useState(0)
  const [selectedEventId, setSelectedEventId] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [savingAction, setSavingAction] = useState(false) // U11: 보정 저장 API 호출 중
  const [newStart, setNewStart] = useState('')
  const [newEnd, setNewEnd] = useState('')
  const [error, setError] = useState(null)
  const videoRef = useRef(null)
  const audioRef = useRef(null)
  const previewUrlRef = useRef(null) // 직전 object URL — 교체/언마운트 시 해제

  // 선택된 이벤트는 항상 events 배열에서 다시 찾는다 — 그래야 보정(타입 변경 등)이
  // 바로 반영된다 (별도 복사본을 들고 있으면 수정 후에도 옛날 값을 보여주게 됨).
  const selectedEvent = events.find((e) => e.id === selectedEventId) ?? null

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
    setSelectedEventId(ev.id)
    if (videoRef.current) {
      videoRef.current.currentTime = ev.start_ms / 1000
    }
  }

  // --- U11: 보정 저장 API 연결 (U10에서는 여기가 전부 mock/로컬 state였음) ---

  async function handleChangeType(newType) {
    if (!selectedEventId || !newType.trim()) return
    setSavingAction(true)
    setError(null)
    try {
      const updated = await updateProjectEvent(
        project.id,
        selectedEventId,
        { effect_type: newType.trim() },
        session.access_token,
      )
      setEvents((prev) => prev.map((e) => (e.id === selectedEventId ? updated : e)))
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingAction(false)
    }
  }

  async function handleReplaceSfx(filename) {
    if (!selectedEventId) return
    setSavingAction(true)
    setError(null)
    try {
      const updated = await updateProjectEvent(
        project.id,
        selectedEventId,
        { sfx_filename: filename.trim() }, // 빈 문자열이면 서버에서 매칭 해제로 처리
        session.access_token,
      )
      setEvents((prev) => prev.map((e) => (e.id === selectedEventId ? updated : e)))
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingAction(false)
    }
  }

  async function handleDeleteEvent() {
    if (!selectedEventId) return
    setSavingAction(true)
    setError(null)
    try {
      await deleteProjectEvent(project.id, selectedEventId, session.access_token)
      setEvents((prev) => prev.filter((e) => e.id !== selectedEventId))
      setSelectedEventId(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingAction(false)
    }
  }

  async function handleAddEvent(e) {
    e.preventDefault()
    const startSec = parseFloat(newStart)
    const endSec = parseFloat(newEnd)
    if (Number.isNaN(startSec) || Number.isNaN(endSec) || endSec <= startSec) {
      setError('시작/종료 시각을 올바르게 입력해주세요 (초 단위, 종료 > 시작).')
      return
    }

    setSavingAction(true)
    setError(null)
    try {
      const created = await createProjectEvent(
        project.id,
        {
          startMs: Math.round(startSec * 1000),
          endMs: Math.round(endSec * 1000),
          effectType: 'unknown',
        },
        session.access_token,
      )
      setEvents((prev) => [...prev, created].sort((a, b) => a.start_ms - b.start_ms))
      setSelectedEventId(created.id)
      setNewStart('')
      setNewEnd('')
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingAction(false)
    }
  }

  async function handlePreview() {
    if (!selectedEvent?.matched_sfx_path) return

    setPreviewLoading(true)
    setError(null)
    try {
      // U11부터: matched_sfx_path가 실제로 서버(DB)에 저장된 값이므로, filename 파라미터
      // 없이 호출해도 최신 교체 결과가 그대로 재생된다 (U10 임시방편은 더 이상 필요 없음).
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
        <CorrectionPanel
          key={selectedEvent.id} // 이벤트를 바꿔 선택하면 입력 필드를 새 값으로 리셋
          event={selectedEvent}
          onChangeType={handleChangeType}
          onReplaceSfx={handleReplaceSfx}
          onDelete={handleDeleteEvent}
          onPreview={handlePreview}
          previewLoading={previewLoading}
          saving={savingAction}
        />
      )}

      <audio ref={audioRef} hidden />

      <form
        onSubmit={handleAddEvent}
        style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-end', marginTop: '1rem' }}
      >
        <label>
          시작(초)
          <input
            type="number"
            step="0.01"
            value={newStart}
            onChange={(e) => setNewStart(e.target.value)}
            style={{ width: 90, padding: '0.4rem', display: 'block' }}
          />
        </label>
        <label>
          종료(초)
          <input
            type="number"
            step="0.01"
            value={newEnd}
            onChange={(e) => setNewEnd(e.target.value)}
            style={{ width: 90, padding: '0.4rem', display: 'block' }}
          />
        </label>
        <button type="submit" disabled={savingAction}>
          이벤트 추가
        </button>
      </form>

      <button type="button" onClick={handleDownloadCsv} style={{ marginTop: '1rem' }}>
        CSV 다운로드
      </button>
    </div>
  )
}
