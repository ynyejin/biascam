"use client"

import { useState } from "react"
import { Upload, Loader2, Video } from "lucide-react"

interface UploadPageProps {
  onUpload: () => void
}

export function UploadPage({ onUpload }: UploadPageProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleUpload = async (file: File) => {
    setIsUploading(true)
    setError(null)
    setFileName(file.name)

    try {
      const formData = new FormData()
      formData.append("file", file)

      const response = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        throw new Error("Upload failed")
      }

      const data = await response.json()
      console.log("Upload success:", data)

      setIsUploading(false)
      onUpload()
    } catch (err) {
      console.error(err)
      setError("영상 업로드에 실패했습니다. 백엔드 서버가 실행 중인지 확인해주세요.")
      setIsUploading(false)
    }
  }

  const openFilePicker = () => {
    document.getElementById("video-upload")?.click()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]

    if (file) {
      handleUpload(file)
    }
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()

    const file = e.dataTransfer.files?.[0]

    if (file) {
      handleUpload(file)
    }
  }

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
  }

  return (
    <section className="min-h-screen w-full bg-black text-white flex items-center justify-center px-6">
      <div className="w-full max-w-3xl">
        <div className="text-center mb-10">
          <h1 className="text-5xl md:text-7xl font-black tracking-tight mb-4">
            Upload your stage
          </h1>
          <p className="text-zinc-400 text-lg">
            Upload a group performance video and let BiasCam find your bias.
          </p>
        </div>

        <input
          id="video-upload"
          type="file"
          accept="video/*"
          className="hidden"
          onChange={handleFileChange}
        />

        <div
          onClick={openFilePicker}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          className="cursor-pointer rounded-3xl border border-white/15 bg-white/5 backdrop-blur-xl p-12 text-center hover:bg-white/10 transition"
        >
          {isUploading ? (
            <div className="flex flex-col items-center gap-5">
              <Loader2 className="h-14 w-14 animate-spin text-pink-400" />
              <div>
                <p className="text-xl font-semibold">Uploading video...</p>
                {fileName && (
                  <p className="text-sm text-zinc-400 mt-2">{fileName}</p>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-5">
              <div className="h-20 w-20 rounded-full bg-pink-500/20 flex items-center justify-center">
                <Upload className="h-10 w-10 text-pink-300" />
              </div>

              <div>
                <p className="text-2xl font-bold mb-2">
                  Drag & drop your video
                </p>
                <p className="text-zinc-400">
                  or click here to upload a group performance video
                </p>
              </div>

              <div className="flex items-center gap-2 text-sm text-zinc-500">
                <Video className="h-4 w-4" />
                MP4 recommended · 10–40 sec clip recommended
              </div>
            </div>
          )}
        </div>

        {error && (
          <p className="mt-5 text-center text-red-400 text-sm">{error}</p>
        )}
      </div>
    </section>
  )
}