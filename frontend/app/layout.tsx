import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'WhisperScore — AI Public Speaking Coach',
  description:
    'Record your presentation and get instant AI coaching on content, voice delivery, and body language. Pinpoint exactly where you can improve.',
  keywords: ['public speaking', 'AI coach', 'presentation feedback', 'debate coach'],
  openGraph: {
    title: 'WhisperScore — AI Public Speaking Coach',
    description: 'AI-powered presentation coaching with timestamp-precise feedback.',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
