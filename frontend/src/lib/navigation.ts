import type { NavItem } from '../components/common/sidebar'

const navItems: NavItem[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'sources', label: 'Sources' },
  { key: 'recipes', label: 'Recipes' },
  { key: 'schedules', label: 'Schedules' },
  { key: 'crawls', label: 'Crawls' },
  { key: 'jobs', label: 'Job Queue' },
  { key: 'content', label: 'Content Library' },
  { key: 'audit', label: 'Audit Log' },
]

export function getNavItems(): NavItem[] {
  return navItems
}
