"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";

const navItems = [
    { href: "/", label: "الرئيسية" },
    { href: "/fatwas", label: "الفتاوى" },
    { href: "/articles", label: "المقالات" },
    { href: "/books", label: "الكتب" },
    { href: "/speeches", label: "الخطب" },
    { href: "/discussions", label: "المحاضرات" },
    { href: "/chat", label: "اسأل الشيخ" },
];

export function Header() {
    const [open, setOpen] = useState(false);

    return (
        <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-xl">
            <div className="container mx-auto flex h-16 items-center justify-between px-4">
                {/* Logo */}
                <Link href="/" className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600 text-white font-bold text-lg font-[family-name:var(--font-amiri)]">
                        بز
                    </div>
                    <div className="hidden sm:block">
                        <h1 className="text-lg font-bold leading-tight">مكتبة ابن باز</h1>
                        <p className="text-xs text-muted-foreground">رحمه الله</p>
                    </div>
                </Link>

                {/* Desktop Nav */}
                <nav className="hidden md:flex items-center gap-1">
                    {navItems.map((item) => (
                        <Link
                            key={item.href}
                            href={item.href}
                            className="px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-muted"
                        >
                            {item.label}
                        </Link>
                    ))}
                </nav>

                {/* Chat CTA */}
                <div className="hidden md:flex items-center gap-2">
                    <Link href="/chat">
                        <Button
                            variant="default"
                            className="bg-emerald-600 hover:bg-emerald-700"
                        >
                            💬 اسأل الشيخ
                        </Button>
                    </Link>
                </div>

                {/* Mobile Menu */}
                <Sheet open={open} onOpenChange={setOpen}>
                    <SheetTrigger asChild className="md:hidden">
                        <Button variant="ghost" size="icon">
                            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                            </svg>
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="right" className="w-72">
                        <nav className="flex flex-col gap-2 mt-8">
                            {navItems.map((item) => (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    onClick={() => setOpen(false)}
                                    className="px-4 py-3 text-sm font-medium rounded-lg hover:bg-muted transition-colors"
                                >
                                    {item.label}
                                </Link>
                            ))}
                        </nav>
                    </SheetContent>
                </Sheet>
            </div>
        </header>
    );
}
