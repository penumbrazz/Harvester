import type { NavItem } from '../components/common/sidebar'

const navItems: NavItem[] = [
  { key: 'overview', label: '概览' },
  { key: 'dashboard', label: '仪表盘' },
  { key: 'sources', label: '信息源' },
  { key: 'recipes', label: '采集配方' },
  { key: 'schedules', label: '调度计划' },
  { key: 'crawls', label: '抓取任务' },
  { key: 'jobs', label: '作业队列' },
  { key: 'content', label: '内容库' },
  { key: 'audit', label: '审计日志' },
]

export function getNavItems(): NavItem[] {
  return navItems
}
