"use client"

import { useEffect, useRef, useState } from "react"
import { motion } from "framer-motion"
import { ArrowLeft, Check, Loader2, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"

interface DetectedFace {
  id: number
  image_url: string
  bbox: number[]
  score: number
}

interface FaceSelectionPageProps {
  onSelect: (faceId: number) => void
  onBack: () => void
}

export function FaceSelectionPage({ onSelect, onBack }: FaceSelectionPageProps) {
  const [faces, setFaces] = useState<DetectedFace[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [hoveredId, setHoveredId] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const hasFetchedRef = useRef(false)

  const fetchDetectedFaces = async () => {
    setIsLoading(true)
    setError(null)
    setFaces([])

    try {
      const response = await fetch("http://127.0.0.1:8000/detect-faces", {
        method: "POST",
      })

      if (!response.ok) {
        throw new Error(`Face detection failed: ${response.status}`)
      }

      const data = await response.json()
      console.log("Detected faces:", data)

      if (!data.faces || data.faces.length === 0) {
        setFaces([])
        setError("얼굴을 찾지 못했습니다. 얼굴이 잘 보이는 영상으로 다시 시도해주세요.")
      } else {
        setFaces(data.faces)
      }
    } catch (err) {
      console.error("Failed to detect faces:", err)
      setFaces([])
      setError("얼굴 후보를 불러오지 못했습니다. 백엔드 서버를 확인해주세요.")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (hasFetchedRef.current) return

    hasFetchedRef.current = true
    fetchDetectedFaces()
  }, [])

  const handleRetryDetection = () => {
    hasFetchedRef.current = false
    fetchDetectedFaces()
    hasFetchedRef.current = true
  }

  const handleSelect = (id: number) => {
    setSelectedId(id)

    setTimeout(() => {
      onSelect(id)
    }, 300)
  }

  return (
    <div className="relative h-full w-full flex flex-col items-center p-8 overflow-y-auto">
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

      <motion.div
        className="text-center mt-16 mb-12"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h2 className="text-4xl md:text-6xl font-bold text-foreground mb-4">
          {"Who's your"}{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-pink-400 to-purple-400">
            bias
          </span>
          ?
        </h2>

        <p className="text-muted-foreground text-lg">
          Select the clearest face candidate for your favorite member
        </p>
      </motion.div>

      {isLoading && (
        <motion.div
          className="flex flex-col items-center justify-center gap-5 mt-20"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <Loader2 className="w-14 h-14 animate-spin text-pink-400" />
          <p className="text-lg text-muted-foreground">
            Detecting faces from your video...
          </p>
        </motion.div>
      )}

      {!isLoading && error && (
        <motion.div
          className="glass rounded-3xl p-8 max-w-xl w-full text-center mt-10"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <p className="text-red-400 mb-6">{error}</p>

          <div className="flex justify-center gap-3">
            <Button variant="outline" onClick={onBack}>
              Upload Again
            </Button>

            <Button onClick={handleRetryDetection}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry Detection
            </Button>
          </div>
        </motion.div>
      )}

      {!isLoading && !error && faces.length > 0 && (
        <>
          <motion.div
            className="grid grid-cols-2 md:grid-cols-3 gap-6 max-w-4xl w-full px-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            {faces.map((face, index) => (
              <motion.button
                key={face.id}
                className={`
                  relative aspect-[3/4] rounded-2xl overflow-hidden
                  glass transition-all duration-300 group
                  ${
                    selectedId === face.id
                      ? "ring-4 ring-accent ring-offset-4 ring-offset-background"
                      : ""
                  }
                `}
                initial={{ opacity: 0, y: 30, rotateY: -15 }}
                animate={{ opacity: 1, y: 0, rotateY: 0 }}
                transition={{
                  duration: 0.5,
                  delay: 0.1 + index * 0.08,
                  type: "spring",
                  stiffness: 100,
                }}
                onClick={() => handleSelect(face.id)}
                onMouseEnter={() => setHoveredId(face.id)}
                onMouseLeave={() => setHoveredId(null)}
                whileHover={{ scale: 1.03, y: -8 }}
                whileTap={{ scale: 0.97 }}
              >
                <img
                  src={face.image_url}
                  alt={`Detected face ${face.id}`}
                  className="absolute inset-0 w-full h-full object-cover"
                />

                <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent" />

                <motion.div
                  className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/20 to-transparent"
                  initial={{ x: "-100%", y: "-100%" }}
                  animate={
                    hoveredId === face.id
                      ? { x: "100%", y: "100%" }
                      : { x: "-100%", y: "-100%" }
                  }
                  transition={{ duration: 0.6 }}
                />

                <div className="absolute bottom-0 left-0 right-0 p-4 text-left">
                  <p className="text-white font-semibold text-lg">
                    Candidate {index + 1}
                  </p>
                  <p className="text-white/60 text-sm">
                    Score {(face.score * 100).toFixed(1)}%
                  </p>
                </div>

                {selectedId === face.id && (
                  <motion.div
                    className="absolute top-4 right-4 w-8 h-8 bg-accent rounded-full flex items-center justify-center"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 500 }}
                  >
                    <Check className="w-5 h-5 text-accent-foreground" />
                  </motion.div>
                )}

                <div
                  className={`
                    absolute inset-0 rounded-2xl transition-opacity duration-300
                    ${
                      hoveredId === face.id || selectedId === face.id
                        ? "opacity-100"
                        : "opacity-0"
                    }
                  `}
                  style={{
                    boxShadow: "inset 0 0 30px rgba(255,255,255,0.18)",
                  }}
                />
              </motion.button>
            ))}
          </motion.div>

          <motion.p
            className="mt-12 text-muted-foreground text-sm text-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
          >
            Detected {faces.length} face candidates. Choose the clearest image of your bias.
          </motion.p>
        </>
      )}
    </div>
  )
}