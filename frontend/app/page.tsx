"use client"

import { useState, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { LandingPage } from "@/components/landing-page"
import { UploadPage } from "@/components/upload-page"
import { FaceSelectionPage } from "@/components/face-selection-page"
import { ProcessingPage } from "@/components/processing-page"
import { ResultPage } from "@/components/result-page"
import { AnalysisPage } from "@/components/analysis-page"

export type AppPage = "landing" | "upload" | "selection" | "processing" | "result" | "analysis"

const pageOrder: AppPage[] = ["landing", "upload", "selection", "processing", "result", "analysis"]

export default function Home() {
  const [currentPage, setCurrentPage] = useState<AppPage>("landing")
  const [direction, setDirection] = useState(1)
  const [selectedFace, setSelectedFace] = useState<number | null>(null)

  const goToPage = useCallback((page: AppPage) => {
    const currentIndex = pageOrder.indexOf(currentPage)
    const nextIndex = pageOrder.indexOf(page)
    setDirection(nextIndex > currentIndex ? 1 : -1)
    setCurrentPage(page)
  }, [currentPage])

  const variants = {
    enter: (direction: number) => ({
      x: direction > 0 ? "100%" : "-100%",
      opacity: 0,
    }),
    center: {
      x: 0,
      opacity: 1,
    },
    exit: (direction: number) => ({
      x: direction > 0 ? "-100%" : "100%",
      opacity: 0,
    }),
  }

  const renderPage = () => {
    switch (currentPage) {
      case "landing":
        return <LandingPage onStart={() => goToPage("upload")} />
      case "upload":
        return <UploadPage onUpload={() => goToPage("selection")} onBack={() => goToPage("landing")} />
      case "selection":
        return (
          <FaceSelectionPage
            onSelect={(faceId) => {
              setSelectedFace(faceId)
              goToPage("processing")
            }}
            onBack={() => goToPage("upload")}
          />
        )
      case "processing":
        return <ProcessingPage onComplete={() => goToPage("result")} />
      case "result":
        return (
          <ResultPage
            onAnalysis={() => goToPage("analysis")}
            onBack={() => goToPage("selection")}
            selectedFace={selectedFace}
          />
        )
      case "analysis":
        return <AnalysisPage onBack={() => goToPage("result")} />
      default:
        return <LandingPage onStart={() => goToPage("upload")} />
    }
  }

  return (
    <main className="h-screen w-screen overflow-hidden bg-background grid-bg relative">
      <AnimatePresence mode="wait" custom={direction}>
        <motion.div
          key={currentPage}
          custom={direction}
          variants={variants}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{
            x: { type: "spring", stiffness: 300, damping: 30 },
            opacity: { duration: 0.2 },
          }}
          className="absolute inset-0"
        >
          {renderPage()}
        </motion.div>
      </AnimatePresence>
    </main>
  )
}
