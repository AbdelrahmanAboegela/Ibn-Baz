"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
    Sheet,
    SheetContent,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet";

const navItems = [
    { href: "/", label: "الرئيسية" },
    { href: "/fatwas", label: "الفتاوى" },
    { href: "/audios", label: "الأشرطة" },
    { href: "/articles", label: "المقالات" },
    { href: "/books", label: "الكتب" },
    { href: "/speeches", label: "الخطب" },
    { href: "/discussions", label: "المحاضرات" },
];

export function Header() {
    const [open, setOpen] = useState(false);

    return (
        <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/90 backdrop-blur-xl">
            <div className="container mx-auto flex h-20 items-center justify-between px-4">

                {/* Logo — portrait photo, tall and roomy */}
                <Link href="/" className="flex items-center gap-4 group">
                    <div className="relative h-14 w-14 shrink-0">
                        <Image
                            src="/ibn-baz.png"
                            alt="الشيخ ابن باز"
                            fill
                            className="object-contain drop-shadow-md"
                            priority
                        />
                    </div>
                    <div className="hidden sm:block">
                        <h1 className="text-xl font-bold leading-tight tracking-tight">مكتبة ابن باز</h1>
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
                <div className="hidden md:flex items-center">
                    <Link href="/chat">
                        <Button className="bg-emerald-600 hover:bg-emerald-700">
                            💬 اسأل الشيخ
                        </Button>
                    </Link>
                </div>

                {/* Mobile Menu */}
                <Sheet open={open} onOpenChange={setOpen}>
                    <SheetTrigger asChild className="md:hidden">
                        <Button variant="ghost" size="icon" aria-label="فتح القائمة">
                            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                            </svg>
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="right" className="w-72">
                        <SheetTitle className="sr-only">القائمة الرئيسية</SheetTitle>
                        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-border/40">
                            <div className="relative h-12 w-12 overflow-hidden rounded-xl ring-1 ring-emerald-600/40">
                                <Image src="/ibn-baz.png" alt="الشيخ ابن باز" fill className="object-contain" />
                            </div>
                            <div>
                                <p className="font-bold text-sm">مكتبة ابن باز</p>
                                <p className="text-xs text-muted-foreground">رحمه الله</p>
                            </div>
                        </div>
                        <nav className="flex flex-col gap-1">
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
