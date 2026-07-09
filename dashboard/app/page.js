import DashboardClient from './DashboardClient';

export const metadata = {
  title: 'Dashboard | PublishOps',
  description: 'Monitor your autonomous content pipeline, view performance metrics, and manage scheduled posts.',
};

export default function DashboardPage() {
  return <DashboardClient />;
}
