"use client"

import { useState, useCallback } from "react"
import { motion } from "framer-motion"
import { Upload, Film, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"

interface UploadPageProps {
  onUpload: () => void
  onBack: () => void
}

export function UploadPage({ onUpload, onBack }: UploadPageProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleUpload()
  }, [])

  const handleUpload = () => {
    setIsUploading(true)
    // Simulate upload
    setTimeout(() => {
      setIsUploading(false)
      onUpload()
    }, 1500)
  }

  const sampleVideos = [
    { id: 1, name: "BLACKPINK - How You Like That", duration: "3:02" },
    { id: 2, name: "BTS - Dynamite", duration: "3:19" },
    { id: 3, name: "NewJeans - Super Shy", duration: "2:34" },
  ]

  return (
    <div className="relative h-full w-full flex flex-col items-center justify-center p-8">
      {/* Back button */}
      <motion.div
        className="absolute top-8 left-8"
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
      <motion.h2
        className="text-4xl md:text-6xl font-bold text-foreground mb-12 text-center"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        Upload your video
      </motion.h2>

      {/* Upload area */}
      <motion.div
        className={`
          w-full max-w-2xl aspect-video rounded-2xl
          glass transition-all duration-300 cursor-pointer
          flex flex-col items-center justify-center gap-6
          ${isDragging ? "border-accent border-2 bg-accent/10" : "border-border hover:border-accent/50"}
        `}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleUpload}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
      >
        {isUploading ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center gap-4"
          >
            <div className="w-16 h-16 border-4 border-accent border-t-transparent rounded-full animate-spin" />
            <p className="text-muted-foreground">Processing video...</p>
          </motion.div>
        ) : (
          <>
            <motion.div
              animate={{ y: isDragging ? -10 : 0 }}
              transition={{ type: "spring", stiffness: 400 }}
            >
              <Upload className="w-16 h-16 text-muted-foreground" />
            </motion.div>
            <div className="text-center">
              <p className="text-foreground font-medium text-lg">
                Drag & drop a group performance video
              </p>
              <p className="text-muted-foreground text-sm mt-2">
                or click to browse your files
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Film className="w-4 h-4" />
              <span>MP4, MOV, AVI up to 500MB</span>
            </div>
          </>
        )}
      </motion.div>

      {/* Sample videos */}
      <motion.div
        className="mt-12 w-full max-w-2xl"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <p className="text-muted-foreground text-sm mb-4 text-center">
          Or try with a sample video
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {sampleVideos.map((video, index) => (
            <motion.button
              key={video.id}
              className="glass rounded-xl p-4 text-left hover:bg-accent/10 transition-colors group"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + index * 0.1 }}
              onClick={handleUpload}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                  <Film className="w-5 h-5 text-muted-foreground group-hover:text-accent" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-foreground text-sm font-medium truncate">
                    {video.name}
                  </p>
                  <p className="text-muted-foreground text-xs">{video.duration}</p>
                </div>
              </div>
            </motion.button>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
