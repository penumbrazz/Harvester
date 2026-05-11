import { Button } from './button'

interface ConfirmDialogProps {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  confirmVariant?: 'primary' | 'secondary' | 'ghost'
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = '确认',
  confirmVariant = 'primary',
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.4)',
        zIndex: 100,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) onCancel()
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        style={{
          background: 'var(--color-white, #ffffff)',
          borderRadius: 12,
          padding: 24,
          minWidth: 340,
          maxWidth: 440,
          border: '1px solid rgba(0,0,0,0.1)',
          boxShadow:
            'rgba(0,0,0,0.01) 0px 1px 3px, rgba(0,0,0,0.02) 0px 3px 7px, rgba(0,0,0,0.02) 0px 7px 15px, rgba(0,0,0,0.04) 0px 14px 28px, rgba(0,0,0,0.05) 0px 23px 52px',
        }}
      >
        <h3
          style={{
            margin: '0 0 8px',
            fontSize: 16,
            fontWeight: 600,
            color: 'var(--color-primary-text, rgba(0,0,0,0.95))',
          }}
        >
          {title}
        </h3>
        <p
          style={{
            margin: '0 0 20px',
            fontSize: 14,
            color: 'var(--color-secondary-text, #615d59)',
            lineHeight: 1.5,
          }}
        >
          {message}
        </p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button
            variant="ghost"
            onClick={onCancel}
            disabled={loading}
            data-testid="confirm-cancel"
          >
            取消
          </Button>
          <Button
            variant={confirmVariant}
            onClick={onConfirm}
            disabled={loading}
            data-testid="confirm-ok"
          >
            {loading ? '处理中...' : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
