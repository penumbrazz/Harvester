import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  style?: React.CSSProperties
}

export function Card({ children, style }: CardProps) {
  return (
    <div
      style={{
        backgroundColor: 'var(--color-white)',
        border: 'var(--border-whisper)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-card)',
        padding: 'var(--space-5)',
        ...style,
      }}
    >
      {children}
    </div>
  )
}
