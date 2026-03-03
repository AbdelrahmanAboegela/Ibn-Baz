"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { BookItem } from "@/types";

export default function BooksPage() {
    const [books, setBooks] = useState<BookItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.books.list()
            .then(setBooks)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold mb-2 font-[family-name:var(--font-amiri)]">📚 كتب الشيخ ابن باز</h1>
            <p className="text-muted-foreground mb-8">مؤلفات ورسائل سماحة الشيخ رحمه الله</p>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {loading ? (
                    Array.from({ length: 6 }).map((_, i) => (
                        <Card key={i} className="border-border/40"><CardContent className="pt-6"><Skeleton className="h-6 w-3/4 mb-4" /><Skeleton className="h-10 w-full" /></CardContent></Card>
                    ))
                ) : (
                    books.map((book) => (
                        <Card key={book.id} className="border-border/40 hover:border-emerald-600/40 transition-all">
                            <CardContent className="pt-6 text-center">
                                <div className="text-4xl mb-4">📕</div>
                                <h3 className="font-bold mb-4">{book.title}</h3>
                                <div className="flex gap-2 justify-center">
                                    {book.pdf_url && (
                                        <a href={book.pdf_url} target="_blank" rel="noopener noreferrer">
                                            <Button variant="default" size="sm" className="bg-emerald-600 hover:bg-emerald-700">
                                                📥 تحميل PDF
                                            </Button>
                                        </a>
                                    )}
                                    {book.url && (
                                        <a href={book.url} target="_blank" rel="noopener noreferrer">
                                            <Button variant="outline" size="sm">🔗 المصدر</Button>
                                        </a>
                                    )}
                                </div>
                            </CardContent>
                        </Card>
                    ))
                )}
            </div>
        </div>
    );
}
