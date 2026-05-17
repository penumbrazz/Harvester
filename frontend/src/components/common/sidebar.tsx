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
        backgroundColor: 'var(--color-bg-content)',
        borderRight: 'var(--border-default)',
        padding: 'var(--space-4) 0',
        flexShrink: 0,
      }}
    >
      <div
        style={{
          padding: '0 var(--space-4) var(--space-5)',
          borderBottom: 'var(--border-default)',
          marginBottom: 'var(--space-2)',
        }}
      >
        <h1
          style={{
            fontFamily: 'var(--font-family)',
            fontSize: 'var(--font-size-lg)',
            fontWeight: 700,
            color: 'var(--color-text-primary)',
          }}
        >
          Harvester
        </h1>
      </div>
      <nav>
        {items.map((item) => {
          const isActive = activeKey === item.key
          return (
            <button
              key={item.key}
              data-testid={`nav-${item.key}`}
              onClick={() => onNavigate(item.key)}
              style={{
                display: 'block',
                width: 'calc(100% - 16px)',
                textAlign: 'left',
                padding: '10px var(--space-4)',
                margin: '2px 8px',
                border: 'none',
                borderRadius: '12px',
                backgroundColor: isActive ? 'var(--color-bg-active)' : 'transparent',
                color: isActive
                  ? 'var(--color-text-primary)'
                  : 'var(--color-text-body)',
                fontFamily: 'var(--font-family)',
                fontSize: 'var(--font-size-sm)',
                fontWeight: isActive ? 700 : 500,
                cursor: 'pointer',
                transition: 'background-color 0.15s ease',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'var(--color-bg-hover)'
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'transparent'
                }
              }}
            >
              {item.label}
            </button>
          )
        })}
      </nav>
    </aside>
  )
}
