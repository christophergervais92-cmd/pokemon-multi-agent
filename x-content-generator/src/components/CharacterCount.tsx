"use client";

interface CharacterCountProps {
  current: number;
  max: number;
}

export default function CharacterCount({ current, max }: CharacterCountProps) {
  const percentage = Math.min((current / max) * 100, 100);
  const isWarning = percentage >= 80;
  const isOver = current > max;
  const remaining = max - current;

  const radius = 10;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  let color = "#1d9bf0";
  if (isOver) color = "#f4212e";
  else if (isWarning) color = "#ffd400";

  return (
    <div className="flex items-center gap-2">
      {current > 0 && (
        <>
          <svg width="26" height="26" viewBox="0 0 26 26" className="char-ring">
            <circle
              cx="13"
              cy="13"
              r={radius}
              fill="none"
              stroke="#2f3336"
              strokeWidth="2"
            />
            <circle
              cx="13"
              cy="13"
              r={radius}
              fill="none"
              stroke={color}
              strokeWidth="2"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              transform="rotate(-90 13 13)"
              className="transition-all duration-200"
            />
          </svg>
          {isWarning && (
            <span
              className={`text-sm font-medium ${
                isOver ? "text-red-500" : "text-yellow-400"
              }`}
            >
              {remaining}
            </span>
          )}
        </>
      )}
    </div>
  );
}
