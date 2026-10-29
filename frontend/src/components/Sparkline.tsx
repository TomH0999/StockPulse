export function Sparkline({ data, width = 100, height = 28 }: { data?: number[]; width?: number; height?: number }) {
  if (!data || data.length < 2) return <svg width={width} height={height} />;
  const min = Math.min(...data), max = Math.max(...data);
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * width},${height - ((v - min) / (max - min || 1)) * (height - 2) - 1}`).join(' ');
  const up = data[data.length - 1] >= data[0];
  return (
    <svg width={width} height={height} className="shrink-0">
      <polyline points={pts} fill="none" stroke={up ? '#10b981' : '#f43f5e'} strokeWidth="1.5" />
    </svg>
  );
}
