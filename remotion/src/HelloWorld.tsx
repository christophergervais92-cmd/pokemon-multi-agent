import {
	AbsoluteFill,
	interpolate,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';

export const HelloWorld: React.FC<{
	titleText: string;
	titleColor: string;
	logoColor1: string;
	logoColor2: string;
}> = ({titleText, titleColor, logoColor1, logoColor2}) => {
	const frame = useCurrentFrame();
	const videoConfig = useVideoConfig();

	const opacity = interpolate(
		frame,
		[0, 20, videoConfig.durationInFrames - 20, videoConfig.durationInFrames],
		[0, 1, 1, 0],
		{
			extrapolateLeft: 'clamp',
			extrapolateRight: 'clamp',
		}
	);

	return (
		<AbsoluteFill
			style={{
				display: 'flex',
				justifyContent: 'center',
				alignItems: 'center',
				backgroundColor: 'white',
			}}
		>
			<div
				style={{
					fontSize: 100,
					fontWeight: 'bold',
					color: titleColor,
					opacity,
				}}
			>
				{titleText}
			</div>
		</AbsoluteFill>
	);
};
