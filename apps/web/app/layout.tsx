import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

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
    <html lang="en" className={`dark ${inter.variable} ${jetbrainsMono.variable}`}>
      <body className={`${inter.className} bg-background text-foreground antialiased selection:bg-primary/20 selection:text-primary`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
