import type { ButtonHTMLAttributes } from 'react'

import type { Variant } from '../../types/style'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
}

const variantStyles: Record<Variant, React.CSSProperties> = {
  primary: {
    backgroundColor: 'var(--color-notion-blue)',
    color: 'var(--color-white)',
    border: '1px solid transparent',
  },
  secondary: {
    backgroundColor: 'rgba(0,0,0,0.05)',
    color: 'var(--color-primary-text)',
    border: '1px solid transparent',
  },
  ghost: {
    backgroundColor: 'transparent',
    color: 'var(--color-primary-text)',
    border: 'none',
  },
}

export function Button({ variant = 'primary', style, children, ...rest }: ButtonProps) {
  return (
    <button
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '8px 16px',
        borderRadius: 'var(--radius-sm)',
        fontFamily: 'var(--font-family)',
        fontSize: 'var(--font-size-sm)',
        fontWeight: 600,
        lineHeight: 1.33,
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        ...variantStyles[variant],
        ...style,
      }}
      {...rest}
    >
      {children}
    </button>
  )
}
