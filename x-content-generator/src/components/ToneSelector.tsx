"use client";

const TONES = [
  { id: "professional", label: "Professional", emoji: "💼", description: "Polished & authoritative" },
  { id: "casual", label: "Casual", emoji: "😎", description: "Friendly & relatable" },
  { id: "witty", label: "Witty", emoji: "🎯", description: "Clever & engaging" },
  { id: "educational", label: "Educational", emoji: "📚", description: "Informative & clear" },
  { id: "provocative", label: "Provocative", emoji: "🔥", description: "Bold & attention-grabbing" },
  { id: "inspirational", label: "Inspirational", emoji: "✨", description: "Motivating & uplifting" },
] as const;

export type ToneId = (typeof TONES)[number]["id"];

interface ToneSelectorProps {
  selected: ToneId;
  onSelect: (tone: ToneId) => void;
}

export default function ToneSelector({ selected, onSelect }: ToneSelectorProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      {TONES.map((tone) => (
        <button
          key={tone.id}
          onClick={() => onSelect(tone.id)}
          className={`flex items-center gap-2 px-3 py-2.5 rounded-xl border transition-all duration-200 text-left ${
            selected === tone.id
              ? "border-x-blue bg-x-blue/10 text-white"
              : "border-x-border bg-x-card hover:bg-x-hover text-gray-300 hover:text-white"
          }`}
        >
          <span className="text-lg">{tone.emoji}</span>
          <div>
            <div className="text-sm font-medium">{tone.label}</div>
            <div className="text-[11px] text-x-gray">{tone.description}</div>
          </div>
        </button>
      ))}
    </div>
  );
}
