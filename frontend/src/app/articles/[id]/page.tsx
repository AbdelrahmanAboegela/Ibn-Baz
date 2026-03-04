"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { QuranBlock } from "@/components/content/QuranBlock";

export default function ArticleDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = Number(params.id);
    const [article, setArticle] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        api.articles.get(id)
            .then(setArticle)
            .catch(() => setError("لم يتم العثور على المقالة"))
            .finally(() => setLoading(false));
    }, [id]);

    if (loading) return (
        <div className="container mx-auto px-4 py-12 max-w-3xl" dir="rtl">
            <Skeleton className="h-8 w-3/4 mb-4" />
            <Skeleton className="h-4 w-full mb-2" /><Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-4/5" />
        </div>
    );

    if (error || !article) return (
        <div className="container mx-auto px-4 py-12 text-center" dir="rtl">
            <p className="text-muted-foreground mb-4">{error || "خطأ غير معروف"}</p>
            <Button variant="outline" onClick={() => router.back()}>رجوع</Button>
        </div>
    );

    return (
        <div className="min-h-screen" dir="rtl">
            <div className="border-b border-border/40 bg-card/30">
                <div className="container mx-auto px-4 py-8 max-w-3xl">
                    <Button variant="ghost" size="sm" onClick={() => router.back()} className="mb-4 text-muted-foreground">
                        ← المقالات
                    </Button>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-2xl">📝</span>
                        <span className="text-sm text-muted-foreground">مقالة</span>
                        {article.date && <span className="text-sm text-muted-foreground">• {article.date}</span>}
                    </div>
                    <h1 className="text-3xl font-bold font-[family-name:var(--font-amiri)] leading-relaxed mb-4">
                        {article.title}
                    </h1>
                    {article.categories?.length > 0 && (
                        <div className="flex gap-2 flex-wrap">
                            {article.categories.map((c: string) => (
                                <Badge key={c} variant="outline" className="border-emerald-600/30 text-emerald-400/80 text-xs">
                                    {c}
                                </Badge>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="container mx-auto px-4 py-8 max-w-3xl">
                <div className="prose prose-invert prose-lg max-w-none">
                    <div
                        className="text-foreground/90 leading-[2.1] text-lg font-[family-name:var(--font-amiri)] whitespace-pre-line"
                        style={{ lineHeight: "2.2" }}
                    >
                        {article.text}
                    </div>
                </div>

                {/* Quran Citations — extracted from text */}
                {article.quran_citations?.length > 0 && (
                    <div className="mt-8 p-5 rounded-xl border border-emerald-600/20 bg-emerald-950/10">
                        <QuranBlock citations={article.quran_citations} />
                    </div>
                )}

                && (
                <div className="mt-8 p-4 rounded-lg border border-border/30 bg-card/30">
                    <p className="text-sm text-muted-foreground">
                        <span className="font-bold text-foreground/70">المصدر: </span>
                        {article.source_ref}
                    </p>
                </div>
                )}

                {article.url && (
                    <div className="mt-4 text-center">
                        <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-emerald-500 hover:text-emerald-400 underline"
                        >
                            المصدر الأصلي ↗
                        </a>
                    </div>
                )}
            </div>
        </div>
    );
}
