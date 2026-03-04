/**
 * Renders a list of nested Q&A pairs (س / ج format) as styled cards.
 * Works with { q, a } objects from fatwas (parsed from answer text)
 * and audios (from qa_pairs field).
 */

interface QAPair {
    q: string;
    a: string;
}

interface NestedQAProps {
    pairs: QAPair[];
    title?: string;
}

export function NestedQA({ pairs, title = "أسئلة وأجوبة إضافية" }: NestedQAProps) {
    if (!pairs || pairs.length === 0) return null;

    return (
        <div className="mt-6 space-y-4">
            <h3 className="text-base font-bold text-muted-foreground flex items-center gap-2">
                <span>💬</span> {title}
            </h3>
            <div className="space-y-4">
                {pairs.map((pair, i) => (
                    <div key={i} className="rounded-xl overflow-hidden border border-border/30">
                        {/* Question */}
                        {pair.q && (
                            <div className="px-4 py-3 bg-emerald-950/20 border-b border-border/20">
                                <span className="text-xs font-bold text-emerald-500 ml-2">س</span>
                                <span className="text-sm leading-relaxed font-[family-name:var(--font-amiri)]">
                                    {pair.q}
                                </span>
                            </div>
                        )}
                        {/* Answer */}
                        {pair.a && (
                            <div className="px-4 py-3 bg-card/40">
                                <span className="text-xs font-bold text-amber-500 ml-2">ج</span>
                                <span className="text-sm leading-loose font-[family-name:var(--font-amiri)]">
                                    {pair.a}
                                </span>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}

/**
 * Parses س: ... ج: ... patterns from raw Arabic text.
 * Used when structured qa pairs aren't available but the answer text contains them.
 */
export function parseQAPairs(text: string): QAPair[] {
    if (!text) return [];
    const pattern = /س\s*[:：]\s*(.*?)\s*ج\s*[:：]\s*(.*?)(?=\s*س\s*[:：]|$)/gs;
    const pairs: QAPair[] = [];
    let match;
    while ((match = pattern.exec(text)) !== null) {
        const q = match[1].trim();
        const a = match[2].trim();
        if (q || a) pairs.push({ q, a });
    }
    return pairs;
}
