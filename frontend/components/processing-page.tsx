"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"

interface ProcessingPageProps {
  onComplete: () => void
}

interface ProgressResponse {
  progress: number
  message: string
  done: boolean
  error: string | null
}

const processingSteps = [
  { id: 1, label: "Face tracking", icon: "👤", threshold: 25 },
  { id: 2, label: "Video conversion", icon: "🎞️", threshold: 55 },
  { id: 3, label: "Motion analysis", icon: "📊", threshold: 75 },
  { id: 4, label: "Generating result", icon: "🎬", threshold: 100 },
]

export function ProcessingPage({ onComplete }: ProcessingPageProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [progress, setProgress] = useState(0)
  const [statusMessage, setStatusMessage] = useState("Starting...")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let completed = false

    const fetchProgress = async () => {
      try {
        const response = await fetch("http://127.0.0.1:8000/progress")

        if (!response.ok) {
          throw new Error("Failed to fetch progress")
        }

        const data: ProgressResponse = await response.json()

        const nextProgress = Math.max(0, Math.min(100, data.progress ?? 0))
        setProgress(nextProgress)
        setStatusMessage(data.message ?? "Processing...")

        const stepIndex = processingSteps.findIndex(
          (step) => nextProgress < step.threshold
        )

        if (stepIndex === -1) {
          setCurrentStep(processingSteps.length - 1)
        } else {
          setCurrentStep(stepIndex)
        }

        if (data.error) {
          setError(data.error)
          completed = true
          return
        }

        if (data.done && nextProgress >= 100 && !completed) {
          completed = true
          setTimeout(() => {
            onComplete()
          }, 700)
        }
      } catch (err) {
        console.error(err)
        setError("백엔드 진행 상태를 불러오지 못했습니다.")
      }
    }

    fetchProgress()

    const interval = setInterval(() => {
      if (!completed) {
        fetchProgress()
      }
    }, 1000)

    return () => {
      completed = true
      clearInterval(interval)
    }
  }, [onComplete])

  return (
    <div className="relative h-full w-full flex flex-col items-center justify-center p-8 scanlines">
      <motion.div
        className="relative w-full max-w-lg"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
      >
        <div className="absolute inset-0 border border-accent/30 rounded-2xl" />
        <div className="absolute inset-2 border border-accent/20 rounded-xl" />

        <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-accent rounded-tl-2xl" />
        <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-accent rounded-tr-2xl" />
        <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-accent rounded-bl-2xl" />
        <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-accent rounded-br-2xl" />

        <div className="p-8 space-y-8">
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
              {error ? "Processing failed" : statusMessage}
            </p>
          </motion.div>

          <div className="flex justify-center">
            <div className="relative w-40 h-40">
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
                  animate={{ strokeDasharray: `${progress * 2.83} 283` }}
                  transition={{ duration: 0.4 }}
                />
                <defs>
                  <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#ff6b9d" />
                    <stop offset="50%" stopColor="#c44569" />
                    <stop offset="100%" stopColor="#6b5b95" />
                  </linearGradient>
                </defs>
              </svg>

              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-4xl font-bold text-foreground">
                  {progress}%
                </span>
              </div>

              {!error && progress < 100 && (
                <motion.div
                  className="absolute inset-0"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                >
                  <div className="absolute top-0 left-1/2 -translate-x-1/2 w-2 h-2 bg-accent rounded-full" />
                </motion.div>
              )}
            </div>
          </div>

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

                <span
                  className={`
                    font-medium transition-colors
                    ${index <= currentStep ? "text-foreground" : "text-muted-foreground"}
                  `}
                >
                  {step.label}
                </span>

                {index === currentStep && !error && progress < 100 && (
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

          <motion.div
            className={`text-center text-xs font-mono ${
              error ? "text-red-400" : "text-muted-foreground"
            }`}
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            {error
              ? `[ERROR] ${error}`
              : `[AI_PROCESSOR] ${statusMessage}`}
          </motion.div>
        </div>
      </motion.div>
    </div>
  )
}