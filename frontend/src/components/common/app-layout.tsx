import type { ReactNode } from 'react'

import { Sidebar } from './sidebar'
import type { NavItem } from './sidebar'

interface AppLayoutProps {
  navItems: NavItem[]
  activeKey: string
  onNavigate: (key: string) => void
  children: ReactNode
}

export function AppLayout({
  navItems,
  activeKey,
  onNavigate,
  children,
}: AppLayoutProps) {
  return (
    <div data-testid="app-layout" style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar items={navItems} activeKey={activeKey} onNavigate={onNavigate} />
      <main
        style={{
          flex: 1,
          padding: 'var(--space-6)',
          maxWidth: 'var(--content-max-width)',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {children}
      </main>
    </div>
  )
}
