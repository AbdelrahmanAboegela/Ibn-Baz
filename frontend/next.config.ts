import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["192.168.1.21", "localhost", "127.0.0.1"],
  // react-markdown v9+ and related packages are ESM-only; transpile them for Next.js
  transpilePackages: ["react-markdown", "remark-gfm", "remark-parse", "unified", "bail", "is-plain-obj", "trough", "vfile", "unist-util-stringify-position", "micromark", "decode-named-character-reference", "character-entities", "mdast-util-from-markdown", "mdast-util-to-string", "mdast-util-gfm", "mdast-util-gfm-autolink-literal", "mdast-util-gfm-footnote", "mdast-util-gfm-strikethrough", "mdast-util-gfm-table", "mdast-util-gfm-task-list-item", "mdast-util-phrasing-content", "mdast-util-to-hast", "hast-util-to-jsx-runtime", "hast-util-whitespace", "hast-util-is-element", "property-information", "space-separated-tokens", "comma-separated-tokens", "vfile-message", "unist-util-visit", "unist-util-is", "unist-util-position", "remark-rehype", "hastscript", "zwitch", "html-url-attributes"],
};

export default nextConfig;
