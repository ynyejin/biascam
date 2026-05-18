"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { ArrowLeft, Check } from "lucide-react"
import { Button } from "@/components/ui/button"

interface FaceSelectionPageProps {
  onSelect: (faceId: number) => void
  onBack: () => void
}

// Placeholder face data - these would be actual detected faces
const detectedFaces = [
  { id: 1, name: "Member 1", color: "from-pink-400 to-rose-600" },
  { id: 2, name: "Member 2", color: "from-purple-400 to-indigo-600" },
  { id: 3, name: "Member 3", color: "from-cyan-400 to-blue-600" },
  { id: 4, name: "Member 4", color: "from-amber-400 to-orange-600" },
  { id: 5, name: "Member 5", color: "from-emerald-400 to-teal-600" },
  { id: 6, name: "Member 6", color: "from-fuchsia-400 to-pink-600" },
]

export function FaceSelectionPage({ onSelect, onBack }: FaceSelectionPageProps) {
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [hoveredId, setHoveredId] = useState<number | null>(null)

  const handleSelect = (id: number) => {
    setSelectedId(id)
    // Small delay before navigating
    setTimeout(() => {
      onSelect(id)
    }, 300)
  }

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

      {/* Title section */}
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
          Select your favorite member from the detected faces
        </p>
      </motion.div>

      {/* Face grid - Photo card style */}
      <motion.div
        className="grid grid-cols-2 md:grid-cols-3 gap-6 max-w-4xl w-full px-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        {detectedFaces.map((face, index) => (
          <motion.button
            key={face.id}
            className={`
              relative aspect-[3/4] rounded-2xl overflow-hidden
              glass transition-all duration-300 group
              ${selectedId === face.id ? "ring-4 ring-accent ring-offset-4 ring-offset-background" : ""}
            `}
            initial={{ opacity: 0, y: 30, rotateY: -15 }}
            animate={{ opacity: 1, y: 0, rotateY: 0 }}
            transition={{
              duration: 0.5,
              delay: 0.3 + index * 0.1,
              type: "spring",
              stiffness: 100,
            }}
            onClick={() => handleSelect(face.id)}
            onMouseEnter={() => setHoveredId(face.id)}
            onMouseLeave={() => setHoveredId(null)}
            whileHover={{ scale: 1.03, y: -8 }}
            whileTap={{ scale: 0.97 }}
          >
            {/* Gradient placeholder for face */}
            <div
              className={`absolute inset-0 bg-gradient-to-br ${face.color} opacity-60`}
            />

            {/* Face placeholder circle */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-24 h-24 md:w-32 md:h-32 rounded-full border-4 border-white/30 border-dashed flex items-center justify-center">
                <span className="text-white/50 text-xs text-center px-2">
                  Face will appear here
                </span>
              </div>
            </div>

            {/* Shine effect */}
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

            {/* Name label */}
            <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent">
              <p className="text-white font-semibold text-lg">{face.name}</p>
              <p className="text-white/60 text-sm">Tap to select</p>
            </div>

            {/* Selection checkmark */}
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

            {/* Card border glow */}
            <div
              className={`
                absolute inset-0 rounded-2xl transition-opacity duration-300
                ${hoveredId === face.id || selectedId === face.id ? "opacity-100" : "opacity-0"}
              `}
              style={{
                boxShadow: "inset 0 0 30px rgba(255,255,255,0.1)",
              }}
            />
          </motion.button>
        ))}
      </motion.div>

      {/* Hint text */}
      <motion.p
        className="mt-12 text-muted-foreground text-sm text-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
      >
        These cards can be replaced with actual detected idol faces
      </motion.p>
    </div>
  )
}
