"use client"

import { motion } from "framer-motion"
import { FloatingStickers } from "./floating-stickers"
import { FloatingIdols } from "./floating-idols"

interface LandingPageProps {
  onStart: () => void
}

export function LandingPage({ onStart }: LandingPageProps) {
  return (
    <div className="relative h-full w-full flex flex-col items-center justify-center">
      <FloatingStickers />
      <FloatingIdols />
      
      {/* Main Title */}
      <motion.button
        onClick={onStart}
        className="relative z-10 cursor-pointer group"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <h1 className="text-6xl md:text-8xl lg:text-[10rem] font-black text-foreground title-glow leading-none tracking-tighter text-center">
          <span className="block">{"Who's"}</span>
          <span className="block">your</span>
          <span className="block text-transparent bg-clip-text bg-gradient-to-r from-pink-400 via-purple-400 to-cyan-400">
            bias?
          </span>
        </h1>
        
        {/* Hover effect glow */}
        <motion.div
          className="absolute inset-0 -z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
          style={{
            background: "radial-gradient(ellipse at center, rgba(255,255,255,0.1) 0%, transparent 70%)",
            filter: "blur(40px)",
          }}
        />
      </motion.button>

      {/* CTA hint */}
      <motion.div
        className="absolute bottom-12 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
      >
        <span className="text-xs text-muted-foreground uppercase tracking-widest">
          Click to start
        </span>
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          className="w-6 h-10 rounded-full border-2 border-muted-foreground/30 flex items-start justify-center pt-2"
        >
          <motion.div className="w-1.5 h-1.5 rounded-full bg-foreground" />
        </motion.div>
      </motion.div>
    </div>
  )
}
