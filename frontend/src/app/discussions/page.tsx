"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { DiscussionBrief, PaginatedResponse } from "@/types";

export default function DiscussionsPage() {
    const router = useRouter();
    const [discussions, setDiscussions] = useState<DiscussionBrief[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [total, setTotal] = useState(0);

    useEffect(() => {
        setLoading(true);
        api.discussions.list(page, 15)
            .then((data: PaginatedResponse<DiscussionBrief>) => {
                setDiscussions(data.items);
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
                        <span className="text-4xl">💬</span>
                        <h1 className="text-4xl font-bold font-[family-name:var(--font-amiri)]">المناقشات</h1>
                    </div>
                    <p className="text-muted-foreground text-lg">محاضرات ودروس علمية لسماحة الشيخ ابن باز رحمه الله</p>
                    {!loading && <p className="text-sm text-muted-foreground mt-2 opacity-70">{total} مناقشة</p>}
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
                        {discussions.map((d) => (
                            <button
                                key={d.id}
                                onClick={() => router.push(`/discussions/${d.id}`)}
                                className="w-full text-right rounded-xl border border-border/30 bg-card/40 p-6 hover:border-blue-600/50 hover:bg-card/70 hover:shadow-lg hover:shadow-blue-900/10 transition-all duration-200 group"
                            >
                                <h3 className="font-bold text-lg leading-relaxed mb-3 font-[family-name:var(--font-amiri)] group-hover:text-blue-400 transition-colors">
                                    {d.title}
                                </h3>
                                {d.text_preview && (
                                    <p className="text-sm text-muted-foreground leading-relaxed mb-4 line-clamp-2">{d.text_preview}</p>
                                )}
                                <div className="flex items-center gap-2 flex-wrap">
                                    {d.categories.slice(0, 3).map((c) => (
                                        <Badge key={c} variant="outline" className="text-xs border-blue-600/30 text-blue-400/80">{c}</Badge>
                                    ))}
                                    <span className="mr-auto text-xs text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity">اقرأ المناقشة ←</span>
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
