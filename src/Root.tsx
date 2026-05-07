import { Composition } from 'remotion';
import { FinancialReport } from './FinancialReport';
import './index.css';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Main"
        component={FinancialReport}
        durationInFrames={330}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
