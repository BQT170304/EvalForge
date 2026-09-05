import React from 'react';

interface RadarDataPoint {
  label: string;
  value: number; // 0 to 1 or 0 to 100
  threshold?: number;
}

interface RadarChartProps {
  data: RadarDataPoint[];
  size?: number;
  maxValue?: number;
}

export const RadarChart: React.FC<RadarChartProps> = ({
  data,
  size = 280,
  maxValue = 1.0,
}) => {
  if (!data || data.length < 3) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-400 text-xs italic">
        Requires at least 3 metrics for radar representation
      </div>
    );
  }

  const center = size / 2;
  const radius = size * 0.38;
  const total = data.length;
  const angleSlice = (Math.PI * 2) / total;

  // Concentric levels (rings)
  const levels = [0.25, 0.5, 0.75, 1.0];

  const getCoordinates = (index: number, val: number) => {
    const angle = angleSlice * index - Math.PI / 2;
    const r = (val / maxValue) * radius;
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
    };
  };

  // Polygon points for the value polygon
  const points = data
    .map((d, i) => {
      const coord = getCoordinates(i, Math.min(Math.max(d.value, 0), maxValue));
      return `${coord.x},${coord.y}`;
    })
    .join(' ');

  // Polygon points for threshold line (if specified)
  const thresholdPoints = data
    .map((d, i) => {
      const t = d.threshold !== undefined ? d.threshold : 0.7;
      const coord = getCoordinates(i, t);
      return `${coord.x},${coord.y}`;
    })
    .join(' ');

  return (
    <div className="relative flex flex-col items-center justify-center">
      <svg width={size} height={size} className="overflow-visible">
        <defs>
          <radialGradient id="radarGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#2563eb" stopOpacity="0.1" />
          </radialGradient>
        </defs>

        {/* Circular / Polygonal background grid levels */}
        {levels.map((level, lvlIdx) => (
          <circle
            key={lvlIdx}
            cx={center}
            cy={center}
            r={radius * level}
            fill="none"
            stroke="#1d3778"
            strokeDasharray={lvlIdx === levels.length - 1 ? 'none' : '3 3'}
            strokeWidth="1"
            opacity="0.6"
          />
        ))}

        {/* Axis lines from center */}
        {data.map((_, i) => {
          const coord = getCoordinates(i, maxValue);
          return (
            <line
              key={i}
              x1={center}
              y1={center}
              x2={coord.x}
              y2={coord.y}
              stroke="#1e3a8a"
              strokeWidth="1"
              opacity="0.5"
            />
          );
        })}

        {/* Threshold contour polygon (subtle dashed cyan) */}
        <polygon
          points={thresholdPoints}
          fill="none"
          stroke="#06b6d4"
          strokeWidth="1.5"
          strokeDasharray="4 3"
          opacity="0.75"
        />

        {/* Data polygon filled with glowing dark blue / cyan gradient */}
        <polygon
          points={points}
          fill="url(#radarGlow)"
          stroke="#60a5fa"
          strokeWidth="2.5"
          className="transition-all duration-500 ease-out drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]"
        />

        {/* Data points */}
        {data.map((d, i) => {
          const coord = getCoordinates(i, Math.min(Math.max(d.value, 0), maxValue));
          const isPassed = d.value >= (d.threshold ?? 0.7);
          return (
            <g key={i}>
              <circle
                cx={coord.x}
                cy={coord.y}
                r="4.5"
                fill={isPassed ? '#38bdf8' : '#f43f5e'}
                stroke="#0b1633"
                strokeWidth="2"
                className="transition-all duration-300 hover:r-6 cursor-pointer"
              />
            </g>
          );
        })}

        {/* Labels positioned outside radius */}
        {data.map((d, i) => {
          const angle = angleSlice * i - Math.PI / 2;
          const labelDist = radius + 22;
          const lx = center + labelDist * Math.cos(angle);
          const ly = center + labelDist * Math.sin(angle);
          const isPassed = d.value >= (d.threshold ?? 0.7);

          return (
            <text
              key={i}
              x={lx}
              y={ly}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-[10px] font-mono select-none"
              fill={isPassed ? '#93c5fd' : '#fca5a5'}
            >
              {d.label.length > 12 ? `${d.label.slice(0, 10)}..` : d.label}
              <tspan x={lx} dy="11" fill="#cbd5e1" fontSize="9px" fontWeight="600">
                {(d.value * 100).toFixed(0)}%
              </tspan>
            </text>
          );
        })}
      </svg>
      <div className="flex items-center gap-4 mt-2 text-[11px] text-slate-400">
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block shadow-[0_0_6px_#3b82f6]"></span>
          Score
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-3 h-0.5 border-b border-cyan-400 border-dashed inline-block"></span>
          Threshold
        </span>
      </div>
    </div>
  );
};
