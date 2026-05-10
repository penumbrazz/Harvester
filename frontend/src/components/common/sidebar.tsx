export interface NavItem {
  key: string
  label: string
}

interface SidebarProps {
  items: NavItem[]
  activeKey: string
  onNavigate: (key: string) => void
}

export function Sidebar({ items, activeKey, onNavigate }: SidebarProps) {
  return (
    <aside
      data-testid="sidebar"
      style={{
        width: 'var(--sidebar-width)',
        minHeight: '100vh',
        backgroundColor: 'var(--color-warm-white)',
        borderRight: 'var(--border-whisper)',
        padding: 'var(--space-4) 0',
        flexShrink: 0,
      }}
    >
      <div
        style={{
          padding: '0 var(--space-4) var(--space-5)',
          borderBottom: 'var(--border-whisper)',
          marginBottom: 'var(--space-2)',
        }}
      >
        <h1
          style={{
            fontFamily: 'var(--font-family)',
            fontSize: 'var(--font-size-lg)',
            fontWeight: 700,
            color: 'var(--color-primary-text)',
            letterSpacing: '-0.125px',
          }}
        >
          Harvester
        </h1>
      </div>
      <nav>
        {items.map((item) => (
          <button
            key={item.key}
            data-testid={`nav-${item.key}`}
            onClick={() => onNavigate(item.key)}
            style={{
              display: 'block',
              width: '100%',
              textAlign: 'left',
              padding: '10px var(--space-4)',
              border: 'none',
              backgroundColor:
                activeKey === item.key ? 'rgba(0,0,0,0.05)' : 'transparent',
              color:
                activeKey === item.key
                  ? 'var(--color-primary-text)'
                  : 'var(--color-warm-gray-500)',
              fontFamily: 'var(--font-family)',
              fontSize: 'var(--font-size-sm)',
              fontWeight: activeKey === item.key ? 600 : 500,
              cursor: 'pointer',
              transition: 'background-color 0.15s ease',
            }}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  )
}
