"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { NestedQA } from "@/components/content/NestedQA";
import { QuranBlock } from "@/components/content/QuranBlock";

export default function AudioDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = Number(params.id);
    const [audio, setAudio] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        api.audios.get(id)
            .then(setAudio)
            .catch(() => setError("لم يتم العثور على التسجيل"))
            .finally(() => setLoading(false));
    }, [id]);

    if (loading) return (
        <div className="container mx-auto px-4 py-12 max-w-3xl" dir="rtl">
            <Skeleton className="h-8 w-3/4 mb-4" />
            <Skeleton className="h-12 w-full mb-4" />
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-4/5" />
        </div>
    );

    if (error || !audio) return (
        <div className="container mx-auto px-4 py-12 text-center" dir="rtl">
            <p className="text-muted-foreground mb-4">{error || "خطأ غير معروف"}</p>
            <Button variant="outline" onClick={() => router.back()}>رجوع</Button>
        </div>
    );

    return (
        <div className="min-h-screen" dir="rtl">
            {/* Header */}
            <div className="border-b border-border/40 bg-card/30">
                <div className="container mx-auto px-4 py-8 max-w-3xl">
                    <Button variant="ghost" size="sm" onClick={() => router.back()} className="mb-4 text-muted-foreground">
                        ← الأشرطة والتسجيلات
                    </Button>
                    <div className="flex items-center gap-2 mb-2">
                        <span className="text-2xl">🎧</span>
                        <span className="text-sm text-muted-foreground">تسجيل صوتي</span>
                    </div>
                    <h1 className="text-3xl font-bold font-[family-name:var(--font-amiri)] leading-relaxed mb-4">
                        {audio.title}
                    </h1>
                    {audio.categories?.length > 0 && (
                        <div className="flex gap-2 flex-wrap">
                            {audio.categories.map((c: string) => (
                                <Badge key={c} variant="outline" className="border-purple-600/30 text-purple-400/80 text-xs">
                                    {c}
                                </Badge>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="container mx-auto px-4 py-8 max-w-3xl space-y-6">

                {/* Audio player — only when audio_url is confirmed */}
                {audio.audio_url && (
                    <div className="p-5 rounded-xl border border-purple-600/30 bg-purple-950/20">
                        <p className="text-sm font-semibold text-purple-400 mb-3 flex items-center gap-2">
                            <span>🎵</span> استمع للتسجيل
                        </p>
                        <audio controls className="w-full" preload="metadata">
                            <source src={audio.audio_url} type="audio/mpeg" />
                            متصفحك لا يدعم تشغيل الصوت
                        </audio>
                    </div>
                )}

                {/* Main transcript (lecture portion) */}
                {audio.transcript && (
                    <div
                        className="text-foreground/90 leading-[2.2] text-lg font-[family-name:var(--font-amiri)] whitespace-pre-line"
                    >
                        {audio.transcript}
                    </div>
                )}

                {/* Nested Q&A — from scraped qa_pairs */}
                {audio.qa_pairs?.length > 0 && (
                    <NestedQA
                        pairs={audio.qa_pairs}
                        title="أسئلة وأجوبة من الدرس"
                    />
                )}

                {/* Quran Citations extracted from transcript */}
                {audio.quran_citations?.length > 0 && (
                    <div className="p-5 rounded-xl border border-emerald-600/20 bg-emerald-950/10">
                        <QuranBlock citations={audio.quran_citations} />
                    </div>
                )}

                {/* Source link */}
                {audio.url && (
                    <div className="mt-4 text-center">
                        <a href={audio.url} target="_blank" rel="noopener noreferrer"
                            className="text-sm text-purple-500 hover:text-purple-400 underline">
                            المصدر الأصلي ↗
                        </a>
                    </div>
                )}
            </div>
        </div>
    );
}
