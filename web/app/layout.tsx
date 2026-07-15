import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Eworks Operator Console',
  description: 'Read-only operator dashboard over eworks.db',
};

/**
 * Root layout stub. Empty shell — no data fetching, no nav yet.
 * Story 11.3 (Home & Navigation Shell) builds the navigation on top of this.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
