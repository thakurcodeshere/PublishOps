import './globals.css';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';

export const metadata = {
  title: 'PublishOps | Autonomous Content Engine',
  description: 'AI-powered 7-stage content automation pipeline — discover, score, script, voice, assemble, review, and publish across all platforms.',
  keywords: 'content automation, AI pipeline, social media, publishing',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div className="dashboard-layout">
          <Sidebar />
          <div className="dashboard-main">
            <Header />
            <main className="dashboard-content">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
