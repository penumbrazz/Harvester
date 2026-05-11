/** Reusable pagination controls component with Previous/Next buttons and range indicator. */

interface PaginationControlsProps {
  total: number
  offset: number
  pageSize: number
  onPageChange: (offset: number) => void
}

const buttonBase: React.CSSProperties = {
  padding: '6px 12px',
  borderRadius: 'var(--radius-sm)',
  border: 'var(--border-whisper)',
  fontFamily: 'var(--font-family)',
  fontSize: 'var(--font-size-sm)',
  fontWeight: 500,
}

export function PaginationControls({
  total,
  offset,
  pageSize,
  onPageChange,
}: PaginationControlsProps) {
  if (total <= pageSize) return null

  const isPrevDisabled = offset === 0
  const isNextDisabled = offset + pageSize >= total
  const rangeEnd = Math.min(offset + pageSize, total)

  return (
    <div
      data-testid="pagination-controls"
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: 'var(--space-4)',
        fontSize: 'var(--font-size-sm)',
        color: 'var(--color-warm-gray-500)',
      }}
    >
      <span data-testid="pagination-range">
        {offset + 1}-{rangeEnd} of {total}
      </span>
      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        <button
          data-testid="pagination-prev"
          disabled={isPrevDisabled}
          onClick={() => onPageChange(Math.max(0, offset - pageSize))}
          style={{
            ...buttonBase,
            backgroundColor: isPrevDisabled
              ? 'var(--color-warm-white)'
              : 'var(--color-white)',
            cursor: isPrevDisabled ? 'not-allowed' : 'pointer',
            opacity: isPrevDisabled ? 0.5 : 1,
          }}
        >
          上一页
        </button>
        <button
          data-testid="pagination-next"
          disabled={isNextDisabled}
          onClick={() => onPageChange(offset + pageSize)}
          style={{
            ...buttonBase,
            backgroundColor: isNextDisabled
              ? 'var(--color-warm-white)'
              : 'var(--color-white)',
            cursor: isNextDisabled ? 'not-allowed' : 'pointer',
            opacity: isNextDisabled ? 0.5 : 1,
          }}
        >
          下一页
        </button>
      </div>
    </div>
  )
}
