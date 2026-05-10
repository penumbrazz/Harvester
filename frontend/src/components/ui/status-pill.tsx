type PillVariant = 'success' | 'error' | 'warning' | 'info' | 'default'

interface StatusPillProps {
  variant?: PillVariant
  children: React.ReactNode
}

const variantColors: Record<PillVariant, { bg: string; text: string }> = {
  success: { bg: '#e6f9ed', text: '#1aae39' },
  error: { bg: '#fff0eb', text: '#dd5b00' },
  warning: { bg: '#fff7e6', text: '#dd5b00' },
  info: {
    bg: 'var(--color-badge-blue-bg)',
    text: 'var(--color-badge-blue-text)',
  },
  default: {
    bg: 'var(--color-warm-white)',
    text: 'var(--color-warm-gray-500)',
  },
}

export function StatusPill({ variant = 'default', children }: StatusPillProps) {
  const colors = variantColors[variant]

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '4px 8px',
        borderRadius: 'var(--radius-pill)',
        backgroundColor: colors.bg,
        color: colors.text,
        fontFamily: 'var(--font-family)',
        fontSize: 'var(--font-size-xs)',
        fontWeight: 600,
        letterSpacing: '0.125px',
        lineHeight: 1.33,
      }}
    >
      {children}
    </span>
  )
}
