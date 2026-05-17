interface SelectOption {
  key: string
  label: string
}

interface SelectProps {
  options: SelectOption[]
  value: string
  onChange: (value: string) => void
  id?: string
  style?: React.CSSProperties
  'data-testid'?: string
}

/**
 * Local Select wrapper compatible with animal-island-ui migration.
 * Uses options array with `key` field and direct string onChange.
 */
export function Select({
  options,
  value,
  onChange,
  id,
  style,
  'data-testid': dataTestId,
}: SelectProps) {
  return (
    <select
      id={id}
      data-testid={dataTestId}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{
        padding: '6px 12px',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border-default)',
        fontFamily: 'var(--font-family)',
        fontSize: 'var(--font-size-sm)',
        color: 'var(--color-text-primary)',
        backgroundColor: 'var(--color-bg-content)',
        outline: 'none',
        cursor: 'pointer',
        ...style,
      }}
    >
      {options.map((opt) => (
        <option key={opt.key} value={opt.key}>
          {opt.label}
        </option>
      ))}
    </select>
  )
}
