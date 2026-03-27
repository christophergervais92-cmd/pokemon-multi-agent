"use client";

import { useState, useCallback } from "react";
import XLogo from "@/components/XLogo";
import ToneSelector, { type ToneId } from "@/components/ToneSelector";
import ContentTypeSelector, { type ContentType } from "@/components/ContentTypeSelector";
import CharacterCount from "@/components/CharacterCount";
import GeneratedContent from "@/components/GeneratedContent";

export default function Home() {
  const [topic, setTopic] = useState("");
  const [tone, setTone] = useState<ToneId>("professional");
  const [contentType, setContentType] = useState<ContentType>("single");
  const [audience, setAudience] = useState("");
  const [includeHashtags, setIncludeHashtags] = useState(true);
  const [includeEmojis, setIncludeEmojis] = useState(true);
  const [generatedContent, setGeneratedContent] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [showApiKeyInput, setShowApiKeyInput] = useState(false);

  const handleGenerate = useCallback(async () => {
    if (!topic.trim()) {
      setError("Please enter a topic or idea for your content.");
      return;
    }

    const keyToUse = apiKey.trim();
    if (!keyToUse) {
      setShowApiKeyInput(true);
      setError("Please enter your OpenAI API key to generate content.");
      return;
    }

    setIsLoading(true);
    setError("");
    setGeneratedContent("");

    try {
      const response = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: topic.trim(),
          tone,
          contentType,
          audience: audience.trim(),
          includeHashtags,
          includeEmojis,
          apiKey: keyToUse,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to generate content");
      }

      setGeneratedContent(data.content);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Something went wrong. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  }, [topic, tone, contentType, audience, includeHashtags, includeEmojis, apiKey]);

  return (
    <div className="min-h-screen bg-black">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-black/80 backdrop-blur-xl border-b border-x-border">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <XLogo className="w-7 h-7 text-white" />
            <div>
              <h1 className="text-lg font-bold text-white">Content Generator</h1>
              <p className="text-xs text-x-gray">AI-powered posts for X</p>
            </div>
          </div>
          <button
            onClick={() => setShowApiKeyInput(!showApiKeyInput)}
            className="text-x-gray hover:text-white transition-colors p-2 rounded-full hover:bg-x-hover"
            title="API Settings"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 pb-32">
        {/* API Key Section */}
        {showApiKeyInput && (
          <div className="mb-6 animate-fadeIn">
            <div className="bg-x-card border border-x-border rounded-2xl p-4">
              <label className="block text-sm font-medium text-white mb-2">
                OpenAI API Key
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full bg-black border border-x-border rounded-xl px-4 py-3 text-white placeholder-x-gray focus:outline-none focus:border-x-blue focus:ring-1 focus:ring-x-blue transition-all text-sm"
              />
              <p className="text-xs text-x-gray mt-2">
                Your API key is sent directly to OpenAI and never stored on our servers.
              </p>
            </div>
          </div>
        )}

        {/* Content Type */}
        <section className="mb-6">
          <label className="block text-sm font-medium text-x-gray mb-3 uppercase tracking-wider">
            Content Type
          </label>
          <ContentTypeSelector selected={contentType} onSelect={setContentType} />
        </section>

        {/* Topic Input */}
        <section className="mb-6">
          <label className="block text-sm font-medium text-x-gray mb-3 uppercase tracking-wider">
            Topic / Idea
          </label>
          <div className="relative">
            <textarea
              value={topic}
              onChange={(e) => {
                setTopic(e.target.value);
                setError("");
              }}
              placeholder="What do you want to post about? e.g., 'The future of AI in healthcare' or 'Tips for remote work productivity'"
              rows={3}
              className="w-full bg-x-card border border-x-border rounded-2xl px-4 py-3 text-white placeholder-x-gray/60 focus:outline-none focus:border-x-blue focus:ring-1 focus:ring-x-blue transition-all text-[15px] leading-relaxed resize-none"
            />
            <div className="absolute bottom-3 right-3">
              <CharacterCount current={topic.length} max={500} />
            </div>
          </div>
        </section>

        {/* Tone */}
        <section className="mb-6">
          <label className="block text-sm font-medium text-x-gray mb-3 uppercase tracking-wider">
            Tone
          </label>
          <ToneSelector selected={tone} onSelect={setTone} />
        </section>

        {/* Audience */}
        <section className="mb-6">
          <label className="block text-sm font-medium text-x-gray mb-3 uppercase tracking-wider">
            Target Audience (optional)
          </label>
          <input
            type="text"
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
            placeholder="e.g., Tech professionals, Startup founders, Fitness enthusiasts"
            className="w-full bg-x-card border border-x-border rounded-xl px-4 py-3 text-white placeholder-x-gray/60 focus:outline-none focus:border-x-blue focus:ring-1 focus:ring-x-blue transition-all text-sm"
          />
        </section>

        {/* Options */}
        <section className="mb-8">
          <label className="block text-sm font-medium text-x-gray mb-3 uppercase tracking-wider">
            Options
          </label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer group">
              <div
                className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all ${
                  includeHashtags
                    ? "bg-x-blue border-x-blue"
                    : "border-x-border group-hover:border-x-gray"
                }`}
              >
                {includeHashtags && (
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
              <span className="text-sm text-gray-300 group-hover:text-white transition-colors">
                Include Hashtags
              </span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer group">
              <div
                className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all ${
                  includeEmojis
                    ? "bg-x-blue border-x-blue"
                    : "border-x-border group-hover:border-x-gray"
                }`}
              >
                {includeEmojis && (
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
              <span className="text-sm text-gray-300 group-hover:text-white transition-colors">
                Include Emojis
              </span>
            </label>
          </div>
        </section>

        {/* Generate Button */}
        <button
          onClick={handleGenerate}
          disabled={isLoading || !topic.trim()}
          className={`w-full py-3.5 rounded-full font-bold text-[15px] transition-all duration-200 ${
            isLoading || !topic.trim()
              ? "bg-x-blue/40 text-white/60 cursor-not-allowed"
              : "bg-x-blue hover:bg-x-blue/90 text-white active:scale-[0.98] shadow-lg shadow-x-blue/20"
          }`}
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Generating...
            </span>
          ) : (
            "Generate Content"
          )}
        </button>

        {/* Error */}
        {error && (
          <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl animate-fadeIn">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Generated Content */}
        {generatedContent && (
          <div className="mt-8">
            <GeneratedContent content={generatedContent} contentType={contentType} />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-black/80 backdrop-blur-xl border-t border-x-border">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-center">
          <p className="text-xs text-x-gray">
            Powered by OpenAI &middot; Content generated by AI may need review before posting
          </p>
        </div>
      </footer>
    </div>
  );
}
