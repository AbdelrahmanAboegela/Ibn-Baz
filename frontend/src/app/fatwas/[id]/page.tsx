"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { NestedQA, parseQAPairs } from "@/components/content/NestedQA";
import { QuranBlock } from "@/components/content/QuranBlock";
import type { FatwaFull, RelatedFatwa } from "@/types";

export default function FatwaDetailPage() {
    const params = useParams();
    const fatwaId = Number(params.id);

    const [fatwa, setFatwa] = useState<FatwaFull | null>(null);
    const [related, setRelated] = useState<RelatedFatwa[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!fatwaId) return;
        setLoading(true);
        Promise.all([
            api.fatwas.get(fatwaId),
            api.fatwas.related(fatwaId),
        ])
            .then(([f, r]) => {
                setFatwa(f);
                setRelated(r);
            })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, [fatwaId]);

    if (loading) {
        return (
            <div className="container mx-auto px-4 py-8 space-y-4">
                <Skeleton className="h-10 w-3/4" />
                <Skeleton className="h-6 w-full" />
                <Skeleton className="h-6 w-full" />
                <Skeleton className="h-6 w-2/3" />
            </div>
        );
    }

    if (!fatwa) {
        return (
            <div className="container mx-auto px-4 py-8 text-center">
                <p className="text-muted-foreground">فتوى غير موجودة</p>
                <Link href="/fatwas">
                    <Button variant="outline" className="mt-4">العودة للفتاوى</Button>
                </Link>
            </div>
        );
    }

    // Parse nested Q&A from answer text (nested_qa not stored in Qdrant)
    // answer_direct = main answer; rest of answer has س: ... ج: ... patterns
    const directAnswer = (fatwa as any).answer_direct || fatwa.answer;
    const fullAnswer = fatwa.answer;
    const nestedPairs = parseQAPairs(
        directAnswer && fullAnswer && fullAnswer !== directAnswer
            ? fullAnswer.slice(directAnswer.length)
            : fullAnswer
    );

    return (
        <div className="container mx-auto px-4 py-8" dir="rtl">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                {/* ─── Main Content ─── */}
                <div className="lg:col-span-2 space-y-6">
                    <Link href="/fatwas">
                        <Button variant="ghost" className="text-sm mb-2">→ العودة للفتاوى</Button>
                    </Link>

                    {/* Title + meta */}
                    <div>
                        <h1 className="text-2xl md:text-3xl font-bold mb-3 font-[family-name:var(--font-amiri)]">
                            {fatwa.title}
                        </h1>
                        <div className="flex flex-wrap gap-2">
                            <Badge variant="outline" className="text-emerald-400 border-emerald-600/30">
                                فتوى #{fatwa.fatwa_id}
                            </Badge>
                            {fatwa.source_ref && (
                                <Badge variant="secondary">{fatwa.source_ref}</Badge>
                            )}
                            {fatwa.categories.map((cat) => (
                                <Badge key={cat} variant="outline">{cat}</Badge>
                            ))}
                        </div>
                    </div>

                    <Separator className="bg-border/40" />

                    {/* Question */}
                    {fatwa.question && (
                        <Card className="border-emerald-600/20 bg-emerald-950/10">
                            <CardHeader>
                                <CardTitle className="text-emerald-400 text-lg flex items-center gap-2">
                                    <span>❓</span> السؤال
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="leading-relaxed whitespace-pre-wrap font-[family-name:var(--font-amiri)]">
                                    {fatwa.question}
                                </p>
                            </CardContent>
                        </Card>
                    )}

                    {/* Main Answer */}
                    <Card className="border-border/40">
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <span>📝</span> الجواب
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="leading-loose whitespace-pre-wrap text-foreground/90 font-[family-name:var(--font-amiri)]">
                                {directAnswer}
                            </div>

                            {/* Nested Q&A pairs (parsed from full answer text) */}
                            {nestedPairs.length > 0 && (
                                <NestedQA pairs={nestedPairs} />
                            )}
                        </CardContent>
                    </Card>

                    {/* Audio player */}
                    {fatwa.audio_url && (
                        <Card className="border-purple-600/20 bg-purple-950/10">
                            <CardHeader>
                                <CardTitle className="text-lg flex items-center gap-2">
                                    <span>🎧</span> الاستماع للفتوى
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <audio controls className="w-full" preload="none">
                                    <source src={fatwa.audio_url} type="audio/mpeg" />
                                    متصفحك لا يدعم تشغيل الصوت
                                </audio>
                            </CardContent>
                        </Card>
                    )}
                </div>

                {/* ─── Sidebar ─── */}
                <div className="space-y-6">

                    {/* Quran Citations — using shared component */}
                    {fatwa.quran_citations?.length > 0 && (
                        <Card className="border-emerald-600/20">
                            <CardContent className="pt-5">
                                <QuranBlock citations={fatwa.quran_citations} />
                            </CardContent>
                        </Card>
                    )}

                    {/* Related */}
                    {related.length > 0 && (
                        <Card className="border-border/40">
                            <CardHeader>
                                <CardTitle>فتاوى ذات صلة</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-2">
                                {related.map((r) => (
                                    <Link key={r.fatwa_id} href={`/fatwas/${r.fatwa_id}`}>
                                        <div className="p-2 rounded hover:bg-muted transition-colors cursor-pointer text-sm">
                                            <span className="text-emerald-400 text-xs ml-2">#{r.fatwa_id}</span>
                                            {r.title}
                                        </div>
                                    </Link>
                                ))}
                            </CardContent>
                        </Card>
                    )}

                    {/* Source */}
                    {fatwa.url && (
                        <Card className="border-border/40">
                            <CardContent className="pt-6">
                                <a
                                    href={fatwa.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-sm text-emerald-400 hover:underline"
                                >
                                    🔗 المصدر الأصلي على binbaz.org.sa
                                </a>
                            </CardContent>
                        </Card>
                    )}
                </div>
            </div>
        </div>
    );
}
