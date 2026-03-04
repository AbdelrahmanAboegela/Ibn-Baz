"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { BookItem } from "@/types";

export default function BooksPage() {
    const router = useRouter();
    const [books, setBooks] = useState<BookItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.books.list()
            .then(setBooks)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="min-h-screen" dir="rtl">
            <div className="border-b border-border/40 bg-card/30 backdrop-blur-sm">
                <div className="container mx-auto px-4 py-10">
                    <div className="flex items-center gap-3 mb-3">
                        <span className="text-4xl">📚</span>
                        <h1 className="text-4xl font-bold font-[family-name:var(--font-amiri)]">كتب الشيخ ابن باز</h1>
                    </div>
                    <p className="text-muted-foreground text-lg">مؤلفات ورسائل سماحة الشيخ رحمه الله</p>
                    {!loading && <p className="text-sm text-muted-foreground mt-2 opacity-70">{books.length} كتاب</p>}
                </div>
            </div>

            <div className="container mx-auto px-4 py-8">
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {Array.from({ length: 9 }).map((_, i) => (
                            <div key={i} className="rounded-xl border border-border/30 bg-card/40 p-6">
                                <Skeleton className="h-10 w-10 mx-auto rounded-full mb-4" />
                                <Skeleton className="h-5 w-4/5 mx-auto mb-3" />
                                <Skeleton className="h-9 w-32 mx-auto rounded-xl" />
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {books.map((book) => (
                            <button
                                key={book.id}
                                onClick={() => router.push(`/books/${book.id}`)}
                                className="w-full text-center rounded-xl border border-border/30 bg-card/40 p-6 hover:border-emerald-600/50 hover:bg-card/70 hover:shadow-lg hover:shadow-emerald-900/10 transition-all duration-200 group flex flex-col items-center gap-3"
                            >
                                <div className="text-4xl group-hover:scale-110 transition-transform">📕</div>
                                <h3 className="font-bold text-sm leading-relaxed font-[family-name:var(--font-amiri)] group-hover:text-emerald-400 transition-colors line-clamp-3">
                                    {book.title}
                                </h3>
                                <div className="flex gap-2 mt-auto pt-2">
                                    {book.pdf_url && (
                                        <span
                                            onClick={(e) => { e.stopPropagation(); window.open(book.pdf_url, "_blank"); }}
                                            className="px-3 py-1.5 rounded-lg bg-emerald-600/80 hover:bg-emerald-500 text-white text-xs font-bold transition-colors"
                                        >
                                            ⬇️ PDF
                                        </span>
                                    )}
                                    {book.url && (
                                        <span className="px-3 py-1.5 rounded-lg border border-border/50 text-xs text-muted-foreground hover:text-foreground transition-colors">
                                            عرض
                                        </span>
                                    )}
                                </div>
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
