import './globals.css';
import { ReactNode } from 'react';

export const metadata = {
  title: 'HyDE Blueprint Generator',
  description: 'Local microservices pipeline for enterprise architecture',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body suppressHydrationWarning className="bg-gray-950 text-gray-100 min-h-screen font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
