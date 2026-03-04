"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { SpeechBrief, PaginatedResponse } from "@/types";

export default function SpeechesPage() {
    const router = useRouter();
    const [speeches, setSpeeches] = useState<SpeechBrief[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [total, setTotal] = useState(0);

    useEffect(() => {
        setLoading(true);
        api.speeches.list(page, 15)
            .then((data: PaginatedResponse<SpeechBrief>) => {
                setSpeeches(data.items);
                setTotalPages(data.total_pages);
                setTotal(data.total);
            })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, [page]);

    return (
        <div className="min-h-screen" dir="rtl">
            <div className="border-b border-border/40 bg-card/30 backdrop-blur-sm">
                <div className="container mx-auto px-4 py-10">
                    <div className="flex items-center gap-3 mb-3">
                        <span className="text-4xl">🎙️</span>
                        <h1 className="text-4xl font-bold font-[family-name:var(--font-amiri)]">الخطب</h1>
                    </div>
                    <p className="text-muted-foreground text-lg">خطب ومواعظ سماحة الشيخ ابن باز رحمه الله</p>
                    {!loading && <p className="text-sm text-muted-foreground mt-2 opacity-70">{total} خطبة</p>}
                </div>
            </div>

            <div className="container mx-auto px-4 py-8">
                {loading ? (
                    <div className="grid gap-4">
                        {Array.from({ length: 6 }).map((_, i) => (
                            <div key={i} className="rounded-xl border border-border/30 bg-card/40 p-6">
                                <Skeleton className="h-6 w-2/3 mb-3" />
                                <Skeleton className="h-4 w-full mb-2" />
                                <Skeleton className="h-4 w-4/5" />
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="grid gap-4">
                        {speeches.map((s) => (
                            <button
                                key={s.id}
                                onClick={() => router.push(`/speeches/${s.id}`)}
                                className="w-full text-right rounded-xl border border-border/30 bg-card/40 p-6 hover:border-amber-600/50 hover:bg-card/70 hover:shadow-lg hover:shadow-amber-900/10 transition-all duration-200 group"
                            >
                                <div className="flex items-start justify-between gap-4 mb-3">
                                    <h3 className="font-bold text-lg leading-relaxed font-[family-name:var(--font-amiri)] group-hover:text-amber-400 transition-colors">
                                        {s.title}
                                    </h3>
                                    {s.date && <span className="text-xs text-muted-foreground whitespace-nowrap pt-1 shrink-0">{s.date}</span>}
                                </div>
                                {s.text_preview && (
                                    <p className="text-sm text-muted-foreground leading-relaxed mb-4 line-clamp-2">{s.text_preview}</p>
                                )}
                                <div className="flex items-center gap-2 flex-wrap">
                                    {s.categories.slice(0, 3).map((c) => (
                                        <Badge key={c} variant="outline" className="text-xs border-amber-600/30 text-amber-400/80">{c}</Badge>
                                    ))}
                                    <span className="mr-auto text-xs text-amber-600 opacity-0 group-hover:opacity-100 transition-opacity">اقرأ الخطبة ←</span>
                                </div>
                            </button>
                        ))}
                    </div>
                )}

                {totalPages > 1 && (
                    <div className="flex justify-center gap-3 mt-10">
                        <Button variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)} className="border-border/40">السابق</Button>
                        <span className="flex items-center px-4 text-sm text-muted-foreground">{page} / {totalPages}</span>
                        <Button variant="outline" disabled={page >= totalPages} onClick={() => setPage(page + 1)} className="border-border/40">التالي</Button>
                    </div>
                )}
            </div>
        </div>
    );
}
