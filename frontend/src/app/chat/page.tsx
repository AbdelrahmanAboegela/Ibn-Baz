"use client";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { api } from "@/lib/api";
import Link from "next/link";
import type { ChatResponse, SSEEvent } from "@/types";

interface Message {
    role: "user" | "assistant";
    content: string;
    metadata?: ChatResponse;
    loading?: boolean;
}

const SUGGESTED_QUESTIONS = [
    "ما حكم التميمة من القرآن؟",
    "ما حكم صلاة الجماعة؟",
    "ما هي شروط الصلاة؟",
    "ما حكم الربا في الإسلام؟",
    "كيف يكون بر الوالدين؟",
];

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        scrollRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const sendMessage = async (query: string) => {
        if (!query.trim() || isLoading) return;

        const userMsg: Message = { role: "user", content: query };
        const assistantMsg: Message = { role: "assistant", content: "", loading: true };

        setMessages((prev) => [...prev, userMsg, assistantMsg]);
        setInput("");
        setIsLoading(true);

        try {
            // Use SSE streaming
            const res = await fetch(api.chat.streamUrl(), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query, top_k: 5 }),
            });

            const reader = res.body?.getReader();
            const decoder = new TextDecoder();
            let fullContent = "";
            let metadata: ChatResponse | undefined;

            if (reader) {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const text = decoder.decode(value, { stream: true });
                    const lines = text.split("\n");

                    for (const line of lines) {
                        if (!line.startsWith("data: ")) continue;
                        try {
                            const event: SSEEvent = JSON.parse(line.slice(6));

                            if (event.type === "chunk" && typeof event.content === "string") {
                                fullContent += event.content;
                                setMessages((prev) => {
                                    const updated = [...prev];
                                    updated[updated.length - 1] = {
                                        role: "assistant",
                                        content: fullContent,
                                        loading: true,
                                    };
                                    return updated;
                                });
                            } else if (event.type === "metadata") {
                                metadata = event.content as ChatResponse;
                            } else if (event.type === "error") {
                                fullContent = `خطأ: ${event.content}`;
                            }
                        } catch {
                            // skip malformed lines
                        }
                    }
                }
            }

            setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                    role: "assistant",
                    content: fullContent || "لم أتمكن من الإجابة",
                    metadata,
                    loading: false,
                };
                return updated;
            });
        } catch (err) {
            // Fallback: non-streaming
            try {
                const data = await api.chat.query(query);
                setMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                        role: "assistant",
                        content: data.answer,
                        metadata: data,
                        loading: false,
                    };
                    return updated;
                });
            } catch {
                setMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                        role: "assistant",
                        content: "حدث خطأ في الاتصال بالخادم",
                        loading: false,
                    };
                    return updated;
                });
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="container mx-auto px-4 py-8 max-w-4xl">
            <div className="mb-6">
                <h1 className="text-3xl font-bold font-[family-name:var(--font-amiri)]">
                    🤖 اسأل الشيخ ابن باز
                </h1>
                <p className="text-muted-foreground text-sm mt-1">
                    محرك بحث ذكي مبني على فتاوى الشيخ ابن باز رحمه الله — مع توثيق الآيات والمصادر
                </p>
            </div>

            {/* Chat Area */}
            <Card className="border-border/40 min-h-[60vh] flex flex-col">
                <ScrollArea className="flex-1 p-4">
                    {messages.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center py-16">
                            <div className="text-6xl mb-4">📖</div>
                            <p className="text-lg font-bold mb-6">ابدأ بسؤال</p>
                            <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                                {SUGGESTED_QUESTIONS.map((q) => (
                                    <Button
                                        key={q}
                                        variant="outline"
                                        size="sm"
                                        className="text-xs"
                                        onClick={() => sendMessage(q)}
                                    >
                                        {q}
                                    </Button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {messages.map((msg, i) => (
                                <div key={i} className={`flex ${msg.role === "user" ? "justify-start" : "justify-end"}`}>
                                    <div className={`max-w-[85%] ${msg.role === "user"
                                            ? "bg-emerald-600/20 border border-emerald-600/30"
                                            : "bg-muted"
                                        } rounded-xl p-4`}>
                                        <p className="text-xs text-muted-foreground mb-1">
                                            {msg.role === "user" ? "أنت" : "الشيخ ابن باز (AI)"}
                                        </p>
                                        <div className="whitespace-pre-wrap leading-relaxed">
                                            {msg.content}
                                            {msg.loading && (
                                                <span className="inline-block w-2 h-4 bg-emerald-400 animate-pulse mr-1" />
                                            )}
                                        </div>

                                        {/* Citations */}
                                        {msg.metadata && !msg.loading && (
                                            <div className="mt-4 space-y-3">
                                                <Separator className="bg-border/30" />

                                                {/* Confidence */}
                                                <div className="flex items-center gap-2">
                                                    <span className="text-xs text-muted-foreground">درجة الثقة:</span>
                                                    <Badge
                                                        variant={msg.metadata.confidence > 0.7 ? "default" : "outline"}
                                                        className={msg.metadata.confidence > 0.7 ? "bg-emerald-600" : ""}
                                                    >
                                                        {Math.round(msg.metadata.confidence * 100)}%
                                                    </Badge>
                                                    <span className="text-xs text-muted-foreground">
                                                        ({msg.metadata.query_time_ms.toFixed(0)} مللي ثانية)
                                                    </span>
                                                </div>

                                                {/* Cited Fatwas */}
                                                {msg.metadata.cited_fatwas.length > 0 && (
                                                    <div>
                                                        <p className="text-xs font-bold text-emerald-400 mb-2">📜 المصادر:</p>
                                                        <div className="flex flex-wrap gap-2">
                                                            {msg.metadata.cited_fatwas.map((f) => (
                                                                <Link key={f.fatwa_id} href={`/fatwas/${f.fatwa_id}`}>
                                                                    <Badge variant="outline" className="cursor-pointer hover:bg-muted text-xs">
                                                                        فتوى #{f.fatwa_id} — {f.title.slice(0, 40)}
                                                                    </Badge>
                                                                </Link>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Quran Citations */}
                                                {msg.metadata.quran_citations.length > 0 && (
                                                    <div>
                                                        <p className="text-xs font-bold text-emerald-400 mb-2">📖 الآيات:</p>
                                                        <div className="space-y-2">
                                                            {msg.metadata.quran_citations.slice(0, 3).map((c, i) => (
                                                                <div key={i} className="p-2 rounded bg-background/50 text-sm">
                                                                    <p className="font-[family-name:var(--font-amiri)] leading-loose">
                                                                        {c.verified_text}
                                                                    </p>
                                                                    <a href={c.quran_url} target="_blank" rel="noopener noreferrer"
                                                                        className="text-xs text-emerald-400 hover:underline">
                                                                        {c.reference} ←
                                                                    </a>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                            <div ref={scrollRef} />
                        </div>
                    )}
                </ScrollArea>

                {/* Input */}
                <div className="p-4 border-t border-border/40">
                    <div className="flex gap-2">
                        <Input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="اكتب سؤالك هنا..."
                            className="text-right"
                            disabled={isLoading}
                            onKeyDown={(e) => e.key === "Enter" && sendMessage(input)}
                        />
                        <Button
                            onClick={() => sendMessage(input)}
                            disabled={isLoading || !input.trim()}
                            className="bg-emerald-600 hover:bg-emerald-700 px-6"
                        >
                            {isLoading ? "⏳" : "إرسال"}
                        </Button>
                    </div>
                </div>
            </Card>
        </div>
    );
}
