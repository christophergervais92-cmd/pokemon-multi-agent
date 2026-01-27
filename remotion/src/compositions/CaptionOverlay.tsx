import React from 'react';
import {
	AbsoluteFill,
	useCurrentFrame,
	useVideoConfig,
	interpolate,
} from 'remotion';

interface CaptionWord {
	word: string;
	start: number;
	end: number;
}

export interface CaptionOverlayProps {
	timestamps: CaptionWord[];
	fps: number;
	style?: 'default' | 'bold' | 'minimal';
}

export const CaptionOverlay: React.FC<CaptionOverlayProps> = ({
	timestamps,
	fps,
	style = 'default',
}) => {
	const frame = useCurrentFrame();
	const currentTime = frame / fps;

	// Find words that should be visible at current time
	const visibleWords = timestamps.filter(
		(ts) => currentTime >= ts.start && currentTime <= ts.end
	);

	// Get current word being spoken
	const currentWord = timestamps.find(
		(ts) => currentTime >= ts.start && currentTime < ts.end
	);

	// Build caption line (show 3-5 words at a time)
	const getCurrentLine = (): CaptionWord[] => {
		const currentIndex = timestamps.findIndex(
			(ts) => currentTime >= ts.start && currentTime < ts.end
		);

		if (currentIndex === -1) return [];

		// Show current word + next 2-4 words
		const wordsPerLine = 4;
		const startIndex = Math.max(
			0,
			currentIndex - Math.floor(wordsPerLine / 2)
		);
		return timestamps.slice(startIndex, startIndex + wordsPerLine);
	};

	const lineWords = getCurrentLine();

	if (lineWords.length === 0) return null;

	return (
		<AbsoluteFill
			style={{
				justifyContent: 'flex-end',
				alignItems: 'center',
				paddingBottom: 150,
			}}
		>
			<div
				style={{
					display: 'flex',
					flexWrap: 'wrap',
					justifyContent: 'center',
					alignItems: 'center',
					gap: '12px',
					maxWidth: '90%',
					padding: '20px 30px',
				}}
			>
				{lineWords.map((wordData, index) => {
					const isActive = currentWord?.word === wordData.word;
					const wordProgress =
						currentWord?.word === wordData.word
							? interpolate(
									currentTime,
									[wordData.start, wordData.end],
									[0, 1],
									{
										extrapolateLeft: 'clamp',
										extrapolateRight: 'clamp',
									}
							  )
							: currentTime > wordData.end
							? 1
							: 0;

					return (
						<span
							key={`${wordData.word}-${index}`}
							style={{
								fontSize: style === 'bold' ? 64 : 56,
								fontWeight: style === 'minimal' ? 600 : 800,
								color: 'white',
								textTransform: 'uppercase',
								textShadow: '0 4px 12px rgba(0,0,0,0.9)',
								backgroundColor: isActive
									? 'rgba(255, 215, 0, 0.9)'
									: 'rgba(0, 0, 0, 0.7)',
								padding: '8px 16px',
								borderRadius: '8px',
								transform: isActive ? 'scale(1.1)' : 'scale(1)',
								transition: 'transform 0.2s ease',
								opacity: interpolate(wordProgress, [0, 0.2], [0.7, 1]),
							}}
						>
							{wordData.word}
						</span>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};
