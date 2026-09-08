import { useEffect, useRef, useState } from 'react'
import { supabase } from './supabaseClient'
import { fetchProject, uploadProjectVideo } from './api'
import ResultView from './ResultView'

const STATUS_LABEL = {
  pending: '대기중',
  processing: '처리중',
  done: '완료',
  failed: '실패',
}

const POLL_INTERVAL_MS = 3000

/**
 * U08: 업로드 화면.
 * 파일 선택 → POST /projects/upload(U05) → 응답의 project.status를
 * GET /projects/{id}(U07)로 폴링하면서 "대기중 → 처리중 → 완료" 전환을 화면에 반영한다.
 */
export default function UploadPage({ session }) {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [project, setProject] = useState(null)
  const [error, setError] = useState(null)
  const pollTimer = useRef(null)

  useEffect(() => {
    return () => clearTimeout(pollTimer.current) // 화면 벗어나면 폴링 중단
  }, [])

  function pollUntilFinished(projectId) {
    clearTimeout(pollTimer.current)

    const tick = async () => {
      try {
        const updated = await fetchProject(projectId, session.access_token)
        setProject(updated)
        if (updated.status === 'pending' || updated.status === 'processing') {
          pollTimer.current = setTimeout(tick, POLL_INTERVAL_MS)
        }
      } catch (err) {
        setError(err.message)
      }
    }
    tick()
  }

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) return

    setUploading(true)
    setError(null)
    setProject(null)

    try {
      const created = await uploadProjectVideo(file, session.access_token)
      setProject(created) // status: "pending"
      pollUntilFinished(created.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div style={{ maxWidth: 720, margin: '4rem auto', textAlign: 'left' }}>
      <h2>영상 업로드</h2>
      <p style={{ opacity: 0.7 }}>{session.user.email}</p>

      <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <input
          type="file"
          accept="video/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button type="submit" disabled={!file || uploading}>
          {uploading ? '업로드 중...' : '업로드'}
        </button>
      </form>

      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      {project && (
        <div style={{ marginTop: '1.5rem' }}>
          <h3>처리 상태</h3>
          <p>
            상태: <strong>{STATUS_LABEL[project.status] ?? project.status}</strong>
            {(project.status === 'pending' || project.status === 'processing') && ' (자동으로 갱신됩니다...)'}
          </p>

          {project.status === 'done' && <ResultView project={project} session={session} />}

          {project.status === 'failed' && (
            <p style={{ color: 'crimson' }}>처리 중 오류가 발생했습니다. 다시 업로드해보세요.</p>
          )}
        </div>
      )}

      <button type="button" onClick={() => supabase.auth.signOut()} style={{ marginTop: '1rem' }}>
        로그아웃
      </button>
    </div>
  )
}
