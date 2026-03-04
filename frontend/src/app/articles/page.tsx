"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { ArticleBrief, PaginatedResponse } from "@/types";

export default function ArticlesPage() {
    const router = useRouter();
    const [articles, setArticles] = useState<ArticleBrief[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [total, setTotal] = useState(0);

    useEffect(() => {
        setLoading(true);
        api.articles.list(page, 15)
            .then((data: PaginatedResponse<ArticleBrief>) => {
                setArticles(data.items);
                setTotalPages(data.total_pages);
                setTotal(data.total);
            })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, [page]);

    return (
        <div className="min-h-screen" dir="rtl">
            {/* Header */}
            <div className="border-b border-border/40 bg-card/30 backdrop-blur-sm">
                <div className="container mx-auto px-4 py-10">
                    <div className="flex items-center gap-3 mb-3">
                        <span className="text-4xl">📝</span>
                        <h1 className="text-4xl font-bold font-[family-name:var(--font-amiri)]">
                            المقالات
                        </h1>
                    </div>
                    <p className="text-muted-foreground text-lg">
                        مقالات ورسائل علمية لسماحة الشيخ ابن باز رحمه الله
                    </p>
                    {!loading && (
                        <p className="text-sm text-muted-foreground mt-2 opacity-70">
                            {total} مقالة
                        </p>
                    )}
                </div>
            </div>

            <div className="container mx-auto px-4 py-8">
                {loading ? (
                    <div className="grid gap-4">
                        {Array.from({ length: 6 }).map((_, i) => (
                            <div key={i} className="rounded-xl border border-border/30 bg-card/40 p-6">
                                <Skeleton className="h-6 w-2/3 mb-3" />
                                <Skeleton className="h-4 w-full mb-2" />
                                <Skeleton className="h-4 w-4/5 mb-4" />
                                <div className="flex gap-2">
                                    <Skeleton className="h-5 w-20 rounded-full" />
                                    <Skeleton className="h-5 w-24 rounded-full" />
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="grid gap-4">
                        {articles.map((a) => (
                            <button
                                key={a.id}
                                onClick={() => router.push(`/articles/${a.id}`)}
                                className="w-full text-right rounded-xl border border-border/30 bg-card/40 p-6 hover:border-emerald-600/50 hover:bg-card/70 hover:shadow-lg hover:shadow-emerald-900/10 transition-all duration-200 group"
                            >
                                <div className="flex items-start justify-between gap-4 mb-3">
                                    <h3 className="font-bold text-lg leading-relaxed font-[family-name:var(--font-amiri)] text-foreground group-hover:text-emerald-400 transition-colors">
                                        {a.title}
                                    </h3>
                                    {a.date && (
                                        <span className="text-xs text-muted-foreground whitespace-nowrap pt-1 shrink-0">
                                            {a.date}
                                        </span>
                                    )}
                                </div>

                                {a.text_preview && (
                                    <p className="text-sm text-muted-foreground leading-relaxed mb-4 line-clamp-2">
                                        {a.text_preview}
                                    </p>
                                )}

                                <div className="flex items-center gap-2 flex-wrap">
                                    {a.categories.slice(0, 3).map((c) => (
                                        <Badge key={c} variant="outline" className="text-xs border-emerald-600/30 text-emerald-400/80">
                                            {c}
                                        </Badge>
                                    ))}
                                    {a.source_ref && (
                                        <Badge variant="secondary" className="text-xs opacity-60">
                                            {a.source_ref.slice(0, 40)}{a.source_ref.length > 40 ? "..." : ""}
                                        </Badge>
                                    )}
                                    <span className="mr-auto text-xs text-emerald-600 opacity-0 group-hover:opacity-100 transition-opacity">
                                        اقرأ المقالة ←
                                    </span>
                                </div>
                            </button>
                        ))}
                    </div>
                )}

                {totalPages > 1 && (
                    <div className="flex justify-center gap-3 mt-10">
                        <Button
                            variant="outline"
                            disabled={page <= 1}
                            onClick={() => setPage(page - 1)}
                            className="border-border/40"
                        >
                            السابق
                        </Button>
                        <span className="flex items-center px-4 text-sm text-muted-foreground">
                            {page} / {totalPages}
                        </span>
                        <Button
                            variant="outline"
                            disabled={page >= totalPages}
                            onClick={() => setPage(page + 1)}
                            className="border-border/40"
                        >
                            التالي
                        </Button>
                    </div>
                )}
            </div>
        </div>
    );
}
