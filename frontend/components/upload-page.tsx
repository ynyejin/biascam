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

  const sampleVideos = [
    {
      id: "sample1",
      title: "It's Me",
      group: "ILLIT",
      description: "Group performance · 45 sec",
      thumbnail: "/samples/sample1.png",
    },
    {
      id: "sample2",
      title: "REDRED",
      group: "CORTIS",
      description: "Fast movement · 41 sec",
      thumbnail: "/samples/sample2.png",
    },
    {
      id: "sample3",
      title: "RUDE!",
      group: "Hearts2Hearts",
      description: "Multi-member stage · 41 sec",
      thumbnail: "/samples/sample3.png",
    },
  ]

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

  const handleSampleSelect = async (sampleId: string) => {
    setIsUploading(true)
    setError(null)
    setFileName(`${sampleId}.mp4`)

    try {
      const response = await fetch("http://127.0.0.1:8000/upload-sample", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sample_id: sampleId,
        }),
      })

      const data = await response.json()
      console.log("Sample upload response:", data)

      if (!response.ok || data.message !== "sample upload complete") {
        throw new Error(data.error || "Sample upload failed")
      }

      setIsUploading(false)
      onUpload()
    } catch (err) {
      console.error(err)
      setError("샘플 영상 불러오기에 실패했습니다.")
      setIsUploading(false)
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

        <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.03] px-5 py-4 text-sm text-zinc-400">
          <p className="font-semibold text-zinc-200 mb-2">
            업로드 추천 조건
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <p>단체 무대처럼 여러 멤버가 함께 나오는 영상이 적합합니다.</p>
            <p>처리 속도를 위해 20–40초 정도의 짧은 클립을 권장합니다.</p>
            <p>얼굴이 밝고 선명하게 보일수록 멤버 선택과 직캠 생성 정확도가 높아집니다.</p>
          </div>
        </div>

        <div className="mt-10">
          <div className="flex items-center justify-center gap-4 mb-5">
            <div className="h-px w-20 bg-white/10" />
            <p className="text-sm text-zinc-400">
              Or try with a sample video
            </p>
            <div className="h-px w-20 bg-white/10" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {sampleVideos.map((sample) => (
              <button
                key={sample.id}
                type="button"
                onClick={() => handleSampleSelect(sample.id)}
                disabled={isUploading}
                className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 text-left hover:border-pink-400/50 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <div className="relative aspect-video overflow-hidden">
                  <img
                    src={sample.thumbnail}
                    alt={sample.title}
                    className="absolute inset-0 h-full w-full object-cover scale-110 blur-[2px] brightness-50 group-hover:scale-125 group-hover:brightness-75 transition duration-500"
                  />

                  <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/35 to-transparent" />

                  <div className="absolute left-4 top-4 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-white backdrop-blur-md border border-white/10">
                    SAMPLE
                  </div>

                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="h-12 w-12 rounded-full bg-white/15 backdrop-blur-md flex items-center justify-center group-hover:scale-110 transition">
                      <Video className="h-5 w-5 text-white" />
                    </div>
                  </div>

                  <div className="absolute bottom-0 left-0 right-0 p-4">
                    <p className="text-xs uppercase tracking-[0.25em] text-pink-300 mb-1">
                      {sample.group}
                    </p>
                    <p className="font-bold text-white text-lg leading-tight">
                      {sample.title}
                    </p>
                    <p className="text-sm text-zinc-300 mt-1">
                      {sample.description}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>

        {error && (
          <p className="mt-5 text-center text-red-400 text-sm">{error}</p>
        )}
      </div>
    </div>
    </section>
  )
}