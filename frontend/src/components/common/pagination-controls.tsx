import { Button } from 'animal-island-ui'

interface PaginationControlsProps {
  total: number
  offset: number
  pageSize: number
  onPageChange: (offset: number) => void
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
        color: 'var(--color-text-body)',
      }}
    >
      <span data-testid="pagination-range">
        {offset + 1}-{rangeEnd} of {total}
      </span>
      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        <Button
          type="default"
          size="small"
          disabled={isPrevDisabled}
          onClick={() => onPageChange(Math.max(0, offset - pageSize))}
          data-testid="pagination-prev"
        >
          上一页
        </Button>
        <Button
          type="default"
          size="small"
          disabled={isNextDisabled}
          onClick={() => onPageChange(offset + pageSize)}
          data-testid="pagination-next"
        >
          下一页
        </Button>
      </div>
    </div>
  )
}
