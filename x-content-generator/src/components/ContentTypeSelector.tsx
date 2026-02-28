"use client";

const CONTENT_TYPES = [
  { id: "single", label: "Single Post", icon: "📝", description: "One impactful post" },
  { id: "thread", label: "Thread", icon: "🧵", description: "Multi-post thread" },
  { id: "reply", label: "Reply / Quote", icon: "💬", description: "Engaging response" },
  { id: "poll", label: "Poll", icon: "📊", description: "Interactive poll" },
] as const;

export type ContentType = (typeof CONTENT_TYPES)[number]["id"];

interface ContentTypeSelectorProps {
  selected: ContentType;
  onSelect: (type: ContentType) => void;
}

export default function ContentTypeSelector({
  selected,
  onSelect,
}: ContentTypeSelectorProps) {
  return (
    <div className="flex gap-2 flex-wrap">
      {CONTENT_TYPES.map((type) => (
        <button
          key={type.id}
          onClick={() => onSelect(type.id)}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-full border transition-all duration-200 ${
            selected === type.id
              ? "border-x-blue bg-x-blue/10 text-white"
              : "border-x-border bg-transparent hover:bg-x-hover text-gray-400 hover:text-white"
          }`}
        >
          <span>{type.icon}</span>
          <span className="text-sm font-medium">{type.label}</span>
        </button>
      ))}
    </div>
  );
}
