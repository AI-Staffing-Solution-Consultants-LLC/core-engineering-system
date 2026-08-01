import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Core Engineering System — Web Interface",
  description: "Control dashboard for the Core Engineering System",
};

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
