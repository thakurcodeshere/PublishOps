import PipelineClient from './PipelineClient';

export const metadata = {
  title: 'Pipeline Monitor | PublishOps',
  description: 'Real-time monitoring of the 7-stage content automation pipeline with live metrics and error tracking.',
};

export default function PipelinePage() {
  return <PipelineClient />;
}
