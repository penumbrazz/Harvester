import type { SelectHTMLAttributes } from 'react'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
}

export function Select({ label, id, style, children, ...rest }: SelectProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      {label && (
        <label
          htmlFor={id}
          style={{
            fontFamily: 'var(--font-family)',
            fontSize: 'var(--font-size-sm)',
            fontWeight: 500,
            color: 'var(--color-warm-gray-500)',
          }}
        >
          {label}
        </label>
      )}
      <select
        id={id}
        style={{
          padding: '6px',
          borderRadius: 'var(--radius-sm)',
          border: 'var(--border-input)',
          fontFamily: 'var(--font-family)',
          fontSize: 'var(--font-size-base)',
          color: 'rgba(0,0,0,0.9)',
          backgroundColor: 'var(--color-white)',
          outline: 'none',
          ...style,
        }}
        {...rest}
      >
        {children}
      </select>
    </div>
  )
}
