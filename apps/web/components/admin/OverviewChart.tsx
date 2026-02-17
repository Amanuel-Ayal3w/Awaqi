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

export function OverviewChart() {
    return (
        <ResponsiveContainer width="100%" height={350}>
            <BarChart data={data}>
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
                    contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }}
                    itemStyle={{ color: 'var(--foreground)' }}
                    cursor={{ fill: 'transparent' }}
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
