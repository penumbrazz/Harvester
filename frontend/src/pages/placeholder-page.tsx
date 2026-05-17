interface PlaceholderPageProps {
  title: string
  description: string
}

export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <div data-testid={`page-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <h2
        style={{
          fontFamily: 'var(--font-family)',
          fontSize: 'var(--font-size-2xl)',
          fontWeight: 700,
          letterSpacing: '-0.625px',
          lineHeight: 'var(--line-height-tight)',
          marginBottom: 'var(--space-3)',
          color: 'var(--color-text-primary)',
        }}
      >
        {title}
      </h2>
      <p
        style={{
          fontSize: 'var(--font-size-base)',
          color: 'var(--color-text-body)',
          lineHeight: 'var(--line-height-normal)',
        }}
      >
        {description}
      </p>
    </div>
  )
}
