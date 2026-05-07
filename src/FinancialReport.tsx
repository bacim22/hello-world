import React from 'react';
import {
  AbsoluteFill,
  Img,
  staticFile,
  Series,
} from 'remotion';
import { Animated, Move, Fade, Scale } from 'remotion-animated';
import { TrendingUp, BarChart3, ShieldCheck, Activity } from 'lucide-react';
import data from './data.json';

interface Metric {
  label: string;
  value: string;
  change: string;
}

interface Method {
  name: string;
  estimate: string;
}

const TitleCard: React.FC = () => {
  return (
    <AbsoluteFill className="bg-slate-900 flex items-center justify-center text-white p-20">
      <Animated
        animations={[
          Fade({ initial: 0, to: 1, start: 0, duration: 30 }),
          Move({ initialY: 50, y: 0, start: 0, duration: 30 }),
        ]}
      >
        <div className="flex flex-col items-center text-center">
          <Img src={staticFile('logo.svg')} className="w-32 h-32 mb-8" />
          <h1 className="text-6xl font-bold mb-4">{data.companyName}</h1>
          <h2 className="text-4xl text-blue-400">{data.reportTitle}</h2>
          <p className="text-2xl text-slate-400 mt-8">Period Ending: {data.periodEnding}</p>
        </div>
      </Animated>
    </AbsoluteFill>
  );
};

const MetricCard: React.FC<{
  label: string;
  value: string;
  change: string;
  index: number;
}> = ({ label, value, change, index }) => {
  return (
    <Animated
      animations={[
        Fade({ initial: 0, to: 1, start: index * 10, duration: 20 }),
        Scale({ initial: 0.8, start: index * 10, duration: 20 }),
      ]}
    >
      <div className="bg-slate-800 p-8 rounded-3xl border border-slate-700 shadow-2xl">
        <p className="text-slate-400 text-xl mb-2">{label}</p>
        <p className="text-5xl font-bold text-white mb-2">{value}</p>
        <p className={`text-xl ${change.startsWith('+') ? 'text-emerald-400' : 'text-rose-400'}`}>
          {change} vs Previous
        </p>
      </div>
    </Animated>
  );
};

const KeyMetrics: React.FC = () => {
  return (
    <AbsoluteFill className="bg-slate-900 p-20">
      <h2 className="text-4xl font-bold text-white mb-12 flex items-center">
        <TrendingUp className="mr-4 text-blue-400" /> Executive Summary
      </h2>
      <div className="grid grid-cols-3 gap-8">
        {(data.keyMetrics as Metric[]).map((m, i) => (
          <MetricCard key={m.label} {...m} index={i} />
        ))}
      </div>
    </AbsoluteFill>
  );
};

const MethodRow: React.FC<{ name: string; estimate: string; index: number }> = ({
  name,
  estimate,
  index,
}) => {
  return (
    <Animated
      animations={[
        Fade({ initial: 0, to: 1, start: index * 5, duration: 15 }),
        Move({ initialX: -30, x: 0, start: index * 5, duration: 15 }),
      ]}
    >
      <div className="flex justify-between items-center p-6 bg-slate-800/50 rounded-xl mb-4 border-l-4 border-blue-500">
        <span className="text-2xl text-white">{name}</span>
        <span className="text-2xl font-mono text-blue-300">{estimate}</span>
      </div>
    </Animated>
  );
};

const IBNRSummary: React.FC = () => {
  return (
    <AbsoluteFill className="bg-slate-900 p-20">
      <div className="flex gap-12 h-full">
        <div className="flex-1">
          <h2 className="text-4xl font-bold text-white mb-12 flex items-center">
            <BarChart3 className="mr-4 text-blue-400" /> Reserving Methods
          </h2>
          {(data.methods as Method[]).map((m, i) => (
            <MethodRow key={m.name} {...m} index={i} />
          ))}
        </div>
        <div className="flex-1 bg-slate-800/30 p-12 rounded-3xl border border-slate-700">
          <h2 className="text-4xl font-bold text-white mb-8 flex items-center">
            <ShieldCheck className="mr-4 text-emerald-400" /> Audit Highlights
          </h2>
          <ul className="space-y-6">
            {(data.auditLogHighlights as string[]).map((h, i) => (
              <Animated
                key={i}
                animations={[Fade({ initial: 0, to: 1, start: 30 + i * 10, duration: 20 })]}
              >
                <li className="text-xl text-slate-300 leading-relaxed border-b border-slate-700 pb-4 italic">
                  "{h}"
                </li>
              </Animated>
            ))}
          </ul>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const ClosingCard: React.FC = () => {
  return (
    <AbsoluteFill className="bg-slate-900 flex items-center justify-center text-white">
      <Animated animations={[Scale({ initial: 0, start: 0, duration: 40 })]}>
        <div className="text-center">
          <Activity className="w-24 h-24 text-blue-400 mx-auto mb-8 animate-pulse" />
          <h1 className="text-5xl font-bold">Confidential & Proprietary</h1>
          <p className="text-2xl text-slate-400 mt-4">{data.companyName} © 2025</p>
        </div>
      </Animated>
    </AbsoluteFill>
  );
};

export const FinancialReport: React.FC = () => {
  return (
    <Series>
      <Series.Sequence durationInFrames={60}>
        <TitleCard />
      </Series.Sequence>
      <Series.Sequence durationInFrames={90}>
        <KeyMetrics />
      </Series.Sequence>
      <Series.Sequence durationInFrames={120}>
        <IBNRSummary />
      </Series.Sequence>
      <Series.Sequence durationInFrames={60}>
        <ClosingCard />
      </Series.Sequence>
    </Series>
  );
};
