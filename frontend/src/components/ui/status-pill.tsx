type PillVariant = 'success' | 'error' | 'warning' | 'info' | 'default'

interface StatusPillProps {
  variant?: PillVariant
  children: React.ReactNode
}

const variantColors: Record<PillVariant, { bg: string; text: string; border?: string }> = {
  success: { bg: 'var(--color-pill-success-bg)', text: 'var(--color-pill-success-text)' },
  error: { bg: 'var(--color-pill-error-bg)', text: 'var(--color-pill-error-text)' },
  warning: { bg: 'var(--color-pill-warning-bg)', text: 'var(--color-pill-warning-text)' },
  info: { bg: 'var(--color-pill-info-bg)', text: 'var(--color-pill-info-text)' },
  default: {
    bg: 'var(--color-pill-default-bg)',
    text: 'var(--color-pill-default-text)',
    border: '2px solid var(--color-pill-default-border)',
  },
}

export function StatusPill({ variant = 'default', children }: StatusPillProps) {
  const colors = variantColors[variant]

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '4px 12px',
        borderRadius: 'var(--radius-pill)',
        backgroundColor: colors.bg,
        color: colors.text,
        fontFamily: 'var(--font-family)',
        fontSize: 'var(--font-size-xs)',
        fontWeight: 600,
        letterSpacing: '0.125px',
        lineHeight: 1.33,
        ...(colors.border ? { border: colors.border } : {}),
      }}
    >
      {children}
    </span>
  )
}
