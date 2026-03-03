"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { SpeechBrief, PaginatedResponse } from "@/types";

export default function SpeechesPage() {
    const [speeches, setSpeeches] = useState<SpeechBrief[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);

    useEffect(() => {
        setLoading(true);
        api.speeches.list(page)
            .then((data: PaginatedResponse<SpeechBrief>) => {
                setSpeeches(data.items);
                setTotalPages(data.total_pages);
            })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, [page]);

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold mb-2 font-[family-name:var(--font-amiri)]">🎤 الخطب</h1>
            <p className="text-muted-foreground mb-8">خطب ومواعظ سماحة الشيخ ابن باز رحمه الله</p>

            <div className="grid gap-4">
                {loading ? (
                    Array.from({ length: 5 }).map((_, i) => (
                        <Card key={i} className="border-border/40"><CardContent className="pt-6"><Skeleton className="h-6 w-3/4 mb-2" /><Skeleton className="h-4 w-full" /></CardContent></Card>
                    ))
                ) : (
                    speeches.map((s) => (
                        <Card key={s.id} className="border-border/40 hover:border-emerald-600/40 transition-all">
                            <CardContent className="pt-6">
                                <h3 className="font-bold text-lg mb-2">{s.title}</h3>
                                <p className="text-sm text-muted-foreground line-clamp-3 mb-3">{s.text_preview}</p>
                                <div className="flex gap-2 flex-wrap">
                                    {s.categories.map((c) => <Badge key={c} variant="outline" className="text-xs">{c}</Badge>)}
                                    {s.date && <Badge variant="secondary" className="text-xs">{s.date}</Badge>}
                                </div>
                            </CardContent>
                        </Card>
                    ))
                )}
            </div>

            {totalPages > 1 && (
                <div className="flex justify-center gap-2 mt-8">
                    <Button variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>السابق</Button>
                    <span className="flex items-center px-4 text-sm text-muted-foreground">صفحة {page} من {totalPages}</span>
                    <Button variant="outline" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>التالي</Button>
                </div>
            )}
        </div>
    );
}
