"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

export default function AudiosPage() {
    const [audios, setAudios] = useState<any[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const PER_PAGE = 24;

    useEffect(() => {
        setLoading(true);
        api.audios.list(page, PER_PAGE)
            .then((res: any) => { setAudios(res.items); setTotal(res.total); })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, [page]);

    const totalPages = Math.ceil(total / PER_PAGE);

    return (
        <div className="min-h-screen" dir="rtl">
            {/* Header */}
            <div className="border-b border-border/40 bg-card/30">
                <div className="container mx-auto px-4 py-8">
                    <div className="flex items-center gap-3 mb-2">
                        <span className="text-4xl">🎧</span>
                        <div>
                            <h1 className="text-3xl font-bold font-[family-name:var(--font-amiri)]">الأشرطة والتسجيلات</h1>
                            <p className="text-sm text-muted-foreground mt-1">{total.toLocaleString("ar-EG")} تسجيل صوتي</p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="container mx-auto px-4 py-8">
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {Array.from({ length: 9 }).map((_, i) => (
                            <Card key={i} className="border-border/40">
                                <CardContent className="pt-6 space-y-3">
                                    <Skeleton className="h-5 w-3/4" />
                                    <Skeleton className="h-4 w-full" />
                                    <Skeleton className="h-8 w-full" />
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                ) : audios.length === 0 ? (
                    <div className="text-center py-20 text-muted-foreground">
                        <p className="text-5xl mb-4">🎧</p>
                        <p className="text-lg">جاري جلب التسجيلات الصوتية...</p>
                        <p className="text-sm mt-2">الرجاء تشغيل سكريبت <code className="bg-muted px-1 rounded">04_load_content.py</code> بعد اكتمال السكراير</p>
                    </div>
                ) : (
                    <>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
                            {audios.map((audio) => (
                                <Link key={audio.id} href={`/audios/${audio.id}`}>
                                    <Card className="border-border/40 hover:border-purple-600/40 transition-all cursor-pointer group h-full">
                                        <CardContent className="pt-5 flex flex-col h-full">
                                            <div className="flex items-start gap-2 mb-3">
                                                <span className="text-xl mt-0.5 shrink-0">{audio.has_audio ? "🎧" : "📜"}</span>
                                                <h3 className="font-bold text-base group-hover:text-purple-400 transition-colors leading-snug line-clamp-2">
                                                    {audio.title}
                                                </h3>
                                            </div>
                                            {audio.transcript_preview && (
                                                <p className="text-xs text-muted-foreground line-clamp-2 mb-3 flex-1">
                                                    {audio.transcript_preview}
                                                </p>
                                            )}
                                            <div className="flex items-center justify-between mt-auto">
                                                {audio.has_audio ? (
                                                    <Badge className="bg-purple-700/40 text-purple-300 text-xs border-0">
                                                        🎵 يتوفر صوت
                                                    </Badge>
                                                ) : (
                                                    <Badge variant="outline" className="text-xs text-muted-foreground">
                                                        نص فقط
                                                    </Badge>
                                                )}
                                                {audio.categories?.[0] && (
                                                    <span className="text-xs text-muted-foreground truncate max-w-[120px]">{audio.categories[0]}</span>
                                                )}
                                            </div>
                                        </CardContent>
                                    </Card>
                                </Link>
                            ))}
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="flex justify-center gap-2">
                                <Button variant="outline" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>السابق</Button>
                                <span className="flex items-center px-4 text-sm text-muted-foreground">
                                    {page} / {totalPages}
                                </span>
                                <Button variant="outline" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>التالي</Button>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
