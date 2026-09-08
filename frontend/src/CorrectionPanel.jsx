import { useState } from 'react'

/**
 * U10: 보정 UI.
 * 선택된 이벤트 하나에 대해 타입 변경 / 효과음 교체 / 삭제를 할 수 있는 패널.
 *
 * Mock 전략(TASK_BREAKDOWN.md 그대로): 여기서 하는 조작은 화면(부모의 로컬 state)에만
 * 반영되고 서버에는 저장되지 않는다 — 실제 저장 API는 U11에서 붙인다.
 */
export default function CorrectionPanel({ event, onChangeType, onReplaceSfx, onDelete, onPreview, previewLoading }) {
  const [typeInput, setTypeInput] = useState(event.effect_type)
  const [sfxInput, setSfxInput] = useState(event.matched_sfx_path?.split('/').pop() ?? '')

  return (
    <div style={{ background: '#8882', padding: '0.75rem', borderRadius: 8 }}>
      <p>
        {(event.start_ms / 1000).toFixed(2)}s ~ {(event.end_ms / 1000).toFixed(2)}s
      </p>

      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.5rem' }}>
        <label style={{ flex: 1 }}>
          효과 타입
          <input
            value={typeInput}
            onChange={(e) => setTypeInput(e.target.value)}
            style={{ width: '100%', padding: '0.4rem' }}
          />
        </label>
        <button type="button" onClick={() => onChangeType(typeInput)} style={{ marginTop: '1.2rem' }}>
          변경
        </button>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.5rem' }}>
        <label style={{ flex: 1 }}>
          효과음 파일명
          <input
            value={sfxInput}
            onChange={(e) => setSfxInput(e.target.value)}
            placeholder="예: iam 컷인 02.wav"
            style={{ width: '100%', padding: '0.4rem' }}
          />
        </label>
        <button type="button" onClick={() => onReplaceSfx(sfxInput)} style={{ marginTop: '1.2rem' }}>
          교체
        </button>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <button type="button" onClick={onPreview} disabled={!event.matched_sfx_path || previewLoading}>
          {previewLoading ? '불러오는 중...' : '미리듣기'}
        </button>
        <button type="button" onClick={onDelete} style={{ color: 'crimson' }}>
          이벤트 삭제
        </button>
      </div>
    </div>
  )
}
