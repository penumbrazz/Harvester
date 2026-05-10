import { useCallback, useState } from 'react'

import type { ApiConfig } from './types/api'
import { AppLayout } from './components/common/app-layout'
import { getNavItems } from './lib/navigation'
import { OverviewPage } from './features/overview/overview-page'
import { PlaceholderPage } from './pages/placeholder-page'
import { loadApiConfig, saveApiConfig } from './lib/api-client'

const placeholderDescriptions: Record<string, string> = {
  sources:
    'Manage information sources for content collection. This page will be implemented in a future update.',
  recipes:
    'Configure extraction and processing recipes. This page will be implemented in a future update.',
  schedules:
    'Set up crawl schedules and monitoring rules. This page will be implemented in a future update.',
  crawls:
    'View crawl history and status. This page will be implemented in a future update.',
  jobs: 'Monitor the job queue and worker status. This page will be implemented in a future update.',
  content:
    'Browse and search the content library. This page will be implemented in a future update.',
  audit: 'Review system audit logs. This page will be implemented in a future update.',
}

export function App() {
  const navItems = getNavItems()
  const [activeKey, setActiveKey] = useState('overview')
  const [config, setConfig] = useState<ApiConfig>(loadApiConfig)

  const handleConfigChange = useCallback((newConfig: ApiConfig) => {
    saveApiConfig(newConfig)
    setConfig(newConfig)
  }, [])

  const renderPage = () => {
    if (activeKey === 'overview') {
      return <OverviewPage config={config} onConfigChange={handleConfigChange} />
    }

    const navItem = navItems.find((item) => item.key === activeKey)
    return (
      <PlaceholderPage
        title={navItem?.label || activeKey}
        description={placeholderDescriptions[activeKey] || 'Coming soon.'}
      />
    )
  }

  return (
    <AppLayout navItems={navItems} activeKey={activeKey} onNavigate={setActiveKey}>
      {renderPage()}
    </AppLayout>
  )
}
