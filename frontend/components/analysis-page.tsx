"use client"

import { motion } from "framer-motion"
import { ArrowLeft, Activity, Move3D, FileText, TrendingUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts"

interface AnalysisPageProps {
  onBack: () => void
}

// Mock data for charts
const energyData = Array.from({ length: 30 }, (_, i) => ({
  time: i * 6,
  energy: 40 + Math.sin(i * 0.5) * 30 + Math.random() * 20,
  average: 55,
}))

const jointAngleData = Array.from({ length: 30 }, (_, i) => ({
  time: i * 6,
  shoulder: 45 + Math.sin(i * 0.3) * 25,
  elbow: 90 + Math.cos(i * 0.4) * 40,
  knee: 120 + Math.sin(i * 0.5) * 30,
}))

export function AnalysisPage({ onBack }: AnalysisPageProps) {
  const analysisMetrics = [
    { label: "Peak Energy", value: "94.2%", change: "+12.3%", icon: Activity },
    { label: "Movement Range", value: "2.8m", change: "+0.4m", icon: Move3D },
    { label: "Sync Score", value: "87.5", change: "+5.2", icon: TrendingUp },
    { label: "Total Moves", value: "342", change: "analyzed", icon: FileText },
  ]

  return (
    <div className="relative h-full w-full flex flex-col p-8 overflow-y-auto">
      {/* Back button */}
      <motion.div
        className="absolute top-8 left-8 z-10"
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.2 }}
      >
        <Button
          variant="ghost"
          size="sm"
          onClick={onBack}
          className="text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Video
        </Button>
      </motion.div>

      {/* Title */}
      <motion.div
        className="text-center mt-16 mb-8"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-2">
          Motion Analysis
        </h2>
        <p className="text-muted-foreground">
          AI-powered performance insights
        </p>
      </motion.div>

      {/* Metrics cards */}
      <motion.div
        className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-6xl mx-auto w-full mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        {analysisMetrics.map((metric, index) => (
          <motion.div
            key={metric.label}
            className="glass rounded-xl p-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + index * 0.1 }}
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-accent/20 flex items-center justify-center">
                <metric.icon className="w-5 h-5 text-accent" />
              </div>
              <span className="text-xs text-muted-foreground">{metric.label}</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{metric.value}</p>
            <p className="text-xs text-accent mt-1">{metric.change}</p>
          </motion.div>
        ))}
      </motion.div>

      {/* Charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-6xl mx-auto w-full">
        {/* Energy Graph */}
        <motion.div
          className="glass rounded-xl p-6"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
        >
          <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-accent" />
            Energy Level Over Time
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={energyData}>
                <defs>
                  <linearGradient id="energyGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ff6b9d" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ff6b9d" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis
                  dataKey="time"
                  stroke="rgba(255,255,255,0.3)"
                  tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 10 }}
                  tickFormatter={(value) => `${value}s`}
                />
                <YAxis
                  stroke="rgba(255,255,255,0.3)"
                  tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 10 }}
                  tickFormatter={(value) => `${value}%`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(0,0,0,0.8)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                  }}
                  labelStyle={{ color: "white" }}
                />
                <Area
                  type="monotone"
                  dataKey="energy"
                  stroke="#ff6b9d"
                  strokeWidth={2}
                  fill="url(#energyGradient)"
                />
                <Line
                  type="monotone"
                  dataKey="average"
                  stroke="rgba(255,255,255,0.3)"
                  strokeDasharray="5 5"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Joint Angle Graph */}
        <motion.div
          className="glass rounded-xl p-6"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.5 }}
        >
          <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
            <Move3D className="w-5 h-5 text-accent" />
            Joint Angles Analysis
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={jointAngleData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis
                  dataKey="time"
                  stroke="rgba(255,255,255,0.3)"
                  tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 10 }}
                  tickFormatter={(value) => `${value}s`}
                />
                <YAxis
                  stroke="rgba(255,255,255,0.3)"
                  tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 10 }}
                  tickFormatter={(value) => `${value}°`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(0,0,0,0.8)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                  }}
                  labelStyle={{ color: "white" }}
                />
                <Line
                  type="monotone"
                  dataKey="shoulder"
                  stroke="#4ecdc4"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="elbow"
                  stroke="#ff6b9d"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="knee"
                  stroke="#ffd93d"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center justify-center gap-6 mt-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#4ecdc4]" />
              <span className="text-xs text-muted-foreground">Shoulder</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#ff6b9d]" />
              <span className="text-xs text-muted-foreground">Elbow</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#ffd93d]" />
              <span className="text-xs text-muted-foreground">Knee</span>
            </div>
          </div>
        </motion.div>

        {/* 3D Trajectory Visualization Placeholder */}
        <motion.div
          className="glass rounded-xl p-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
            <Move3D className="w-5 h-5 text-accent" />
            3D Movement Trajectory
          </h3>
          <div className="h-64 flex items-center justify-center relative overflow-hidden rounded-lg bg-secondary/30">
            {/* 3D grid floor */}
            <div
              className="absolute inset-0"
              style={{
                background:
                  "linear-gradient(to bottom, transparent 50%, rgba(255,107,157,0.05) 100%)",
              }}
            />
            <svg
              className="absolute inset-0 w-full h-full"
              viewBox="0 0 200 200"
              preserveAspectRatio="xMidYMid meet"
            >
              {/* Grid lines */}
              {Array.from({ length: 10 }).map((_, i) => (
                <g key={i}>
                  <line
                    x1={20 + i * 18}
                    y1="50"
                    x2={20 + i * 18 - 30}
                    y2="180"
                    stroke="rgba(255,255,255,0.1)"
                    strokeWidth="0.5"
                  />
                  <line
                    x1="20"
                    y1={50 + i * 14}
                    x2="180"
                    y2={50 + i * 14 + 20}
                    stroke="rgba(255,255,255,0.1)"
                    strokeWidth="0.5"
                  />
                </g>
              ))}
              {/* Trajectory path */}
              <motion.path
                d="M60 140 Q80 100 100 120 T140 100 T160 80"
                fill="none"
                stroke="url(#trajectoryGrad)"
                strokeWidth="3"
                strokeLinecap="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 2, ease: "easeInOut" }}
              />
              <defs>
                <linearGradient id="trajectoryGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#4ecdc4" />
                  <stop offset="50%" stopColor="#ff6b9d" />
                  <stop offset="100%" stopColor="#ffd93d" />
                </linearGradient>
              </defs>
              {/* Points along trajectory */}
              <motion.circle
                cx="60"
                cy="140"
                r="4"
                fill="#4ecdc4"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.5 }}
              />
              <motion.circle
                cx="100"
                cy="120"
                r="4"
                fill="#ff6b9d"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 1 }}
              />
              <motion.circle
                cx="160"
                cy="80"
                r="4"
                fill="#ffd93d"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 1.5 }}
              />
            </svg>
            <p className="absolute bottom-4 text-xs text-muted-foreground">
              Interactive 3D view available in full analysis
            </p>
          </div>
        </motion.div>

        {/* Report Panel */}
        <motion.div
          className="glass rounded-xl p-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
        >
          <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-accent" />
            AI Performance Summary
          </h3>
          <div className="space-y-4 text-sm">
            <div className="p-3 rounded-lg bg-accent/10 border-l-4 border-accent">
              <p className="font-medium text-foreground mb-1">Overall Assessment</p>
              <p className="text-muted-foreground">
                Exceptional stage presence with consistent energy levels throughout the performance.
                Movement precision is above average for the genre.
              </p>
            </div>
            <div className="p-3 rounded-lg bg-secondary/50">
              <p className="font-medium text-foreground mb-1">Key Highlights</p>
              <ul className="text-muted-foreground space-y-1">
                <li>• Peak energy at 1:24 during chorus section</li>
                <li>• Smooth transitions between formations</li>
                <li>• Strong center presence during solo moments</li>
              </ul>
            </div>
            <div className="p-3 rounded-lg bg-secondary/50">
              <p className="font-medium text-foreground mb-1">Technical Notes</p>
              <ul className="text-muted-foreground space-y-1">
                <li>• Arm extensions: 92% of maximum range</li>
                <li>• Average jump height: 0.4m</li>
                <li>• Movement velocity: 2.3 m/s peak</li>
              </ul>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Footer */}
      <motion.div
        className="text-center mt-12 mb-8"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
      >
        <p className="text-xs text-muted-foreground">
          Analysis powered by AI computer vision • Face tracking • Pose estimation • Motion analysis
        </p>
      </motion.div>
    </div>
  )
}
