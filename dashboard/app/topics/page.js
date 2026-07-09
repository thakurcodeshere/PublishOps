import TopicsClient from './TopicsClient';

export const metadata = {
  title: 'Topic Explorer | PublishOps',
  description: 'Explore, score, and manage trending topics with composite scoring and radar chart breakdowns.',
};

export default function TopicsPage() {
  return <TopicsClient />;
}
