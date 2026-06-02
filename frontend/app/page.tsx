"use client"

import { useState, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { LandingPage } from "@/components/landing-page"
import { UploadPage } from "@/components/upload-page"
import { FaceSelectionPage } from "@/components/face-selection-page"
import { ProcessingPage } from "@/components/processing-page"
import { ResultPage } from "@/components/result-page"
import { AnalysisPage } from "@/components/analysis-page"

export type AppPage =
  | "landing"
  | "upload"
  | "selection"
  | "processing"
  | "result"
  | "analysis"

const pageOrder: AppPage[] = [
  "landing",
  "upload",
  "selection",
  "processing",
  "result",
  "analysis",
]

export default function Home() {
  const [currentPage, setCurrentPage] = useState<AppPage>("landing")
  const [direction, setDirection] = useState(1)
  const [selectedFace, setSelectedFace] = useState<number | null>(null)
  const [processError, setProcessError] = useState<string | null>(null)
  const [resultData, setResultData] = useState<any>(null)

  const goToPage = useCallback(
    (page: AppPage) => {
      const currentIndex = pageOrder.indexOf(currentPage)
      const nextIndex = pageOrder.indexOf(page)
      setDirection(nextIndex > currentIndex ? 1 : -1)
      setCurrentPage(page)
    },
    [currentPage]
  )

  const handleFaceSelect = async (faceId: number) => {
  setSelectedFace(faceId)
  setProcessError(null)
  setResultData(null)
  goToPage("processing")

  try {
    const response = await fetch("http://127.0.0.1:8000/process", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        face_id: faceId,
      }),
    })

    const data = await response.json()
    console.log("Processing response:", data)

    if (!response.ok || data.message !== "processing started") {
      throw new Error(data.error || "Processing failed")
    }

    goToPage("processing")
  } catch (error) {
    console.error(error)
    setProcessError("처리 중 오류가 발생했습니다. 백엔드 서버를 확인해주세요.")
    goToPage("selection")
  }
}

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
        return (
          <UploadPage
            onUpload={() => goToPage("selection")}
          />
        )

      case "selection":
        return (
          <FaceSelectionPage
            onSelect={handleFaceSelect}
            onBack={() => goToPage("upload")}
          />
        )

      case "processing":
        return (
          <ProcessingPage
            onComplete={() => goToPage("result")}
            setResultData={setResultData}
          />
        )

      case "result":
        return (
          <ResultPage
            onAnalysis={() => goToPage("analysis")}
            onBack={() => goToPage("selection")}
            selectedFace={selectedFace}
            resultData={resultData}
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
      {processError && (
        <div className="absolute top-4 left-1/2 z-50 -translate-x-1/2 rounded-xl bg-red-500/20 border border-red-400/40 px-5 py-3 text-sm text-red-200 backdrop-blur">
          {processError}
        </div>
      )}

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