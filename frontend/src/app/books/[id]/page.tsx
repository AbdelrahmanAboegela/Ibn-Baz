"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

export default function BookDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = Number(params.id);
    const [book, setBook] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        api.books.get(id)
            .then(setBook)
            .catch(() => setError("لم يتم العثور على الكتاب"))
            .finally(() => setLoading(false));
    }, [id]);

    if (loading) return (
        <div className="container mx-auto px-4 py-12 max-w-xl" dir="rtl">
            <Skeleton className="h-8 w-3/4 mb-4" />
            <Skeleton className="h-12 w-full rounded-xl" />
        </div>
    );

    if (error || !book) return (
        <div className="container mx-auto px-4 py-12 text-center" dir="rtl">
            <p className="text-muted-foreground mb-4">{error || "خطأ غير معروف"}</p>
            <Button variant="outline" onClick={() => router.back()}>رجوع</Button>
        </div>
    );

    return (
        <div className="min-h-screen" dir="rtl">
            <div className="border-b border-border/40 bg-card/30">
                <div className="container mx-auto px-4 py-8 max-w-xl">
                    <Button variant="ghost" size="sm" onClick={() => router.back()} className="mb-4 text-muted-foreground">
                        ← الكتب
                    </Button>
                    <div className="flex items-center gap-2 mb-2">
                        <span className="text-3xl">📚</span>
                        <span className="text-sm text-muted-foreground">كتاب</span>
                    </div>
                    <h1 className="text-3xl font-bold font-[family-name:var(--font-amiri)] leading-relaxed">
                        {book.title}
                    </h1>
                </div>
            </div>

            <div className="container mx-auto px-4 py-10 max-w-xl">
                <div className="rounded-2xl border border-border/30 bg-card/40 p-8 text-center space-y-6">
                    <div className="text-6xl">📖</div>
                    <p className="text-muted-foreground text-sm">
                        هذا الكتاب متاح للتحميل بصيغة PDF
                    </p>

                    {book.pdf_url ? (
                        <a
                            href={book.pdf_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 px-8 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold transition-colors"
                        >
                            ⬇️ تحميل PDF
                        </a>
                    ) : (
                        <p className="text-muted-foreground text-sm">رابط التحميل غير متوفر</p>
                    )}

                    {book.url && (
                        <div>
                            <a
                                href={book.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-muted-foreground hover:text-foreground underline"
                            >
                                عرض على الموقع الأصلي ↗
                            </a>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
