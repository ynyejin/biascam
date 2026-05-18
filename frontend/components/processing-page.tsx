"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"

interface ProcessingPageProps {
  onComplete: () => void
}

const processingSteps = [
  { id: 1, label: "Face tracking", icon: "👤" },
  { id: 2, label: "Re-ID matching", icon: "🔍" },
  { id: 3, label: "Motion analysis", icon: "📊" },
  { id: 4, label: "Generating fancam", icon: "🎬" },
]

export function ProcessingPage({ onComplete }: ProcessingPageProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    // Simulate processing steps
    const stepInterval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < processingSteps.length - 1) {
          return prev + 1
        }
        return prev
      })
    }, 1500)

    // Progress bar animation
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(progressInterval)
          setTimeout(onComplete, 500)
          return 100
        }
        return prev + 1
      })
    }, 60)

    return () => {
      clearInterval(stepInterval)
      clearInterval(progressInterval)
    }
  }, [onComplete])

  return (
    <div className="relative h-full w-full flex flex-col items-center justify-center p-8 scanlines">
      {/* HUD-style container */}
      <motion.div
        className="relative w-full max-w-lg"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
      >
        {/* Outer frame */}
        <div className="absolute inset-0 border border-accent/30 rounded-2xl" />
        <div className="absolute inset-2 border border-accent/20 rounded-xl" />

        {/* Corner accents */}
        <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-accent rounded-tl-2xl" />
        <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-accent rounded-tr-2xl" />
        <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-accent rounded-bl-2xl" />
        <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-accent rounded-br-2xl" />

        <div className="p-8 space-y-8">
          {/* Title */}
          <motion.div
            className="text-center"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-2">
              Creating your fancam...
            </h2>
            <p className="text-muted-foreground text-sm">
              AI is processing your video
            </p>
          </motion.div>

          {/* Circular progress */}
          <div className="flex justify-center">
            <div className="relative w-40 h-40">
              {/* Background circle */}
              <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  fill="none"
                  stroke="rgba(255,255,255,0.1)"
                  strokeWidth="6"
                />
                <motion.circle
                  cx="50"
                  cy="50"
                  r="45"
                  fill="none"
                  stroke="url(#progressGradient)"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeDasharray={`${progress * 2.83} 283`}
                  initial={{ strokeDasharray: "0 283" }}
                />
                <defs>
                  <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#ff6b9d" />
                    <stop offset="50%" stopColor="#c44569" />
                    <stop offset="100%" stopColor="#6b5b95" />
                  </linearGradient>
                </defs>
              </svg>

              {/* Center content */}
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-4xl font-bold text-foreground">{progress}%</span>
              </div>

              {/* Spinning ring */}
              <motion.div
                className="absolute inset-0"
                animate={{ rotate: 360 }}
                transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
              >
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-2 h-2 bg-accent rounded-full" />
              </motion.div>
            </div>
          </div>

          {/* Processing steps */}
          <div className="space-y-3">
            {processingSteps.map((step, index) => (
              <motion.div
                key={step.id}
                className={`
                  flex items-center gap-4 p-3 rounded-lg transition-colors
                  ${index <= currentStep ? "bg-accent/10" : "bg-secondary/30"}
                `}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + index * 0.1 }}
              >
                {/* Status indicator */}
                <div
                  className={`
                    w-8 h-8 rounded-full flex items-center justify-center text-sm
                    transition-all duration-300
                    ${
                      index < currentStep
                        ? "bg-accent text-accent-foreground"
                        : index === currentStep
                        ? "bg-accent/50 text-foreground animate-pulse"
                        : "bg-secondary text-muted-foreground"
                    }
                  `}
                >
                  {index < currentStep ? "✓" : step.icon.charAt(0)}
                </div>

                {/* Label */}
                <span
                  className={`
                    font-medium transition-colors
                    ${index <= currentStep ? "text-foreground" : "text-muted-foreground"}
                  `}
                >
                  {step.label}
                </span>

                {/* Loading dots */}
                {index === currentStep && (
                  <div className="ml-auto flex gap-1">
                    {[0, 1, 2].map((dot) => (
                      <motion.div
                        key={dot}
                        className="w-1.5 h-1.5 bg-accent rounded-full"
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{
                          duration: 1,
                          repeat: Infinity,
                          delay: dot * 0.2,
                        }}
                      />
                    ))}
                  </div>
                )}
              </motion.div>
            ))}
          </div>

          {/* Status text */}
          <motion.div
            className="text-center text-xs text-muted-foreground font-mono"
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            [AI_PROCESSOR] Running inference on frame {Math.floor(progress * 3)}...
          </motion.div>
        </div>
      </motion.div>
    </div>
  )
}
