/**
 * arabicText.ts
 * Utilities for cleaning LLM-generated Arabic text before display.
 */

// XML wrapper tags the LLM may emit — strip them client-side from streamed chunks
const XML_TAG_RE = /<\/?(?:quran_start|quran_end|hadith_start|hadith_end|verse_start|verse_end)\b[^>]*>/gi;

/**
 * Remove any XML wrapper tags (quran_start / quran_end / hadith_start /
 * hadith_end etc.) that the LLM might include in its streamed output.
 */
export function stripXmlTags(text: string): string {
    return text.replace(XML_TAG_RE, "");
}
