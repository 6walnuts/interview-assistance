import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Interview Coach",
  description: "Learn, practice, mock interview, review — and close the loop.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
