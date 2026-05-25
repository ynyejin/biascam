"use client"

import dynamic from "next/dynamic"
import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import {
  ArrowLeft,
  Activity,
  Move3D,
  FileText,
  TrendingUp,
  Loader2,
} from "lucide-react"
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

interface EnergyRow {
  time: number
  upper_energy: number
  lower_energy: number
  total_energy: number
  average?: number
}

interface AngleRow {
  time: number
  joint: string
  angle: number
}

interface TrajectoryRow {
  time: number
  joint: string
  x: number
  y: number
  z: number
}

interface AnalysisDataResponse {
  energy_data: EnergyRow[]
  angle_data: AngleRow[]
  trajectory_data: TrajectoryRow[]
}

interface AnalysisResultResponse {
  message: string
  energy_graph: string
  angle_graph: string
  trajectory_graph: string
  report: string
}

interface AngleChartRow {
  time: number
  left_elbow?: number
  right_elbow?: number
  left_knee?: number
  right_knee?: number
}

export function AnalysisPage({ onBack }: AnalysisPageProps) {
  const [energyData, setEnergyData] = useState<EnergyRow[]>([])
  const [angleData, setAngleData] = useState<AngleChartRow[]>([])
  const [trajectoryData, setTrajectoryData] = useState<TrajectoryRow[]>([])
  const [report, setReport] = useState<string>("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const Plot = dynamic(() => import("react-plotly.js"), {
    ssr: false,
  })

  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        const [dataResponse, resultResponse] = await Promise.all([
          fetch("http://127.0.0.1:8000/analysis-data"),
          fetch("http://127.0.0.1:8000/analysis-results"),
        ])

        if (!dataResponse.ok || !resultResponse.ok) {
          throw new Error("Failed to fetch analysis data")
        }

        const data: AnalysisDataResponse = await dataResponse.json()
        const result: AnalysisResultResponse = await resultResponse.json()

        const energyAverage =
          data.energy_data.length > 0
            ? data.energy_data.reduce(
                (sum, row) => sum + row.total_energy,
                0
              ) / data.energy_data.length
            : 0

        const formattedEnergyData = data.energy_data.map((row) => ({
          ...row,
          time: Number(row.time.toFixed(2)),
          average: energyAverage,
        }))

        const groupedAngles: Record<string, AngleChartRow> = {}

        data.angle_data.forEach((row) => {
          const time = Number(row.time.toFixed(2))
          const key = String(time)

          if (!groupedAngles[key]) {
            groupedAngles[key] = { time }
          }

          if (
            row.joint === "left_elbow" ||
            row.joint === "right_elbow" ||
            row.joint === "left_knee" ||
            row.joint === "right_knee"
          ) {
            groupedAngles[key][row.joint] = row.angle
          }
        })

        setEnergyData(formattedEnergyData)
        setAngleData(Object.values(groupedAngles))
        setTrajectoryData(data.trajectory_data)
        setReport(result.report)
      } catch (err) {
        console.error(err)
        setError("분석 결과를 불러오지 못했습니다.")
      } finally {
        setLoading(false)
      }
    }

    fetchAnalysis()
  }, [])

  const peakEnergy =
    energyData.length > 0
      ? Math.max(...energyData.map((row) => row.total_energy))
      : 0

  const totalMoves = energyData.length

  const analysisMetrics = [
    {
      label: "Peak Energy",
      value: peakEnergy.toFixed(1),
      change: "max",
      icon: Activity,
    },
    {
      label: "Movement Range",
      value: "Pseudo-3D",
      change: "tracked",
      icon: Move3D,
    },
    {
      label: "Pose Model",
      value: "MediaPipe",
      change: "active",
      icon: TrendingUp,
    },
    {
      label: "Frames",
      value: String(totalMoves),
      change: "analyzed",
      icon: FileText,
    },
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

      {loading && (
        <div className="flex flex-col items-center justify-center gap-5 mt-20">
          <Loader2 className="w-14 h-14 animate-spin text-pink-400" />
          <p className="text-muted-foreground">Loading analysis results...</p>
        </div>
      )}

      {error && <div className="text-center text-red-400 mt-10">{error}</div>}

      {!loading && !error && (
        <>
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
                  <span className="text-xs text-muted-foreground">
                    {metric.label}
                  </span>
                </div>
                <p className="text-2xl font-bold text-foreground">
                  {metric.value}
                </p>
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
                      <linearGradient
                        id="energyGradient"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="5%"
                          stopColor="#ff6b9d"
                          stopOpacity={0.3}
                        />
                        <stop
                          offset="95%"
                          stopColor="#ff6b9d"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(255,255,255,0.1)"
                    />
                    <XAxis
                      dataKey="time"
                      stroke="rgba(255,255,255,0.3)"
                      tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 10 }}
                      tickFormatter={(value) => `${value}s`}
                    />
                    <YAxis
                      stroke="rgba(255,255,255,0.3)"
                      tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 10 }}
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
                      dataKey="total_energy"
                      name="Total Energy"
                      stroke="#ff6b9d"
                      strokeWidth={2}
                      fill="url(#energyGradient)"
                    />
                    <Line
                      type="monotone"
                      dataKey="average"
                      name="Average"
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
                  <LineChart data={angleData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(255,255,255,0.1)"
                    />
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
                      dataKey="left_elbow"
                      name="Left Elbow"
                      stroke="#4ecdc4"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="right_elbow"
                      name="Right Elbow"
                      stroke="#ff6b9d"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="left_knee"
                      name="Left Knee"
                      stroke="#ffd93d"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="right_knee"
                      name="Right Knee"
                      stroke="#a78bfa"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-4 mt-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#4ecdc4]" />
                  <span className="text-xs text-muted-foreground">
                    Left Elbow
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#ff6b9d]" />
                  <span className="text-xs text-muted-foreground">
                    Right Elbow
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#ffd93d]" />
                  <span className="text-xs text-muted-foreground">
                    Left Knee
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#a78bfa]" />
                  <span className="text-xs text-muted-foreground">
                    Right Knee
                  </span>
                </div>
              </div>
            </motion.div>

            {/* 3D Trajectory Visualization */}
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
                {trajectoryData.length > 0 ? (
                  <Plot
                    data={[
                      {
                        name: "Left Wrist",
                        x: trajectoryData.filter((p) => p.joint === "left_wrist").map((p) => p.x),
                        y: trajectoryData.filter((p) => p.joint === "left_wrist").map((p) => p.y),
                        z: trajectoryData.filter((p) => p.joint === "left_wrist").map((p) => p.z),
                        type: "scatter3d",
                        mode: "lines",
                        line: { width: 6, color: "#ff6b9d" },
                      },
                      {
                        name: "Right Wrist",
                        x: trajectoryData.filter((p) => p.joint === "right_wrist").map((p) => p.x),
                        y: trajectoryData.filter((p) => p.joint === "right_wrist").map((p) => p.y),
                        z: trajectoryData.filter((p) => p.joint === "right_wrist").map((p) => p.z),
                        type: "scatter3d",
                        mode: "lines",
                        line: { width: 6, color: "#4ecdc4" },
                      },
                      {
                        name: "Left Ankle",
                        x: trajectoryData.filter((p) => p.joint === "left_ankle").map((p) => p.x),
                        y: trajectoryData.filter((p) => p.joint === "left_ankle").map((p) => p.y),
                        z: trajectoryData.filter((p) => p.joint === "left_ankle").map((p) => p.z),
                        type: "scatter3d",
                        mode: "lines",
                        line: { width: 6, color: "#ffd93d" },
                      },
                      {
                        name: "Right Ankle",
                        x: trajectoryData.filter((p) => p.joint === "right_ankle").map((p) => p.x),
                        y: trajectoryData.filter((p) => p.joint === "right_ankle").map((p) => p.y),
                        z: trajectoryData.filter((p) => p.joint === "right_ankle").map((p) => p.z),
                        type: "scatter3d",
                        mode: "lines",
                        line: { width: 6, color: "#a78bfa" },
                      },
                    ]}
                    layout={{
                      paper_bgcolor: "rgba(0,0,0,0)",
                      plot_bgcolor: "rgba(0,0,0,0)",

                      scene: {
                        bgcolor: "rgba(0,0,0,0)",

                        xaxis: {
                          color: "white",
                        },

                        yaxis: {
                          color: "white",
                        },

                        zaxis: {
                          color: "white",
                        },

                        camera: {
                          eye: {
                            x: 1.5,
                            y: 1.5,
                            z: 1,
                          },
                        },
                      },

                      margin: {
                        l: 0,
                        r: 0,
                        t: 0,
                        b: 0,
                      },
                    }}
                    config={{
                      displaylogo: false,
                      responsive: true,
                    }}
                    style={{
                      width: "100%",
                      height: "100%",
                    }}
                  />
                ) : (
                  <p className="text-xs text-muted-foreground">
                    No trajectory data available
                  </p>
                )}
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
              <div className="space-y-4 text-sm max-h-64 overflow-y-auto pr-2">
                <div className="p-3 rounded-lg bg-accent/10 border-l-4 border-accent">
                  <p className="font-medium text-foreground mb-1">
                    Motion Analysis Report
                  </p>
                  <pre className="whitespace-pre-wrap text-muted-foreground leading-relaxed font-mono text-xs">
                    {report || "No report available"}
                  </pre>
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
              Analysis powered by AI computer vision • Face tracking • Pose
              estimation • Motion analysis
            </p>
          </motion.div>
        </>
      )}
    </div>
  )
}