"use client"

import { motion } from "framer-motion"

interface FloatingStickersProps {
  className?: string
}

const stickers = [
  // Star
  {
    id: "star",
    content: (
      <svg viewBox="0 0 100 100" className="w-full h-full">
        <defs>
          <linearGradient id="starGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFD93D" />
            <stop offset="100%" stopColor="#FF9A3C" />
          </linearGradient>
        </defs>
        <path
          d="M50 5 L61 40 L98 40 L68 60 L79 95 L50 75 L21 95 L32 60 L2 40 L39 40 Z"
          fill="url(#starGrad)"
        />
        <ellipse cx="40" cy="35" rx="6" ry="4" fill="#000" />
        <ellipse cx="60" cy="35" rx="6" ry="4" fill="#000" />
        <path d="M40 55 Q50 65 60 55" stroke="#000" strokeWidth="3" fill="none" />
      </svg>
    ),
    position: { top: "8%", right: "15%" },
    size: "w-20 h-20",
    rotation: 15,
    delay: 0,
  },
  // Heart
  {
    id: "heart",
    content: (
      <svg viewBox="0 0 100 100" className="w-full h-full">
        <defs>
          <linearGradient id="heartGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FF6B9D" />
            <stop offset="50%" stopColor="#C44569" />
            <stop offset="100%" stopColor="#6B5B95" />
          </linearGradient>
        </defs>
        <path
          d="M50 88 C20 60 5 40 15 25 C25 10 45 15 50 30 C55 15 75 10 85 25 C95 40 80 60 50 88"
          fill="url(#heartGrad)"
        />
        <rect x="30" y="40" width="25" height="8" fill="#FFD93D" rx="2" transform="rotate(-10 42 44)" />
      </svg>
    ),
    position: { top: "25%", left: "8%" },
    size: "w-24 h-24",
    rotation: -10,
    delay: 0.2,
  },
  // Camera
  {
    id: "camera",
    content: (
      <svg viewBox="0 0 100 80" className="w-full h-full">
        <defs>
          <linearGradient id="camGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#4ECDC4" />
            <stop offset="100%" stopColor="#2C3E50" />
          </linearGradient>
        </defs>
        <rect x="5" y="20" width="90" height="55" rx="8" fill="url(#camGrad)" />
        <rect x="30" y="5" width="40" height="20" rx="4" fill="#34495E" />
        <circle cx="50" cy="47" r="20" fill="#1a1a2e" stroke="#fff" strokeWidth="3" />
        <circle cx="50" cy="47" r="12" fill="#16213e" />
        <circle cx="55" cy="42" r="4" fill="rgba(255,255,255,0.5)" />
        <circle cx="80" cy="30" r="5" fill="#e74c3c" />
      </svg>
    ),
    position: { bottom: "20%", right: "10%" },
    size: "w-28 h-22",
    rotation: 8,
    delay: 0.4,
  },
  // Music Note
  {
    id: "music",
    content: (
      <svg viewBox="0 0 60 100" className="w-full h-full">
        <defs>
          <linearGradient id="musicGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#a8edea" />
            <stop offset="100%" stopColor="#fed6e3" />
          </linearGradient>
        </defs>
        <ellipse cx="15" cy="85" rx="15" ry="12" fill="url(#musicGrad)" />
        <rect x="27" y="20" width="6" height="68" fill="url(#musicGrad)" />
        <path d="M30 20 Q45 15 55 25 Q60 35 50 40 L30 35 Z" fill="url(#musicGrad)" />
      </svg>
    ),
    position: { top: "60%", left: "5%" },
    size: "w-16 h-24",
    rotation: -15,
    delay: 0.6,
  },
  // Sparkle
  {
    id: "sparkle",
    content: (
      <svg viewBox="0 0 100 100" className="w-full h-full">
        <defs>
          <linearGradient id="sparkleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#fff" />
            <stop offset="100%" stopColor="#E0E5EC" />
          </linearGradient>
        </defs>
        <path
          d="M50 5 L55 40 L95 50 L55 60 L50 95 L45 60 L5 50 L45 40 Z"
          fill="url(#sparkleGrad)"
        />
      </svg>
    ),
    position: { top: "15%", left: "20%" },
    size: "w-12 h-12",
    rotation: 0,
    delay: 0.1,
  },
  // Cute blob face
  {
    id: "blob",
    content: (
      <svg viewBox="0 0 100 100" className="w-full h-full">
        <defs>
          <linearGradient id="blobGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ffecd2" />
            <stop offset="100%" stopColor="#fcb69f" />
          </linearGradient>
        </defs>
        <path
          d="M50 10 C80 10 95 30 95 50 C95 75 75 90 50 90 C25 90 5 75 5 50 C5 25 20 10 50 10"
          fill="url(#blobGrad)"
        />
        <circle cx="35" cy="45" r="5" fill="#333" />
        <circle cx="65" cy="45" r="5" fill="#333" />
        <ellipse cx="35" cy="43" rx="2" ry="1.5" fill="#fff" />
        <ellipse cx="65" cy="43" rx="2" ry="1.5" fill="#fff" />
        <path d="M40 65 Q50 75 60 65" stroke="#333" strokeWidth="3" fill="none" strokeLinecap="round" />
        <ellipse cx="25" cy="55" rx="8" ry="5" fill="rgba(255,150,150,0.5)" />
        <ellipse cx="75" cy="55" rx="8" ry="5" fill="rgba(255,150,150,0.5)" />
      </svg>
    ),
    position: { bottom: "15%", left: "12%" },
    size: "w-20 h-20",
    rotation: 5,
    delay: 0.3,
  },
  // Polaroid placeholder
  {
    id: "polaroid",
    content: (
      <svg viewBox="0 0 80 100" className="w-full h-full">
        <defs>
          <linearGradient id="polaroidGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#fff" />
            <stop offset="100%" stopColor="#f0f0f0" />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="80" height="100" rx="4" fill="url(#polaroidGrad)" />
        <rect x="8" y="8" width="64" height="64" fill="#2a2a4a" />
        <circle cx="40" cy="40" r="15" stroke="#555" strokeWidth="2" fill="none" strokeDasharray="4 2" />
        <text x="40" y="90" textAnchor="middle" fontSize="8" fill="#888">bias?</text>
      </svg>
    ),
    position: { top: "10%", right: "8%" },
    size: "w-16 h-20",
    rotation: 20,
    delay: 0.5,
  },
  // Video icon
  {
    id: "video",
    content: (
      <svg viewBox="0 0 100 80" className="w-full h-full">
        <defs>
          <linearGradient id="vidGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#667eea" />
            <stop offset="100%" stopColor="#764ba2" />
          </linearGradient>
        </defs>
        <rect x="5" y="10" width="60" height="60" rx="8" fill="url(#vidGrad)" />
        <path d="M70 25 L95 10 L95 70 L70 55 Z" fill="url(#vidGrad)" />
        <circle cx="35" cy="40" r="12" fill="rgba(255,255,255,0.3)" />
        <path d="M30 32 L45 40 L30 48 Z" fill="#fff" />
      </svg>
    ),
    position: { bottom: "25%", right: "18%" },
    size: "w-20 h-16",
    rotation: -8,
    delay: 0.7,
  },
]

export function FloatingStickers({ className = "" }: FloatingStickersProps) {
  return (
    <div className={`absolute inset-0 overflow-hidden pointer-events-none ${className}`}>
      {stickers.map((sticker) => (
        <motion.div
          key={sticker.id}
          className={`absolute sticker ${sticker.size}`}
          style={{
            ...sticker.position,
          }}
          initial={{ opacity: 0, scale: 0.5, rotate: sticker.rotation - 20 }}
          animate={{
            opacity: 1,
            scale: 1,
            rotate: sticker.rotation,
            y: [0, -10, 0],
          }}
          transition={{
            opacity: { duration: 0.5, delay: sticker.delay },
            scale: { duration: 0.5, delay: sticker.delay },
            rotate: { duration: 0.5, delay: sticker.delay },
            y: {
              duration: 3 + Math.random() * 2,
              repeat: Infinity,
              ease: "easeInOut",
              delay: sticker.delay,
            },
          }}
        >
          {sticker.content}
        </motion.div>
      ))}
    </div>
  )
}
