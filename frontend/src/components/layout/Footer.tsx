export function Footer() {
    return (
        <footer className="border-t border-border/40 bg-background/50 py-8">
            <div className="container mx-auto px-4 text-center">
                <p className="text-sm text-muted-foreground font-[family-name:var(--font-amiri)]">
                    سماحة الشيخ عبد العزيز بن عبد الله بن باز رحمه الله
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                    ١٣٣٠ - ١٤٢٠ هـ | المفتي العام للمملكة العربية السعودية
                </p>
                <p className="text-xs text-muted-foreground/60 mt-4">
                    مشروع بحثي لمقرر معالجة اللغة الطبيعية — جميع المحتويات من موقع{" "}
                    <a
                        href="https://binbaz.org.sa"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline hover:text-foreground transition-colors"
                    >
                        binbaz.org.sa
                    </a>
                </p>
            </div>
        </footer>
    );
}
