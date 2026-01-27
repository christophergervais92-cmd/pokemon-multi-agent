import React from 'react';
import {
	AbsoluteFill,
	Audio,
	Sequence,
	useCurrentFrame,
	useVideoConfig,
	interpolate,
	staticFile,
} from 'remotion';
import {VideoSequencer} from './VideoSequencer';
import {CaptionOverlay} from './CaptionOverlay';

export interface TikTokVideoProps {
	audioPath: string;
	videoClips: Array<{
		filepath: string;
		duration: number;
		startFrame: number;
	}>;
	timestamps: Array<{
		word: string;
		start: number;
		end: number;
	}>;
	backgroundMusicPath?: string;
	title?: string;
}

export const TikTokVideo: React.FC<TikTokVideoProps> = ({
	audioPath,
	videoClips,
	timestamps,
	backgroundMusicPath,
	title,
}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();

	// Calculate fade in/out for music
	const musicVolume = backgroundMusicPath
		? interpolate(frame, [0, 30], [0, 0.2], {
				extrapolateRight: 'clamp',
		  })
		: 0;

	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			{/* Background video clips */}
			<VideoSequencer clips={videoClips} />

			{/* Voiceover audio */}
			<Audio src={staticFile(audioPath)} />

			{/* Background music (lower volume) */}
			{backgroundMusicPath && (
				<Audio src={staticFile(backgroundMusicPath)} volume={musicVolume} />
			)}

			{/* Animated captions */}
			<CaptionOverlay timestamps={timestamps} fps={fps} />

			{/* Optional title overlay at start */}
			{title && frame < 60 && (
				<AbsoluteFill
					style={{
						justifyContent: 'flex-start',
						alignItems: 'center',
						paddingTop: 100,
					}}
				>
					<div
						style={{
							fontSize: 48,
							fontWeight: 'bold',
							color: 'white',
							textAlign: 'center',
							textShadow: '0 2px 10px rgba(0,0,0,0.8)',
							opacity: interpolate(frame, [0, 15, 45, 60], [0, 1, 1, 0]),
							padding: '0 40px',
						}}
					>
						{title}
					</div>
				</AbsoluteFill>
			)}
		</AbsoluteFill>
	);
};
