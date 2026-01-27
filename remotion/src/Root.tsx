import {Composition} from 'remotion';
import {HelloWorld} from './HelloWorld';
import {TikTokVideo} from './compositions/TikTokVideo';

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Composition
				id="HelloWorld"
				component={HelloWorld}
				durationInFrames={150}
				fps={30}
				width={1920}
				height={1080}
				defaultProps={{
					titleText: 'Welcome to Remotion',
					titleColor: '#000000',
					logoColor1: '#91EAE4',
					logoColor2: '#86A8E7',
				}}
			/>
			<Composition
				id="TikTokVideo"
				component={TikTokVideo}
				durationInFrames={900}
				fps={30}
				width={1080}
				height={1920}
				defaultProps={{
					audioPath: 'audio/generated/voiceover_demo.mp3',
					videoClips: [
						{
							filepath: 'assets/footage/mongolia/clip1.mp4',
							duration: 150,
							startFrame: 0,
						},
						{
							filepath: 'assets/footage/mongolia/clip2.mp4',
							duration: 150,
							startFrame: 150,
						},
					],
					timestamps: [
						{word: 'Watch', start: 0, end: 0.4},
						{word: 'this!', start: 0.4, end: 0.8},
					],
					title: 'Amazing Tribal Culture',
				}}
			/>
		</>
	);
};
