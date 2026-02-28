"use client";

import { useState } from "react";
import type { ContentType } from "./ContentTypeSelector";

interface GeneratedContentProps {
  content: string;
  contentType: ContentType;
}

export default function GeneratedContent({
  content,
  contentType,
}: GeneratedContentProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement("textarea");
      textArea.value = content;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const posts =
    contentType === "thread"
      ? content.split(/\n\n(?=\d+[\.\)\/]|\[?\d+[\.\)\/])/g).filter(Boolean)
      : [content];

  return (
    <div className="animate-fadeIn">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Generated Content</h3>
        <button
          onClick={handleCopy}
          className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
            copied
              ? "bg-green-500/20 text-green-400 border border-green-500/30"
              : "bg-x-blue/10 text-x-blue border border-x-blue/30 hover:bg-x-blue/20"
          }`}
        >
          {copied ? (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Copied!
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Copy All
            </>
          )}
        </button>
      </div>

      <div className="space-y-3">
        {posts.map((post, index) => (
          <div
            key={index}
            className="bg-x-card border border-x-border rounded-2xl p-4 hover:border-x-border/80 transition-colors"
          >
            {contentType === "thread" && posts.length > 1 && (
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-medium text-x-blue bg-x-blue/10 px-2 py-0.5 rounded-full">
                  {index + 1}/{posts.length}
                </span>
              </div>
            )}
            <p className="text-white whitespace-pre-wrap leading-relaxed text-[15px]">
              {post.trim()}
            </p>
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-x-border/50">
              <span className="text-xs text-x-gray">
                {post.trim().length} characters
              </span>
              <button
                onClick={async () => {
                  await navigator.clipboard.writeText(post.trim());
                }}
                className="text-xs text-x-gray hover:text-x-blue transition-colors"
              >
                Copy this post
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
