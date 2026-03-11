/**
 * useVoiceInput
 * Arabic voice input using the browser Web Speech API (ar-SA).
 * Works in Chrome, Edge, and Safari. Not available in Firefox.
 *
 * Usage:
 *   const { isListening, isSupported, start, stop } = useVoiceInput({
 *       onResult: (transcript) => setInput(transcript),
 *       onError:  (msg)        => console.error(msg),
 *   });
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

declare global {
    interface Window {
        SpeechRecognition: typeof SpeechRecognition;
        webkitSpeechRecognition: typeof SpeechRecognition;
    }
}

interface UseVoiceInputOptions {
    onResult: (transcript: string) => void;
    onError?: (message: string) => void;
    lang?: string;
}

interface UseVoiceInputReturn {
    isListening: boolean;
    isSupported: boolean;
    start: () => void;
    stop: () => void;
}

export function useVoiceInput({
    onResult,
    onError,
    lang = "ar-SA",
}: UseVoiceInputOptions): UseVoiceInputReturn {
    const [isListening, setIsListening] = useState(false);
    const recognitionRef = useRef<SpeechRecognition | null>(null);

    const isSupported =
        typeof window !== "undefined" &&
        !!(window.SpeechRecognition || window.webkitSpeechRecognition);

    useEffect(() => {
        return () => {
            recognitionRef.current?.abort();
        };
    }, []);

    const start = useCallback(() => {
        if (!isSupported || isListening) return;

        const SpeechRecognition =
            window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.lang = lang;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        recognition.continuous = false;

        recognition.onresult = (event: SpeechRecognitionEvent) => {
            const transcript = event.results[0][0].transcript;
            onResult(transcript);
        };

        recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
            const msgs: Record<string, string> = {
                "no-speech":          "لم يتم اكتشاف أي صوت. حاول مرة أخرى.",
                "audio-capture":      "لا يمكن الوصول إلى الميكروفون.",
                "not-allowed":        "تم رفض إذن الميكروفون.",
                "network":            "خطأ في الشبكة أثناء التعرف على الصوت.",
                "aborted":            "",
            };
            const msg = msgs[event.error] ?? `خطأ: ${event.error}`;
            if (msg) onError?.(msg);
            setIsListening(false);
        };

        recognition.onend = () => {
            setIsListening(false);
        };

        recognitionRef.current = recognition;
        recognition.start();
        setIsListening(true);
    }, [isSupported, isListening, lang, onResult, onError]);

    const stop = useCallback(() => {
        recognitionRef.current?.stop();
        setIsListening(false);
    }, []);

    return { isListening, isSupported, start, stop };
}
