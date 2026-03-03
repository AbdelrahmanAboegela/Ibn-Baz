import type { Metadata } from "next";
import { Amiri, Noto_Kufi_Arabic } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

const notoKufi = Noto_Kufi_Arabic({
  subsets: ["arabic"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-kufi",
});

const amiri = Amiri({
  subsets: ["arabic"],
  weight: ["400", "700"],
  variable: "--font-amiri",
});

export const metadata: Metadata = {
  title: "مكتبة الشيخ ابن باز",
  description:
    "مكتبة شاملة لفتاوى ومقالات وكتب وخطب سماحة الشيخ عبد العزيز بن عبد الله بن باز رحمه الله",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ar" dir="rtl" className="dark">
      <body
        className={`${notoKufi.variable} ${amiri.variable} font-sans antialiased bg-background text-foreground min-h-screen`}
      >
        <Header />
        <main className="min-h-[calc(100vh-8rem)]">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
