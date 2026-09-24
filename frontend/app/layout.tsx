import type { Metadata } from "next";
import localFont from "next/font/local";
import { AuthProvider } from "@/lib/auth-context";
import { AppShell } from "@/components/AppShell";
import "@/app/globals.css";

const plexSans = localFont({
  src: "./fonts/ibm-plex-sans-latin-variable.woff2",
  weight: "400 700",
  variable: "--font-plex-sans",
  display: "swap",
});

const plexMono = localFont({
  src: [
    { path: "./fonts/ibm-plex-mono-latin-400.woff2", weight: "400", style: "normal" },
    { path: "./fonts/ibm-plex-mono-latin-500.woff2", weight: "500", style: "normal" },
    { path: "./fonts/ibm-plex-mono-latin-600.woff2", weight: "600", style: "normal" },
  ],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Patio Esperanza",
  description: "Gestión de patio de contenedores",
  icons: { apple: "/favicon-180.png" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${plexSans.variable} ${plexMono.variable}`}>
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
