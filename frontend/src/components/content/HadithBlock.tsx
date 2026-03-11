/**
 * HadithBlock — renders structured hadith citations detected in the AI answer.
 * Shows the hadith text (verified via dorar.net when available), narrator,
 * authenticity grade badge (colour-coded), English translation (from sunnah.com
 * when available), and links to dorar.net (precise search) and sunnah.com (direct page).
 */

import { HadithCitation } from "@/types";

interface HadithBlockProps {
    citations: HadithCitation[];
    compact?: boolean;
}

function gradeBadge(level: number | undefined, grade: string | undefined, secondary?: string) {
    if (!grade) return null;
    const colors: Record<number, string> = {
        1: "bg-green-900/40 text-green-400 border-green-600/30",
        2: "bg-blue-900/40 text-blue-400 border-blue-600/30",
        3: "bg-orange-900/40 text-orange-400 border-orange-600/30",
        4: "bg-red-900/40 text-red-400 border-red-600/30",
    };
    const cls = colors[level ?? 0] ?? "bg-gray-800/40 text-gray-400 border-gray-600/30";
    return (
        <span className="flex items-center gap-1.5 flex-wrap">
            <span className={`text-xs rounded-full px-2 py-0.5 border ${cls}`}>
                {grade}
            </span>
            {secondary && secondary !== grade && (
                <span className="text-xs text-muted-foreground/70" title="sunnah.com grade">
                    ({secondary})
                </span>
            )}
        </span>
    );
}

export function HadithBlock({ citations, compact = false }: HadithBlockProps) {
    if (!citations || citations.length === 0) return null;

    // Filter: need at least a collection name or a meaningful text snippet
    const valid = citations.filter(c =>
        (c.text && c.text.length >= 10) || c.collection || c.verified_text
    );
    if (valid.length === 0) return null;

    if (compact) {
        return (
            <div className="flex flex-wrap gap-2 mt-3">
                {valid.map((c, i) => (
                    <a
                        key={i}
                        href={c.dorar_url || c.sunnah_url || "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-950/30 border border-amber-600/25 text-amber-400 text-xs hover:bg-amber-950/50 transition-colors"
                        title={c.verified_text || c.text}
                    >
                        📜 {c.collection || "حديث نبوي"}
                    </a>
                ))}
            </div>
        );
    }

    return (
        <div className="space-y-3">
            <h3 className="text-sm font-bold text-amber-400 flex items-center gap-2">
                <span>📜</span> الأحاديث النبوية
            </h3>
            {valid.map((c, i) => {
                // Prefer the dorar-verified text; fall back to extracted snippet
                const displayText = (c.verified_text && c.verified_text.length >= 10)
                    ? c.verified_text
                    : (c.text && c.text.length >= 10 ? c.text : null);

                return (
                    <div
                        key={i}
                        className="rounded-xl border border-amber-600/20 bg-amber-950/10 p-4 space-y-3"
                    >
                        {/* Arabic hadith body */}
                        {displayText && (
                            <p className="font-[family-name:var(--font-amiri)] text-base leading-loose text-foreground/90">
                                {displayText}
                            </p>
                        )}

                        {/* English translation from sunnah.com (when available) */}
                        {c.sunnah_text_en && (
                            <p className="text-xs text-muted-foreground/80 leading-relaxed border-t border-amber-600/10 pt-2 italic">
                                {c.sunnah_text_en}
                            </p>
                        )}

                        {/* Grade + narrator row */}
                        {(c.grade || c.narrator) && (
                            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                {gradeBadge(c.grade_level, c.grade, c.sunnah_grade)}
                                {c.narrator && (
                                    <span>رواه: {c.narrator}</span>
                                )}
                                {c.source_book && (
                                    <span className="opacity-70">• {c.source_book}</span>
                                )}
                            </div>
                        )}

                        {/* Attribution + external links */}
                        <div className="flex items-center justify-between flex-wrap gap-2">
                            <span className="text-xs bg-amber-900/40 text-amber-400 rounded-full px-2.5 py-0.5 border border-amber-600/20">
                                {c.collector || "حديث نبوي"}
                            </span>
                            <div className="flex items-center gap-3">
                                {c.dorar_url && (
                                    <a
                                        href={c.dorar_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-xs text-amber-500 hover:text-amber-400 hover:underline transition-colors"
                                    >
                                        dorar.net ↗
                                    </a>
                                )}
                                {c.sunnah_url && (
                                    <a
                                        href={c.sunnah_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-xs text-amber-500/70 hover:text-amber-400 hover:underline transition-colors"
                                    >
                                        sunnah.com ↗
                                    </a>
                                )}
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
