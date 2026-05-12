'use client';

import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, Legend } from 'recharts';

const data = [
    { name: 'Jan', successful: 1200, failed: 100 },
    { name: 'Feb', successful: 1350, failed: 120 },
    { name: 'Mar', successful: 1500, failed: 150 },
    { name: 'Apr', successful: 1450, failed: 130 },
    { name: 'May', successful: 1600, failed: 140 },
    { name: 'Jun', successful: 1750, failed: 160 },
    { name: 'Jul', successful: 1800, failed: 170 },
    { name: 'Aug', successful: 1900, failed: 180 },
    { name: 'Sep', successful: 2000, failed: 200 },
    { name: 'Oct', successful: 2100, failed: 210 },
    { name: 'Nov', successful: 2200, failed: 220 },
    { name: 'Dec', successful: 2400, failed: 250 },
];

interface TooltipPayloadItem {
    name: string;
    value: number;
    color: string;
}

interface CustomTooltipProps {
    active?: boolean;
    payload?: TooltipPayloadItem[];
    label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
    if (!active || !payload || payload.length === 0) return null;

    const total = payload.reduce((sum, item) => sum + item.value, 0);

    return (
        <div className="rounded-xl border border-white/10 bg-black/80 backdrop-blur-md px-4 py-3 shadow-2xl min-w-[160px]">
            <p className="text-xs font-semibold text-white/50 uppercase tracking-widest mb-2">{label}</p>
            <div className="space-y-1.5">
                {payload.map((item) => (
                    <div key={item.name} className="flex items-center justify-between gap-6">
                        <div className="flex items-center gap-1.5">
                            <span
                                className="inline-block h-2 w-2 rounded-full flex-shrink-0"
                                style={{ backgroundColor: item.color }}
                            />
                            <span className="text-xs text-white/60">{item.name}</span>
                        </div>
                        <span className="text-xs font-semibold text-white">{item.value.toLocaleString()}</span>
                    </div>
                ))}
            </div>
            <div className="mt-2 pt-2 border-t border-white/10 flex justify-between">
                <span className="text-xs text-white/40">Total</span>
                <span className="text-xs font-bold text-white">{total.toLocaleString()}</span>
            </div>
        </div>
    );
}

export function OverviewChart() {
    return (
        <ResponsiveContainer width="100%" height={350}>
            <BarChart data={data} barCategoryGap="30%">
                <XAxis
                    dataKey="name"
                    stroke="#888888"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                />
                <YAxis
                    stroke="#888888"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value) => `${value}`}
                />
                <Tooltip
                    content={<CustomTooltip />}
                    cursor={{ fill: 'rgba(255,255,255,0.04)', radius: 6 }}
                    wrapperStyle={{ outline: 'none' }}
                />
                <Legend />
                <Bar
                    dataKey="successful"
                    name="Successful Conversations"
                    fill="#40e3aaff"
                    fillOpacity={0.2}
                    stroke="#40e3aaff"
                    strokeWidth={1}
                    stackId="a"
                    radius={[0, 0, 4, 4]}
                />
                <Bar
                    dataKey="failed"
                    name="Failed"
                    fill="#dd6a6aff"
                    fillOpacity={0.2}
                    stroke="#ef4444"
                    strokeWidth={1}
                    stackId="a"
                    radius={[4, 4, 0, 0]}
                />
            </BarChart>
        </ResponsiveContainer>
    );
}
