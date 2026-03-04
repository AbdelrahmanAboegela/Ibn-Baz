/**
 * QuranBlock — renders one or more structured Quran citations.
 * Used wherever quran_citations is available (fatwas, chat responses).
 */

interface QuranCitation {
    reference: string;
    surah_name?: string;
    surah_number?: number;
    ayah_number?: number;
    verified_text?: string;
    quran_url?: string;
}

interface QuranBlockProps {
    citations: QuranCitation[];
    compact?: boolean;         // true = inline chips, false = full cards
}

export function QuranBlock({ citations, compact = false }: QuranBlockProps) {
    if (!citations || citations.length === 0) return null;

    if (compact) {
        return (
            <div className="flex flex-wrap gap-2 mt-3">
                {citations.map((c, i) => (
                    <a
                        key={i}
                        href={c.quran_url || "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/30 border border-emerald-600/25 text-emerald-400 text-xs hover:bg-emerald-950/50 transition-colors"
                        title={c.verified_text}
                    >
                        📖 {c.reference}
                    </a>
                ))}
            </div>
        );
    }

    return (
        <div className="space-y-3">
            <h3 className="text-sm font-bold text-emerald-400 flex items-center gap-2">
                <span>📖</span> الآيات القرآنية
            </h3>
            {citations.map((c, i) => (
                <div
                    key={i}
                    className="rounded-xl border border-emerald-600/20 bg-emerald-950/10 p-4"
                >
                    {/* Verse text */}
                    {c.verified_text && (
                        <p className="font-[family-name:var(--font-amiri)] text-lg leading-loose mb-3 text-foreground/90">
                            {c.verified_text}
                        </p>
                    )}
                    {/* Reference + link */}
                    <div className="flex items-center justify-between">
                        <span className="text-xs bg-emerald-900/40 text-emerald-400 rounded-full px-2.5 py-0.5 border border-emerald-600/20">
                            {c.surah_name
                                ? `${c.surah_name} — آية ${c.ayah_number}`
                                : c.reference}
                        </span>
                        {c.quran_url && (
                            <a
                                href={c.quran_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-emerald-500 hover:text-emerald-400 hover:underline transition-colors"
                            >
                                quran.com ↗
                            </a>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}
