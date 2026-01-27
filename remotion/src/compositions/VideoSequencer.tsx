import React from 'react';
import {Sequence, Video, useCurrentFrame, interpolate, staticFile} from 'remotion';

interface VideoClip {
	filepath: string;
	duration: number;
	startFrame: number;
}

export interface VideoSequencerProps {
	clips: VideoClip[];
}

export const VideoSequencer: React.FC<VideoSequencerProps> = ({clips}) => {
	const frame = useCurrentFrame();

	return (
		<>
			{clips.map((clip, index) => {
				const nextClip = clips[index + 1];
				const transitionFrames = 10; // 10 frames for crossfade

				// Calculate opacity for crossfade
				const opacity = nextClip
					? interpolate(
							frame,
							[
								clip.startFrame + clip.duration - transitionFrames,
								clip.startFrame + clip.duration,
							],
							[1, 0],
							{
								extrapolateLeft: 'clamp',
								extrapolateRight: 'clamp',
							}
					  )
					: 1;

				return (
					<Sequence
						key={`clip-${index}`}
						from={clip.startFrame}
						durationInFrames={clip.duration}
					>
						<Video
							src={staticFile(clip.filepath)}
							style={{
								width: '100%',
								height: '100%',
								objectFit: 'cover',
								opacity,
							}}
						/>
					</Sequence>
				);
			})}
		</>
	);
};
