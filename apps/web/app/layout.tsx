import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Road Intelligence Platform | Infrastructure Condition & Pothole Operations",
  description: "Enterprise Road Infrastructure Condition Monitoring & Pothole Lifecycle Intelligence System",
  icons: {
    icon: "/favicon.ico",
  },
};

import { Providers } from "@/components/providers";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        {/* Inter (interface) and JetBrains Mono (IDs, coordinates). Loaded in the browser, so the
            production build no longer downloads fonts. Families are named in app/globals.css. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
      </head>
      <body className="font-sans bg-background text-foreground antialiased selection:bg-white/20 selection:text-white">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
