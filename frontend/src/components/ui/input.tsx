import type { InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
}

export function Input({ label, id, style, ...rest }: InputProps) {
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
      <input
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
          transition: 'border-color 0.15s ease',
          ...style,
        }}
        {...rest}
      />
    </div>
  )
}
