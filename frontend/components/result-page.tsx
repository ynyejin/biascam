"use client"

import { motion } from "framer-motion"
import { ArrowLeft, Play, Pause, Download, Share2, BarChart2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useState } from "react"

interface ResultPageProps {
  onAnalysis: () => void
  onBack: () => void
  selectedFace: number | null
}

export function ResultPage({ onAnalysis, onBack }: ResultPageProps) {
  const [isPlaying, setIsPlaying] = useState(false)

  return (
    <div className="relative h-full w-full flex flex-col items-center p-8 overflow-y-auto">
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
          Back
        </Button>
      </motion.div>

      {/* Title */}
      <motion.div
        className="text-center mt-16 mb-8"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h2 className="text-4xl md:text-5xl font-bold text-foreground mb-2">
          Your{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-pink-400 to-purple-400">
            BiasCam
          </span>{" "}
          is ready
        </h2>
        <p className="text-muted-foreground">
          Your personalized fancam has been generated
        </p>
      </motion.div>

      {/* Video player container */}
      <motion.div
        className="w-full max-w-4xl"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        {/* Video frame with cinematic styling */}
        <div className="relative aspect-video rounded-2xl overflow-hidden glass">
          {/* Placeholder video content */}
          <div className="absolute inset-0 bg-gradient-to-br from-pink-900/40 via-purple-900/40 to-indigo-900/40">
            {/* Grid overlay */}
            <div
              className="absolute inset-0 opacity-20"
              style={{
                backgroundImage:
                  "linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)",
                backgroundSize: "30px 30px",
              }}
            />

            {/* Center play button */}
            <motion.button
              className="absolute inset-0 flex items-center justify-center"
              onClick={() => setIsPlaying(!isPlaying)}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <div className="w-20 h-20 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center border border-white/30">
                {isPlaying ? (
                  <Pause className="w-8 h-8 text-white ml-0" />
                ) : (
                  <Play className="w-8 h-8 text-white ml-1" />
                )}
              </div>
            </motion.button>

            {/* Video info overlay */}
            <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black/80 to-transparent">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white font-semibold text-lg">Generated Fancam</p>
                  <p className="text-white/60 text-sm">Member 1 • 3:02</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-1 bg-accent/20 rounded text-xs text-accent">
                    AI Generated
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mt-4">
                <div className="h-1 bg-white/20 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-pink-400 to-purple-400"
                    initial={{ width: "0%" }}
                    animate={{ width: isPlaying ? "100%" : "35%" }}
                    transition={{ duration: isPlaying ? 180 : 0.3 }}
                  />
                </div>
                <div className="flex justify-between mt-2 text-xs text-white/60">
                  <span>1:04</span>
                  <span>3:02</span>
                </div>
              </div>
            </div>

            {/* Face tracking indicator */}
            <motion.div
              className="absolute top-6 left-6 flex items-center gap-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <span className="text-xs text-white/80 font-mono">
                TRACKING ACTIVE
              </span>
            </motion.div>
          </div>
        </div>

        {/* Action buttons */}
        <motion.div
          className="flex flex-wrap items-center justify-center gap-4 mt-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Button
            size="lg"
            className="bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600 text-white"
            onClick={onAnalysis}
          >
            <BarChart2 className="w-5 h-5 mr-2" />
            View Analysis
          </Button>
          <Button size="lg" variant="outline" className="border-border">
            <Download className="w-5 h-5 mr-2" />
            Download
          </Button>
          <Button size="lg" variant="outline" className="border-border">
            <Share2 className="w-5 h-5 mr-2" />
            Share
          </Button>
        </motion.div>

        {/* Stats cards */}
        <motion.div
          className="grid grid-cols-3 gap-4 mt-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          {[
            { label: "Frames Processed", value: "5,432" },
            { label: "Face Detections", value: "4,891" },
            { label: "Tracking Accuracy", value: "98.7%" },
          ].map((stat, index) => (
            <div
              key={stat.label}
              className="glass rounded-xl p-4 text-center"
            >
              <p className="text-2xl font-bold text-foreground">{stat.value}</p>
              <p className="text-xs text-muted-foreground mt-1">{stat.label}</p>
            </div>
          ))}
        </motion.div>
      </motion.div>
    </div>
  )
}
