"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { DashboardStats } from "@/types";

const STAT_ITEMS = [
  { key: "total_fatwas" as const, label: "فتوى", icon: "📜" },
  { key: "total_articles" as const, label: "مقال", icon: "📝" },
  { key: "total_books" as const, label: "كتاب", icon: "📚" },
  { key: "total_speeches" as const, label: "خطبة", icon: "🎤" },
  { key: "total_discussions" as const, label: "محاضرة", icon: "💬" },
];

const QUICK_LINKS = [
  { href: "/fatwas", label: "تصفح الفتاوى", icon: "📜", desc: "أكثر من 24 ألف فتوى" },
  { href: "/articles", label: "المقالات", icon: "📝", desc: "مقالات علمية" },
  { href: "/books", label: "الكتب", icon: "📚", desc: "مؤلفات الشيخ" },
  { href: "/chat", label: "اسأل الشيخ", icon: "🤖", desc: "محرك بحث ذكي" },
];

export default function HomePage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.stats().then(setStats).catch(console.error);
  }, []);

  return (
    <div className="flex flex-col">
      {/* ━━━ Hero ━━━ */}
      <section className="relative overflow-hidden border-b border-border/40">
        {/* Islamic geometric pattern overlay */}
        <div className="absolute inset-0 opacity-[0.03]" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }} />

        <div className="container mx-auto px-4 py-20 text-center relative">
          {/* Bismillah */}
          <p className="text-emerald-500/80 font-[family-name:var(--font-amiri)] text-lg mb-4">
            بسم الله الرحمن الرحيم
          </p>

          <h1 className="text-4xl md:text-6xl font-bold mb-4 font-[family-name:var(--font-amiri)]">
            مكتبة الشيخ ابن باز
          </h1>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto mb-2">
            سماحة الشيخ عبد العزيز بن عبد الله بن باز رحمه الله
          </p>
          <p className="text-muted-foreground/60 text-sm mb-8">
            المفتي العام للمملكة العربية السعودية ورئيس هيئة كبار العلماء
          </p>

          {/* Search */}
          <div className="max-w-xl mx-auto flex gap-2">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="ابحث في فتاوى الشيخ ابن باز..."
              className="text-right h-12"
              onKeyDown={(e) => {
                if (e.key === "Enter" && search.trim()) {
                  window.location.href = `/fatwas?search=${encodeURIComponent(search)}`;
                }
              }}
            />
            <Link href={search ? `/fatwas?search=${encodeURIComponent(search)}` : "/fatwas"}>
              <Button className="h-12 bg-emerald-600 hover:bg-emerald-700 px-6">
                بحث
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* ━━━ Stats ━━━ */}
      <section className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {STAT_ITEMS.map((item) => (
            <Card key={item.key} className="text-center border-border/40 bg-card/50">
              <CardContent className="pt-6">
                <div className="text-3xl mb-2">{item.icon}</div>
                {stats ? (
                  <div className="text-2xl font-bold text-emerald-400">
                    {stats[item.key]?.toLocaleString("ar-EG")}
                  </div>
                ) : (
                  <Skeleton className="h-8 w-16 mx-auto" />
                )}
                <div className="text-sm text-muted-foreground mt-1">{item.label}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* ━━━ Sheikh Biography ━━━ */}
      <section className="container mx-auto px-4 pb-12">
        <Card className="border-emerald-600/20 bg-emerald-950/20">
          <CardContent className="pt-6 md:flex md:gap-8">
            <div className="flex-shrink-0 text-center mb-6 md:mb-0">
              <div className="w-32 h-32 mx-auto rounded-full bg-emerald-900/40 border-2 border-emerald-600/30 flex items-center justify-center text-5xl font-[family-name:var(--font-amiri)]">
                ابن باز
              </div>
            </div>
            <div className="space-y-3 text-right">
              <h2 className="text-xl font-bold font-[family-name:var(--font-amiri)]">
                سماحة الشيخ عبد العزيز بن عبد الله بن باز
              </h2>
              <p className="text-muted-foreground text-sm leading-relaxed">
                ولد رحمه الله في الرياض عام ١٣٣٠هـ، وحفظ القرآن الكريم قبل البلوغ،
                وأصيب بمرض في عينيه عام ١٣٤٦هـ ثم فقد بصره بالكامل عام ١٣٥٠هـ.
                تولى رئاسة الجامعة الإسلامية بالمدينة المنورة، ثم عُيّن رئيساً لإدارة البحوث
                العلمية والإفتاء، ثم المفتي العام للمملكة العربية السعودية ورئيس هيئة كبار العلماء.
              </p>
              <p className="text-muted-foreground text-sm leading-relaxed">
                عُرف رحمه الله بغزارة علمه وتواضعه ورحمته بالناس، وكان من أبرز المدافعين
                عن عقيدة التوحيد والسنة النبوية. توفي رحمه الله عام ١٤٢٠هـ.
              </p>
              <div className="flex gap-2 flex-wrap">
                <Badge variant="outline" className="text-emerald-400 border-emerald-600/30">التوحيد</Badge>
                <Badge variant="outline" className="text-emerald-400 border-emerald-600/30">الفقه</Badge>
                <Badge variant="outline" className="text-emerald-400 border-emerald-600/30">العقيدة</Badge>
                <Badge variant="outline" className="text-emerald-400 border-emerald-600/30">الحديث</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* ━━━ Quick Links ━━━ */}
      <section className="container mx-auto px-4 pb-16">
        <h2 className="text-2xl font-bold mb-6">تصفح المكتبة</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {QUICK_LINKS.map((link) => (
            <Link key={link.href} href={link.href}>
              <Card className="h-full border-border/40 hover:border-emerald-600/40 transition-all hover:shadow-lg hover:shadow-emerald-950/20 cursor-pointer group">
                <CardContent className="pt-6 text-center">
                  <div className="text-4xl mb-3 group-hover:scale-110 transition-transform">
                    {link.icon}
                  </div>
                  <h3 className="font-bold text-lg mb-1">{link.label}</h3>
                  <p className="text-sm text-muted-foreground">{link.desc}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
