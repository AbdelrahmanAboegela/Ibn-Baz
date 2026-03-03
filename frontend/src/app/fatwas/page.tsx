"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { FatwaBrief, PaginatedResponse } from "@/types";

function FatwasContent() {
    const searchParams = useSearchParams();
    const initialSearch = searchParams.get("search") || "";

    const [fatwas, setFatwas] = useState<FatwaBrief[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState(initialSearch);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [total, setTotal] = useState(0);

    const fetchFatwas = async (p: number, q?: string) => {
        setLoading(true);
        try {
            const data: PaginatedResponse<FatwaBrief> = await api.fatwas.list(p, 20, undefined, q || undefined);
            setFatwas(data.items);
            setTotalPages(data.total_pages);
            setTotal(data.total);
        } catch (err) {
            console.error("Failed to load fatwas:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchFatwas(page, search);
    }, [page]);

    const handleSearch = () => {
        setPage(1);
        fetchFatwas(1, search);
    };

    return (
        <div className="container mx-auto px-4 py-8">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold mb-2 font-[family-name:var(--font-amiri)]">
                    📜 فتاوى الشيخ ابن باز
                </h1>
                <p className="text-muted-foreground">
                    {total > 0 ? `${total.toLocaleString("ar-EG")} فتوى` : "جاري التحميل..."}
                </p>
            </div>

            {/* Search */}
            <div className="flex gap-2 mb-6 max-w-xl">
                <Input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="ابحث في الفتاوى..."
                    className="text-right"
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
                <Button onClick={handleSearch} className="bg-emerald-600 hover:bg-emerald-700">
                    بحث
                </Button>
                {search && (
                    <Button variant="ghost" onClick={() => { setSearch(""); fetchFatwas(1, ""); }}>
                        إلغاء
                    </Button>
                )}
            </div>

            {/* Fatwa Cards */}
            <div className="grid gap-4">
                {loading ? (
                    Array.from({ length: 5 }).map((_, i) => (
                        <Card key={i} className="border-border/40">
                            <CardContent className="pt-6 space-y-3">
                                <Skeleton className="h-6 w-3/4" />
                                <Skeleton className="h-4 w-full" />
                                <Skeleton className="h-4 w-2/3" />
                            </CardContent>
                        </Card>
                    ))
                ) : fatwas.length === 0 ? (
                    <Card className="border-border/40">
                        <CardContent className="pt-6 text-center text-muted-foreground">
                            لم يتم العثور على نتائج
                        </CardContent>
                    </Card>
                ) : (
                    fatwas.map((fatwa) => (
                        <Link key={fatwa.fatwa_id} href={`/fatwas/${fatwa.fatwa_id}`}>
                            <Card className="border-border/40 hover:border-emerald-600/40 transition-all cursor-pointer group">
                                <CardContent className="pt-6">
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex-1 min-w-0">
                                            <h3 className="font-bold text-lg mb-2 group-hover:text-emerald-400 transition-colors">
                                                {fatwa.title}
                                            </h3>
                                            {fatwa.question && (
                                                <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                                                    <span className="font-semibold text-foreground/70">السؤال: </span>
                                                    {fatwa.question}
                                                </p>
                                            )}
                                            <p className="text-sm text-muted-foreground/60 line-clamp-2">
                                                {fatwa.answer_preview}
                                            </p>
                                        </div>
                                        <div className="flex flex-col items-end gap-2 flex-shrink-0">
                                            <Badge variant="outline" className="text-xs text-emerald-400 border-emerald-600/30">
                                                فتوى #{fatwa.fatwa_id}
                                            </Badge>
                                            {fatwa.categories.length > 0 && (
                                                <Badge variant="secondary" className="text-xs">
                                                    {fatwa.categories[0]}
                                                </Badge>
                                            )}
                                            {fatwa.has_audio && (
                                                <Badge variant="outline" className="text-xs">🎧 صوتي</Badge>
                                            )}
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </Link>
                    ))
                )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex justify-center gap-2 mt-8">
                    <Button
                        variant="outline"
                        disabled={page <= 1}
                        onClick={() => setPage(page - 1)}
                    >
                        السابق
                    </Button>
                    <span className="flex items-center px-4 text-sm text-muted-foreground">
                        صفحة {page} من {totalPages}
                    </span>
                    <Button
                        variant="outline"
                        disabled={page >= totalPages}
                        onClick={() => setPage(page + 1)}
                    >
                        التالي
                    </Button>
                </div>
            )}
        </div>
    );
}

export default function FatwasPage() {
    return (
        <Suspense fallback={
            <div className="container mx-auto px-4 py-8">
                <Skeleton className="h-10 w-64 mb-4" />
                <Skeleton className="h-12 w-96 mb-8" />
                {Array.from({ length: 5 }).map((_, i) => (
                    <Card key={i} className="border-border/40 mb-4">
                        <CardContent className="pt-6 space-y-3">
                            <Skeleton className="h-6 w-3/4" />
                            <Skeleton className="h-4 w-full" />
                        </CardContent>
                    </Card>
                ))}
            </div>
        }>
            <FatwasContent />
        </Suspense>
    );
}
