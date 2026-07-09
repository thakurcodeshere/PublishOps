import SettingsClient from './SettingsClient';

export const metadata = {
  title: 'Settings | PublishOps',
  description: 'Configure API connections, scoring weights, content preferences, and notification settings.',
};

export default function SettingsPage() {
  return <SettingsClient />;
}
