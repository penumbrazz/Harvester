import { useCallback, useState } from 'react'

import type { ApiConfig } from './types/api'
import { AppLayout } from './components/common/app-layout'
import { getNavItems } from './lib/navigation'
import { OverviewPage } from './features/overview/overview-page'
import { DashboardPage } from './features/operations/dashboard-page'
import { SourcesPage } from './features/sources/sources-page'
import { RecipesPage } from './features/recipes-schedules/recipes-page'
import { SchedulesPage } from './features/recipes-schedules/schedules-page'
import { CrawlsPage } from './features/operations/crawls-page'
import { JobsPage } from './features/operations/jobs-page'
import { PlaceholderPage } from './pages/placeholder-page'
import { loadApiConfig, saveApiConfig } from './lib/api-client'

const placeholderDescriptions: Record<string, string> = {
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

    if (activeKey === 'dashboard') {
      return <DashboardPage config={config} />
    }

    if (activeKey === 'sources') {
      return <SourcesPage config={config} />
    }

    if (activeKey === 'recipes') {
      return <RecipesPage config={config} />
    }

    if (activeKey === 'schedules') {
      return <SchedulesPage config={config} />
    }

    if (activeKey === 'crawls') {
      return <CrawlsPage config={config} />
    }

    if (activeKey === 'jobs') {
      return <JobsPage config={config} />
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
