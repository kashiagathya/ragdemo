import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "RAG AI Chat Studio", description: "See retrieval augmented generation execute in real time." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
